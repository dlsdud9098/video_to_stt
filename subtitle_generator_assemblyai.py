import assemblyai as aai
import srt
from pathlib import Path
from typing import Optional, List, Dict
import logging
from datetime import timedelta
import json
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SubtitleGeneratorAssemblyAI:
    def __init__(self, api_key: Optional[str] = None):
        if api_key is None:
            api_key = os.getenv("ASSEMBLYAI_API_KEY")
            if not api_key:
                raise ValueError("AssemblyAI API key is required. Set ASSEMBLYAI_API_KEY environment variable or pass api_key parameter.")
        
        aai.settings.api_key = api_key
        logger.info("AssemblyAI client initialized with Universal-2 model")
        
    def transcribe_audio(self, audio_path: str, language: Optional[str] = None) -> Dict:
        audio_path = Path(audio_path)
        
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        logger.info(f"Transcribing audio with AssemblyAI Universal-2: {audio_path}")
        
        config = aai.TranscriptionConfig(
            language_detection=language is None,
            language_code=language if language else None,
            punctuate=True,
            format_text=True,
            disfluencies=False,
            speaker_labels=False,
            auto_highlights=False,
            content_safety=False,
            iab_categories=False,
            sentiment_analysis=False,
            summarization=False,
            entity_detection=False
        )
        
        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(str(audio_path), config=config)
        
        if transcript.status == aai.TranscriptStatus.error:
            raise Exception(f"Transcription failed: {transcript.error}")
        
        segments = []
        if transcript.words:
            current_segment = {
                "start": 0,
                "end": 0,
                "text": ""
            }
            segment_duration = 3.0
            current_start = 0
            
            for word in transcript.words:
                if word.start / 1000 - current_start > segment_duration and current_segment["text"]:
                    current_segment["end"] = word.start / 1000
                    segments.append(current_segment.copy())
                    current_segment = {
                        "start": word.start / 1000,
                        "end": 0,
                        "text": word.text
                    }
                    current_start = word.start / 1000
                else:
                    if current_segment["text"]:
                        current_segment["text"] += " " + word.text
                    else:
                        current_segment["text"] = word.text
                        current_segment["start"] = word.start / 1000
            
            if current_segment["text"]:
                current_segment["end"] = transcript.words[-1].end / 1000
                segments.append(current_segment)
        
        result = {
            "text": transcript.text,
            "language": transcript.language_code if transcript.language_code else language,
            "segments": segments
        }
        
        logger.info(f"Transcription completed. Language: {result['language']}")
        logger.info(f"Total segments: {len(segments)}")
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
        
        logger.info(f"Translating audio to English with AssemblyAI: {audio_path}")
        
        config = aai.TranscriptionConfig(
            language_code="en",
            punctuate=True,
            format_text=True
        )
        
        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(str(audio_path), config=config)
        
        if transcript.status == aai.TranscriptStatus.error:
            raise Exception(f"Translation failed: {transcript.error}")
        
        segments = []
        if transcript.words:
            current_segment = {
                "start": 0,
                "end": 0,
                "text": ""
            }
            segment_duration = 3.0
            current_start = 0
            
            for word in transcript.words:
                if word.start / 1000 - current_start > segment_duration and current_segment["text"]:
                    current_segment["end"] = word.start / 1000
                    segments.append(current_segment.copy())
                    current_segment = {
                        "start": word.start / 1000,
                        "end": 0,
                        "text": word.text
                    }
                    current_start = word.start / 1000
                else:
                    if current_segment["text"]:
                        current_segment["text"] += " " + word.text
                    else:
                        current_segment["text"] = word.text
                        current_segment["start"] = word.start / 1000
            
            if current_segment["text"]:
                current_segment["end"] = transcript.words[-1].end / 1000
                segments.append(current_segment)
        
        subtitle_content = self._segments_to_srt(segments)
        output_path.write_text(subtitle_content, encoding='utf-8')
        
        logger.info(f"English subtitles saved to: {output_path}")
        return str(output_path)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python subtitle_generator_assemblyai.py <audio_file> [api_key]")
        print("Set ASSEMBLYAI_API_KEY environment variable or pass api_key as parameter")
        sys.exit(1)
    
    api_key = sys.argv[2] if len(sys.argv) > 2 else None
    
    generator = SubtitleGeneratorAssemblyAI(api_key=api_key)
    subtitle_path = generator.generate_subtitles(sys.argv[1])
    print(f"Subtitles saved to: {subtitle_path}")