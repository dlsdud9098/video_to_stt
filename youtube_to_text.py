#!/usr/bin/env python3
"""
YouTube to Text Converter
고정확도 음성-텍스트 변환 도구

사용법:
    python youtube_to_text.py <YouTube URL>
    python youtube_to_text.py <YouTube URL> --model large-v3
    python youtube_to_text.py <YouTube URL> --language ko
"""

import sys
import argparse
from pathlib import Path
import logging
from datetime import datetime
from video_downloader import VideoDownloader
from audio_extractor import AudioExtractor
from subtitle_generator import SubtitleGenerator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def convert_youtube_to_text(
    youtube_url: str,
    model_size: str = "large-v3",
    language: str = None,
    output_format: str = "txt",
    keep_files: bool = False
):
    """
    YouTube 영상을 다운로드하고 텍스트로 변환
    
    Args:
        youtube_url: YouTube 영상 URL
        model_size: Whisper 모델 크기 (정확도: large-v3 > large-v2 > medium > small > base > tiny)
        language: 언어 코드 (None이면 자동 감지)
        output_format: 출력 형식 (txt, srt, json)
        keep_files: 중간 파일 보관 여부
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("output") / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        logger.info("="*60)
        logger.info("YouTube to Text Converter")
        logger.info(f"Model: {model_size} (정확도 우선)")
        logger.info("="*60)
        
        # 1단계: YouTube 영상 다운로드
        logger.info("\n[1/3] YouTube 영상 다운로드 중...")
        downloader = VideoDownloader(output_dir="downloads")
        video_path = downloader.download_video(youtube_url)
        
        if not video_path:
            logger.error("영상 다운로드 실패")
            return None
        
        # 2단계: 음성 추출
        logger.info("\n[2/3] 영상에서 음성 추출 중...")
        extractor = AudioExtractor(output_format="wav")
        audio_path = extractor.extract_audio(
            str(video_path),
            str(output_dir / f"audio.wav")
        )
        
        # 3단계: 음성을 텍스트로 변환
        logger.info(f"\n[3/3] 음성을 텍스트로 변환 중 (모델: {model_size})...")
        logger.info("이 작업은 몇 분 정도 소요될 수 있습니다...")
        
        generator = SubtitleGenerator(model_size=model_size)
        
        # 결과 파일 경로
        base_name = video_path.stem
        output_file = output_dir / f"{base_name}.{output_format}"
        
        # 텍스트 변환 수행
        result_path = generator.generate_subtitles(
            audio_path,
            str(output_file),
            format=output_format,
            language=language
        )
        
        # 텍스트 파일 내용 출력
        if output_format == "txt":
            with open(result_path, 'r', encoding='utf-8') as f:
                text_content = f.read()
                logger.info("\n" + "="*60)
                logger.info("변환된 텍스트:")
                logger.info("="*60)
                print(text_content)
                logger.info("="*60)
        
        logger.info(f"\n✅ 변환 완료!")
        logger.info(f"📁 결과 파일: {result_path}")
        
        # 정리
        if not keep_files:
            logger.info("\n임시 파일 정리 중...")
            import os
            if video_path.exists():
                os.remove(video_path)
            if Path(audio_path).exists():
                os.remove(audio_path)
        
        return result_path
        
    except Exception as e:
        logger.error(f"오류 발생: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(
        description="YouTube 영상을 텍스트로 변환 (고정확도 모드)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
모델 정확도 순위:
  1. large-v3  (1550M 파라미터, 가장 정확함, VRAM 10GB 필요)
  2. large-v2  (1550M 파라미터, 매우 정확함)
  3. large     (1550M 파라미터)
  4. medium    (769M 파라미터, 균형잡힌 선택)
  5. small     (244M 파라미터)
  6. base      (74M 파라미터, 빠르지만 정확도 낮음)
  7. tiny      (39M 파라미터, 가장 빠르지만 정확도 가장 낮음)

예제:
  python youtube_to_text.py https://youtube.com/watch?v=xxx
  python youtube_to_text.py https://youtube.com/watch?v=xxx --model medium
  python youtube_to_text.py https://youtube.com/watch?v=xxx --language ko --format srt
        """
    )
    
    parser.add_argument("url", help="YouTube 영상 URL")
    parser.add_argument(
        "-m", "--model",
        default="large-v3",
        choices=["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"],
        help="Whisper 모델 크기 (기본값: large-v3)"
    )
    parser.add_argument(
        "-l", "--language",
        help="언어 코드 (예: ko, en, ja, zh). 지정하지 않으면 자동 감지"
    )
    parser.add_argument(
        "-f", "--format",
        default="txt",
        choices=["txt", "srt", "json"],
        help="출력 형식 (기본값: txt)"
    )
    parser.add_argument(
        "--keep-files",
        action="store_true",
        help="다운로드한 영상과 음성 파일 보관"
    )
    
    args = parser.parse_args()
    
    # GPU 사용 가능 여부 확인
    try:
        import torch
        if torch.cuda.is_available():
            logger.info(f"🎮 GPU 사용 가능: {torch.cuda.get_device_name(0)}")
            logger.info(f"   VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
        else:
            logger.info("💻 CPU 모드로 실행 (GPU 없음, 속도가 느릴 수 있음)")
    except:
        pass
    
    # 변환 실행
    result = convert_youtube_to_text(
        args.url,
        model_size=args.model,
        language=args.language,
        output_format=args.format,
        keep_files=args.keep_files
    )
    
    if result:
        logger.info("\n✅ 모든 작업이 성공적으로 완료되었습니다!")
    else:
        logger.error("\n❌ 변환 중 오류가 발생했습니다.")
        sys.exit(1)

if __name__ == "__main__":
    main()