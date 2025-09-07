from moviepy.editor import VideoFileClip
import os
from pathlib import Path
from typing import Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AudioExtractor:
    def __init__(self, output_format: str = "wav"):
        self.output_format = output_format
        
    def extract_audio(self, video_path: str, output_path: Optional[str] = None) -> str:
        video_path = Path(video_path)
        
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        if output_path is None:
            output_path = video_path.with_suffix(f".{self.output_format}")
        else:
            output_path = Path(output_path)
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            logger.info(f"Extracting audio from {video_path}")
            video = VideoFileClip(str(video_path))
            
            audio = video.audio
            
            if audio is None:
                raise ValueError(f"No audio stream found in {video_path}")
            
            audio.write_audiofile(
                str(output_path),
                codec='pcm_s16le' if self.output_format == 'wav' else None,
                logger=None
            )
            
            video.close()
            audio.close()
            
            logger.info(f"Audio extracted successfully to {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error extracting audio: {e}")
            raise

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python audio_extractor.py <video_file>")
        sys.exit(1)
    
    extractor = AudioExtractor()
    audio_path = extractor.extract_audio(sys.argv[1])
    print(f"Audio saved to: {audio_path}")