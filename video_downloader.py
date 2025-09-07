import os
from pytube import YouTube
from pytube.exceptions import VideoUnavailable, PytubeError
from typing import Optional
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VideoDownloader:
    def __init__(self, output_dir: str = "downloads"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def download_video(self, url: str, quality: str = "highest") -> Optional[Path]:
        try:
            logger.info(f"Starting download for: {url}")
            yt = YouTube(url)
            
            logger.info(f"Video Title: {yt.title}")
            logger.info(f"Video Duration: {yt.length} seconds")
            
            if quality == "highest":
                stream = yt.streams.get_highest_resolution()
            elif quality == "lowest":
                stream = yt.streams.get_lowest_resolution()
            elif quality == "audio_only":
                stream = yt.streams.get_audio_only()
            else:
                stream = yt.streams.filter(res=quality).first()
            
            if not stream:
                logger.error(f"No stream found for quality: {quality}")
                return None
            
            logger.info(f"Downloading stream: {stream}")
            
            safe_filename = "".join(c for c in yt.title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_filename = safe_filename[:100]
            
            output_path = stream.download(
                output_path=self.output_dir,
                filename=f"{safe_filename}.{stream.subtype}"
            )
            
            output_file = Path(output_path)
            logger.info(f"Download completed: {output_file}")
            
            return output_file
            
        except VideoUnavailable as e:
            logger.error(f"Video unavailable: {e}")
            return None
        except PytubeError as e:
            logger.error(f"PyTube error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return None
    
    def download_audio_only(self, url: str) -> Optional[Path]:
        return self.download_video(url, quality="audio_only")
    
    def get_video_info(self, url: str) -> Optional[dict]:
        try:
            yt = YouTube(url)
            return {
                "title": yt.title,
                "author": yt.author,
                "length": yt.length,
                "views": yt.views,
                "description": yt.description,
                "publish_date": yt.publish_date,
                "thumbnail_url": yt.thumbnail_url,
                "available_qualities": [stream.resolution for stream in yt.streams.filter(progressive=True)]
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
        print(f"Available qualities: {info['available_qualities']}")
    
    video_path = downloader.download_video(test_url)
    if video_path:
        print(f"\nVideo downloaded successfully to: {video_path}")