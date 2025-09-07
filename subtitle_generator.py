import whisper
import torch
import srt
from pathlib import Path
from typing import Optional, List, Dict
import logging
from datetime import timedelta
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SubtitleGenerator:
    def __init__(self, model_size: str = "large-v3", device: Optional[str] = None):
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        
        logger.info(f"Using device: {device}")
        if device == "cuda":
            logger.info(f"CUDA version: {torch.version.cuda}")
            logger.info(f"GPU: {torch.cuda.get_device_name(0)}")
            logger.info(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
        
        self.device = device
        self.model_size = model_size
        
        model_priority = ["large-v3", "large-v2", "large", "medium", "small", "base", "tiny"]
        
        if model_size not in model_priority:
            logger.warning(f"Unknown model size: {model_size}, defaulting to large-v3")
            model_size = "large-v3"
        
        logger.info(f"Loading Whisper model: {model_size}")
        try:
            self.model = whisper.load_model(model_size, device=device)
            logger.info(f"Successfully loaded {model_size} model")
        except Exception as e:
            logger.warning(f"Failed to load {model_size}: {e}")
            fallback_model = "base"
            logger.info(f"Falling back to {fallback_model} model")
            self.model = whisper.load_model(fallback_model, device=device)
        
    def transcribe_audio(self, audio_path: str, language: Optional[str] = None) -> Dict:
        audio_path = Path(audio_path)
        
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        logger.info(f"Transcribing audio: {audio_path}")
        logger.info(f"Using model: {self.model_size}")
        
        options = {
            "language": language,
            "task": "transcribe",
            "verbose": False,
            "temperature": 0,
            "beam_size": 5,
            "best_of": 5,
            "fp16": self.device == "cuda",
            "condition_on_previous_text": True,
            "initial_prompt": None,
            "word_timestamps": True,
            "vad_filter": True,
            "vad_parameters": {
                "threshold": 0.6,
                "min_speech_duration_ms": 250,
                "max_speech_duration_s": float('inf'),
                "min_silence_duration_ms": 2000,
                "speech_pad_ms": 400
            }
        }
        
        result = self.model.transcribe(str(audio_path), **options)
        
        logger.info(f"Transcription completed. Detected language: {result['language']}")
        logger.info(f"Total segments: {len(result.get('segments', []))}")
        return result
    
    def _segments_to_srt(self, segments: List[Dict]) -> str:
        srt_segments = []
        
        for i, segment in enumerate(segments, 1):
            start_time = timedelta(seconds=segment['start'])
            end_time = timedelta(seconds=segment['end'])
            text = segment['text'].strip()
            
            srt_segment = srt.Subtitle(
                index=i,
                start=start_time,
                end=end_time,
                content=text
            )
            srt_segments.append(srt_segment)
        
        return srt.compose(srt_segments)
    
    def generate_subtitles(
        self, 
        audio_path: str, 
        output_path: Optional[str] = None, 
        format: str = "srt",
        language: Optional[str] = None
    ) -> str:
        audio_path = Path(audio_path)
        
        if output_path is None:
            output_path = audio_path.with_suffix(f".{format}")
        else:
            output_path = Path(output_path)
        
        result = self.transcribe_audio(str(audio_path), language=language)
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if format == "srt":
            subtitle_content = self._segments_to_srt(result['segments'])
            output_path.write_text(subtitle_content, encoding='utf-8')
        elif format == "json":
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
        elif format == "txt":
            output_path.write_text(result['text'], encoding='utf-8')
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        logger.info(f"Subtitles saved to: {output_path}")
        return str(output_path)
    
    def translate_to_english(self, audio_path: str, output_path: Optional[str] = None) -> str:
        audio_path = Path(audio_path)
        
        if output_path is None:
            output_path = audio_path.with_suffix(".en.srt")
        else:
            output_path = Path(output_path)
        
        logger.info(f"Translating audio to English: {audio_path}")
        
        result = self.model.transcribe(
            str(audio_path),
            task="translate",
            verbose=False
        )
        
        subtitle_content = self._segments_to_srt(result['segments'])
        output_path.write_text(subtitle_content, encoding='utf-8')
        
        logger.info(f"English subtitles saved to: {output_path}")
        return str(output_path)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python subtitle_generator.py <audio_file> [model_size]")
        print("Model sizes: tiny, base, small, medium, large")
        sys.exit(1)
    
    model_size = sys.argv[2] if len(sys.argv) > 2 else "base"
    
    generator = SubtitleGenerator(model_size=model_size)
    subtitle_path = generator.generate_subtitles(sys.argv[1])
    print(f"Subtitles saved to: {subtitle_path}")