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

# 데이터셋 생성 모듈 추가
sys.path.append(str(Path(__file__).parent.parent))
from youtube_analyzer_ytdlp import YouTubeAnalyzer
from video_frame_analyzer import AdvancedVideoAnalyzer
from video_downloader_ytdlp import VideoDownloader

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

class DatasetRequest(BaseModel):
    youtube_url: str
    youtube_api_key: Optional[str] = None
    use_ocr: bool = False
    model_size: str = "large-v3"

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

@app.post("/api/dataset/create")
async def create_dataset(request: DatasetRequest, background_tasks: BackgroundTasks):
    """YouTube URL로부터 데이터셋 생성"""
    task_id = str(uuid.uuid4())
    processing_status.create_task(task_id)
    
    background_tasks.add_task(
        create_dataset_task,
        task_id,
        request.youtube_url,
        request.youtube_api_key,
        request.use_ocr,
        request.model_size
    )
    
    return {"task_id": task_id, "message": "Dataset creation started"}

async def create_dataset_task(
    task_id: str,
    youtube_url: str,
    api_key: Optional[str],
    use_ocr: bool,
    model_size: str
):
    """데이터셋 생성 백그라운드 작업"""
    try:
        processing_status.update_task(
            task_id,
            status="processing",
            progress=10,
            message="Initializing analyzers..."
        )
        await processing_status.send_update(task_id)
        
        # 분석기 초기화
        youtube_analyzer = YouTubeAnalyzer(api_key=api_key)
        downloader = VideoDownloader(output_dir="downloads")
        audio_extractor = AudioExtractor()
        subtitle_generator = SubtitleGenerator(model_size=model_size)
        
        video_analyzer = None
        if use_ocr:
            try:
                video_analyzer = AdvancedVideoAnalyzer(use_gpu=True)
            except:
                use_ocr = False
        
        # 메타데이터 수집
        processing_status.update_task(
            task_id,
            progress=20,
            message="Collecting metadata..."
        )
        await processing_status.send_update(task_id)
        
        metadata = youtube_analyzer.get_video_metadata(youtube_url)
        if not metadata:
            raise Exception("Failed to collect metadata")
        
        # 댓글 수집
        processing_status.update_task(
            task_id,
            progress=30,
            message="Collecting comments..."
        )
        await processing_status.send_update(task_id)
        
        comments = []
        video_id = metadata.get('video_id')
        if video_id and api_key:
            comments = youtube_analyzer.get_top_comments(video_id, max_results=50)
        
        # 영상 다운로드
        processing_status.update_task(
            task_id,
            progress=40,
            message="Downloading video..."
        )
        await processing_status.send_update(task_id)
        
        video_path = downloader.download_video(youtube_url)
        if not video_path:
            raise Exception("Failed to download video")
        
        # 음성 추출 및 텍스트 변환
        processing_status.update_task(
            task_id,
            progress=60,
            message="Extracting audio and transcribing..."
        )
        await processing_status.send_update(task_id)
        
        audio_path = audio_extractor.extract_audio(str(video_path))
        transcription_result = subtitle_generator.transcribe_audio(audio_path)
        transcription = transcription_result.get('text', '')
        detected_language = transcription_result.get('language', 'unknown')
        
        # OCR 분석 (선택사항)
        ocr_data = {}
        if use_ocr and video_analyzer:
            processing_status.update_task(
                task_id,
                progress=80,
                message="Analyzing video frames with OCR..."
            )
            await processing_status.send_update(task_id)
            
            try:
                full_analysis = video_analyzer.comprehensive_analysis(str(video_path))
                ocr_data = full_analysis.get('ocr', {})
            except:
                pass
        
        # 데이터 포맷팅
        processing_status.update_task(
            task_id,
            progress=90,
            message="Formatting dataset..."
        )
        await processing_status.send_update(task_id)
        
        # 분석 텍스트 생성
        analysis_text = f"""영상 제목: {metadata.get('title', 'Unknown')}
채널: {metadata.get('channel', 'Unknown')}
조회수: {metadata.get('views', 0):,}
길이: {metadata.get('duration', 0)}초

음성 텍스트:
{transcription[:500]}...

언어: {detected_language}"""
        
        # 상위 댓글 선택
        top_comments = sorted(
            comments,
            key=lambda x: x.get('likes', 0),
            reverse=True
        )[:10]
        
        # 데이터셋 항목 생성
        dataset_items = []
        for comment in top_comments:
            dataset_items.append({
                'input': analysis_text,
                'output': comment['text'],
                'metadata': {
                    'video_id': metadata.get('video_id'),
                    'title': metadata.get('title'),
                    'channel': metadata.get('channel'),
                    'views': metadata.get('views'),
                    'duration': metadata.get('duration'),
                    'language': detected_language,
                    'comment_likes': comment.get('likes', 0)
                }
            })
        
        # 파일 저장
        output_file = OUTPUT_DIR / f"{task_id}_dataset.jsonl"
        with open(output_file, 'w', encoding='utf-8') as f:
            for item in dataset_items:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        
        # 임시 파일 정리
        if video_path.exists():
            os.remove(video_path)
        if Path(audio_path).exists():
            os.remove(audio_path)
        
        processing_status.update_task(
            task_id,
            status="completed",
            progress=100,
            message="Dataset created successfully!",
            result={
                "dataset_file": f"{task_id}_dataset.jsonl",
                "items_count": len(dataset_items),
                "video_title": metadata.get('title'),
                "video_duration": metadata.get('duration')
            }
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

@app.get("/api/dataset/download/{filename}")
async def download_dataset(filename: str):
    """생성된 데이터셋 다운로드"""
    file_path = OUTPUT_DIR / filename
    if not file_path.exists() or not filename.endswith('.jsonl'):
        raise HTTPException(status_code=404, detail="Dataset file not found")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type='application/jsonl'
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)