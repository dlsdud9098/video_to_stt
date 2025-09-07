import os
import yt_dlp
from typing import Optional
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VideoDownloader:
    def __init__(self, output_dir: str = "downloads"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def download_video(self, url: str, quality: str = "best") -> Optional[Path]:
        try:
            logger.info(f"Starting download for: {url}")
            
            # 파일명 템플릿 설정
            output_template = str(self.output_dir / '%(title)s.%(ext)s')
            
            ydl_opts = {
                'outtmpl': output_template,
                'quiet': False,
                'no_warnings': False,
                'extract_flat': False,
            }
            
            # 품질 설정
            if quality == "best":
                ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            elif quality == "worst":
                ydl_opts['format'] = 'worst'
            elif quality == "audio_only":
                ydl_opts['format'] = 'bestaudio/best'
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]
            else:
                # 특정 해상도 지정 (예: 720p, 1080p)
                ydl_opts['format'] = f'best[height<={quality[:-1]}]'
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # 정보 추출
                info = ydl.extract_info(url, download=True)
                
                # 다운로드된 파일 경로 찾기
                if 'requested_downloads' in info:
                    filepath = info['requested_downloads'][0]['filepath']
                else:
                    # 파일명 직접 구성
                    title = info.get('title', 'video').replace('/', '_')
                    ext = info.get('ext', 'mp4')
                    filepath = self.output_dir / f"{title}.{ext}"
                
                output_file = Path(filepath)
                
                if output_file.exists():
                    logger.info(f"Download completed: {output_file}")
                    return output_file
                else:
                    # 파일이 없으면 downloads 디렉토리에서 찾기
                    for file in self.output_dir.glob("*"):
                        if file.is_file() and info.get('title', '') in file.name:
                            logger.info(f"Download completed: {file}")
                            return file
                    
                    logger.error("Downloaded file not found")
                    return None
                    
        except Exception as e:
            logger.error(f"Download error: {e}")
            return None
    
    def download_audio_only(self, url: str) -> Optional[Path]:
        return self.download_video(url, quality="audio_only")
    
    def get_video_info(self, url: str) -> Optional[dict]:
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                return {
                    "title": info.get('title'),
                    "author": info.get('uploader') or info.get('channel'),
                    "length": info.get('duration'),
                    "views": info.get('view_count'),
                    "description": info.get('description'),
                    "publish_date": info.get('upload_date'),
                    "thumbnail_url": info.get('thumbnail'),
                    "like_count": info.get('like_count'),
                    "formats": [f"{fmt.get('format_note', 'unknown')} - {fmt.get('ext', 'unknown')}" 
                               for fmt in info.get('formats', [])[:10]]  # 상위 10개만
                }
        except Exception as e:
            logger.error(f"Error getting video info: {e}")
            return None


if __name__ == "__main__":
    downloader = VideoDownloader()
    
    test_url = input("Enter YouTube URL: ")
    
    info = downloader.get_video_info(test_url)
    if info:
        print(f"\nVideo Info:")
        print(f"Title: {info['title']}")
        print(f"Author: {info['author']}")
        print(f"Duration: {info['length']} seconds")
        print(f"Views: {info.get('views', 'N/A')}")
        print(f"Likes: {info.get('like_count', 'N/A')}")
    
    video_path = downloader.download_video(test_url)
    if video_path:
        print(f"\nVideo downloaded successfully to: {video_path}")