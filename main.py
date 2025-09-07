#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path
import logging
from audio_extractor import AudioExtractor
from subtitle_generator import SubtitleGenerator
from video_downloader import VideoDownloader
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_cuda():
    try:
        import torch
        if torch.cuda.is_available():
            logger.info(f"CUDA is available. Version: {torch.version.cuda}")
            logger.info(f"GPU Device: {torch.cuda.get_device_name(0)}")
            return True
        else:
            logger.warning("CUDA is not available. Using CPU.")
            return False
    except ImportError:
        logger.error("PyTorch is not installed.")
        return False

def process_video(
    video_path: str,
    output_dir: str = None,
    model_size: str = "large-v3",
    language: str = None,
    subtitle_format: str = "srt",
    keep_audio: bool = True,
    translate_english: bool = False,
    device: str = None,
    is_youtube_url: bool = False
):
    if is_youtube_url:
        logger.info(f"Downloading YouTube video: {video_path}")
        downloader = VideoDownloader(output_dir="downloads")
        downloaded_path = downloader.download_video(video_path)
        if not downloaded_path:
            logger.error("Failed to download video")
            sys.exit(1)
        video_path = downloaded_path
    else:
        video_path = Path(video_path)
    
    if not video_path.exists():
        logger.error(f"Video file not found: {video_path}")
        sys.exit(1)
    
    if output_dir is None:
        output_dir = video_path.parent
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    
    base_name = video_path.stem
    
    logger.info(f"Processing video: {video_path}")
    logger.info(f"Output directory: {output_dir}")
    
    try:
        logger.info("Step 1: Extracting audio from video")
        extractor = AudioExtractor(output_format="wav")
        audio_path = extractor.extract_audio(
            str(video_path),
            str(output_dir / f"{base_name}.wav")
        )
        
        logger.info("Step 2: Generating subtitles from audio")
        generator = SubtitleGenerator(model_size=model_size, device=device)
        
        subtitle_path = generator.generate_subtitles(
            audio_path,
            str(output_dir / f"{base_name}.{subtitle_format}"),
            format=subtitle_format,
            language=language
        )
        
        if translate_english and language != "en":
            logger.info("Step 3: Translating to English")
            english_subtitle_path = generator.translate_to_english(
                audio_path,
                str(output_dir / f"{base_name}.en.srt")
            )
            logger.info(f"English subtitles: {english_subtitle_path}")
        
        if not keep_audio:
            logger.info("Removing temporary audio file")
            os.remove(audio_path)
        
        logger.info("Processing completed successfully!")
        logger.info(f"Subtitles saved to: {subtitle_path}")
        
        return subtitle_path
        
    except Exception as e:
        logger.error(f"Error during processing: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="Extract audio from video and generate subtitles using Whisper"
    )
    parser.add_argument("video", help="Path to the video file or YouTube URL")
    parser.add_argument("-o", "--output", help="Output directory (default: same as video)")
    parser.add_argument(
        "--youtube",
        action="store_true",
        help="Input is a YouTube URL"
    )
    parser.add_argument(
        "-m", "--model",
        default="large-v3",
        choices=["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"],
        help="Whisper model size (default: large-v3, highest accuracy)"
    )
    parser.add_argument(
        "-l", "--language",
        help="Language code (e.g., ko, en, ja, zh). Auto-detect if not specified"
    )
    parser.add_argument(
        "-f", "--format",
        default="srt",
        choices=["srt", "json", "txt"],
        help="Subtitle format (default: srt)"
    )
    parser.add_argument(
        "--no-keep-audio",
        action="store_true",
        help="Delete extracted audio file after processing"
    )
    parser.add_argument(
        "--translate",
        action="store_true",
        help="Also generate English translation"
    )
    parser.add_argument(
        "--device",
        choices=["cuda", "cpu"],
        help="Device to use (auto-detect if not specified)"
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Process all video files in a directory"
    )
    
    args = parser.parse_args()
    
    logger.info("Video Subtitle Extractor")
    logger.info("=" * 50)
    
    check_cuda()
    
    is_youtube = args.youtube or (isinstance(args.video, str) and (args.video.startswith("http://") or args.video.startswith("https://")))
    
    if args.batch:
        if is_youtube:
            logger.error("Batch processing is not supported for YouTube URLs")
            sys.exit(1)
        
        video_path = Path(args.video)
        if not video_path.is_dir():
            logger.error("For batch processing, provide a directory path")
            sys.exit(1)
        
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv'}
        video_files = [f for f in video_path.iterdir() if f.suffix.lower() in video_extensions]
        
        if not video_files:
            logger.error(f"No video files found in {video_path}")
            sys.exit(1)
        
        logger.info(f"Found {len(video_files)} video files to process")
        
        for i, video_file in enumerate(video_files, 1):
            logger.info(f"\n[{i}/{len(video_files)}] Processing: {video_file.name}")
            process_video(
                str(video_file),
                args.output,
                args.model,
                args.language,
                args.format,
                not args.no_keep_audio,
                args.translate,
                args.device,
                False
            )
    else:
        process_video(
            args.video,
            args.output,
            args.model,
            args.language,
            args.format,
            not args.no_keep_audio,
            args.translate,
            args.device,
            is_youtube
        )

if __name__ == "__main__":
    main()