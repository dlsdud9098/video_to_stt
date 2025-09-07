#!/usr/bin/env python3
"""
YouTube 영상 종합 분석 시스템 (yt-dlp 버전)
- 영상 메타데이터 수집
- 댓글 수집
- 음성 텍스트 변환
- OCR 텍스트 추출
- 종합 분석 및 시나리오 생성
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import re
import yt_dlp
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class YouTubeAnalyzer:
    def __init__(self, api_key: Optional[str] = None):
        """
        YouTube 영상 분석기 초기화
        
        Args:
            api_key: YouTube Data API v3 키 (댓글 수집용)
        """
        self.api_key = api_key or os.getenv('YOUTUBE_API_KEY')
        self.youtube_api = None
        
        if self.api_key:
            try:
                self.youtube_api = build('youtube', 'v3', developerKey=self.api_key)
                logger.info("YouTube API 초기화 성공")
            except Exception as e:
                logger.warning(f"YouTube API 초기화 실패: {e}")
    
    def extract_video_id(self, url: str) -> Optional[str]:
        """YouTube URL에서 비디오 ID 추출"""
        patterns = [
            r'youtube\.com/watch\?v=([^&]+)',
            r'youtu\.be/([^?]+)',
            r'youtube\.com/shorts/([^?/]+)',
            r'youtube\.com/embed/([^?]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def get_video_metadata(self, url: str) -> Dict[str, Any]:
        """영상 메타데이터 수집 (yt-dlp 사용)"""
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                metadata = {
                    'video_id': info.get('id'),
                    'title': info.get('title'),
                    'channel': info.get('uploader') or info.get('channel'),
                    'channel_id': info.get('channel_id') or info.get('uploader_id'),
                    'description': info.get('description'),
                    'duration': info.get('duration'),
                    'views': info.get('view_count'),
                    'publish_date': info.get('upload_date'),
                    'thumbnail_url': info.get('thumbnail'),
                    'keywords': info.get('tags', []),
                    'like_count': info.get('like_count'),
                    'comment_count': info.get('comment_count'),
                    'url': url,
                    'webpage_url': info.get('webpage_url', url),
                    'categories': info.get('categories', []),
                    'age_limit': info.get('age_limit', 0),
                }
                
                logger.info(f"메타데이터 수집 완료: {metadata['title']}")
                return metadata
                
        except Exception as e:
            logger.error(f"메타데이터 수집 실패: {e}")
            return {}
    
    def get_top_comments(self, video_id: str, max_results: int = 100) -> List[Dict[str, Any]]:
        """상위 댓글 수집"""
        if not self.youtube_api:
            logger.warning("YouTube API가 설정되지 않아 댓글을 수집할 수 없습니다")
            return []
        
        try:
            comments = []
            
            # 댓글 스레드 요청
            request = self.youtube_api.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=min(max_results, 100),
                order="relevance"  # 관련성 순으로 정렬 (인기도 포함)
            )
            
            response = request.execute()
            
            for item in response.get('items', []):
                comment = item['snippet']['topLevelComment']['snippet']
                comments.append({
                    'text': comment['textOriginal'],
                    'author': comment['authorDisplayName'],
                    'likes': comment['likeCount'],
                    'published_at': comment['publishedAt'],
                    'updated_at': comment.get('updatedAt', comment['publishedAt'])
                })
            
            # 추가 페이지 처리
            while 'nextPageToken' in response and len(comments) < max_results:
                request = self.youtube_api.commentThreads().list(
                    part="snippet",
                    videoId=video_id,
                    pageToken=response['nextPageToken'],
                    maxResults=min(max_results - len(comments), 100),
                    order="relevance"
                )
                response = request.execute()
                
                for item in response.get('items', []):
                    comment = item['snippet']['topLevelComment']['snippet']
                    comments.append({
                        'text': comment['textOriginal'],
                        'author': comment['authorDisplayName'],
                        'likes': comment['likeCount'],
                        'published_at': comment['publishedAt'],
                        'updated_at': comment.get('updatedAt', comment['publishedAt'])
                    })
            
            logger.info(f"댓글 {len(comments)}개 수집 완료")
            return comments
            
        except HttpError as e:
            if e.resp.status == 403:
                logger.error("API 할당량 초과 또는 권한 없음")
            else:
                logger.error(f"댓글 수집 실패: {e}")
            return []
        except Exception as e:
            logger.error(f"댓글 수집 중 오류: {e}")
            return []
    
    def analyze_video(self, url: str, include_comments: bool = True) -> Dict[str, Any]:
        """영상 종합 분석"""
        analysis = {
            'metadata': {},
            'comments': [],
            'analysis_timestamp': datetime.now().isoformat()
        }
        
        # 메타데이터 수집
        metadata = self.get_video_metadata(url)
        if not metadata:
            logger.error("메타데이터 수집 실패")
            return analysis
        
        analysis['metadata'] = metadata
        
        # 댓글 수집
        if include_comments and self.youtube_api:
            video_id = metadata.get('video_id')
            if video_id:
                comments = self.get_top_comments(video_id)
                analysis['comments'] = comments
                
                # 댓글 통계
                if comments:
                    total_likes = sum(c.get('likes', 0) for c in comments)
                    avg_likes = total_likes / len(comments) if comments else 0
                    
                    analysis['comment_stats'] = {
                        'total_comments': len(comments),
                        'total_likes': total_likes,
                        'average_likes': avg_likes,
                        'most_liked': max(comments, key=lambda x: x.get('likes', 0)) if comments else None
                    }
        
        return analysis


if __name__ == "__main__":
    # 테스트
    analyzer = YouTubeAnalyzer()
    
    test_url = "https://www.youtube.com/watch?v=-K3Q557ZDfU"
    
    print("메타데이터 수집 중...")
    result = analyzer.analyze_video(test_url, include_comments=False)
    
    if result['metadata']:
        print(f"\n영상 제목: {result['metadata'].get('title')}")
        print(f"채널: {result['metadata'].get('channel')}")
        print(f"조회수: {result['metadata'].get('views'):,}")
        print(f"길이: {result['metadata'].get('duration')} 초")
        print(f"좋아요: {result['metadata'].get('like_count', 'N/A')}")
    
    # JSON 파일로 저장
    output_file = Path("video_analysis.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n분석 결과 저장: {output_file}")