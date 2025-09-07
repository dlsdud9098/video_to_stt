from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.websockets import WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from pathlib import Path
import shutil
import uuid
import os
import sys
import json
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))
from audio_extractor import AudioExtractor
from subtitle_generator import SubtitleGenerator
from subtitle_generator_assemblyai import SubtitleGeneratorAssemblyAI

app = FastAPI(title="Video to Subtitle API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

class ProcessingStatus:
    def __init__(self):
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.websockets: Dict[str, WebSocket] = {}
    
    def create_task(self, task_id: str):
        self.tasks[task_id] = {
            "id": task_id,
            "status": "pending",
            "progress": 0,
            "message": "Waiting to start...",
            "created_at": datetime.now().isoformat(),
            "result": None,
            "error": None
        }
    
    def update_task(self, task_id: str, **kwargs):
        if task_id in self.tasks:
            self.tasks[task_id].update(kwargs)
    
    def get_task(self, task_id: str):
        return self.tasks.get(task_id)
    
    async def send_update(self, task_id: str):
        if task_id in self.websockets:
            task = self.get_task(task_id)
            if task:
                try:
                    await self.websockets[task_id].send_json(task)
                except:
                    pass

processing_status = ProcessingStatus()

class ProcessRequest(BaseModel):
    model_size: str = "base"
    language: Optional[str] = None
    subtitle_format: str = "srt"
    translate_english: bool = False
    use_assemblyai: bool = True
    assemblyai_api_key: Optional[str] = None

@app.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    await websocket.accept()
    processing_status.websockets[task_id] = websocket
    
    try:
        task = processing_status.get_task(task_id)
        if task:
            await websocket.send_json(task)
        
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if task_id in processing_status.websockets:
            del processing_status.websockets[task_id]

@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv')):
        raise HTTPException(status_code=400, detail="Invalid video format")
    
    task_id = str(uuid.uuid4())
    video_path = UPLOAD_DIR / f"{task_id}_{file.filename}"
    
    with open(video_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    processing_status.create_task(task_id)
    
    return {
        "task_id": task_id,
        "filename": file.filename,
        "size": len(content)
    }

async def process_video_task(task_id: str, video_path: Path, options: ProcessRequest):
    try:
        processing_status.update_task(task_id, status="processing", progress=10, message="Extracting audio...")
        await processing_status.send_update(task_id)
        
        extractor = AudioExtractor(output_format="wav")
        audio_path = extractor.extract_audio(
            str(video_path),
            str(OUTPUT_DIR / f"{task_id}.wav")
        )
        
        processing_status.update_task(task_id, progress=30, message="Generating subtitles...")
        await processing_status.send_update(task_id)
        
        if options.use_assemblyai:
            generator = SubtitleGeneratorAssemblyAI(api_key=options.assemblyai_api_key)
        else:
            generator = SubtitleGenerator(model_size=options.model_size)
        
        subtitle_path = generator.generate_subtitles(
            audio_path,
            str(OUTPUT_DIR / f"{task_id}.{options.subtitle_format}"),
            format=options.subtitle_format,
            language=options.language
        )
        
        processing_status.update_task(task_id, progress=80, message="Finalizing...")
        await processing_status.send_update(task_id)
        
        result_files = {
            "subtitle": f"{task_id}.{options.subtitle_format}"
        }
        
        if options.translate_english and options.language != "en":
            processing_status.update_task(task_id, progress=90, message="Translating to English...")
            await processing_status.send_update(task_id)
            
            english_path = generator.translate_to_english(
                audio_path,
                str(OUTPUT_DIR / f"{task_id}.en.srt")
            )
            result_files["english_subtitle"] = f"{task_id}.en.srt"
        
        os.remove(audio_path)
        os.remove(video_path)
        
        processing_status.update_task(
            task_id,
            status="completed",
            progress=100,
            message="Processing completed!",
            result=result_files
        )
        await processing_status.send_update(task_id)
        
    except Exception as e:
        processing_status.update_task(
            task_id,
            status="failed",
            message=f"Error: {str(e)}",
            error=str(e)
        )
        await processing_status.send_update(task_id)
        
        if video_path.exists():
            os.remove(video_path)

@app.post("/api/process/{task_id}")
async def process_video(task_id: str, options: ProcessRequest, background_tasks: BackgroundTasks):
    task = processing_status.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    video_files = list(UPLOAD_DIR.glob(f"{task_id}_*"))
    if not video_files:
        raise HTTPException(status_code=404, detail="Video file not found")
    
    video_path = video_files[0]
    
    background_tasks.add_task(process_video_task, task_id, video_path, options)
    
    return {"message": "Processing started", "task_id": task_id}

@app.get("/api/status/{task_id}")
async def get_status(task_id: str):
    task = processing_status.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.get("/api/download/{filename}")
async def download_file(filename: str):
    file_path = OUTPUT_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type='application/octet-stream'
    )

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)