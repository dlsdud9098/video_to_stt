#!/usr/bin/env python3
"""
YouTube 영상 종합 분석 시스템
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
from pytube import YouTube
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
        # URL 파라미터 제거
        url = url.split('?')[0] if '?' in url else url
        
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
        """영상 메타데이터 수집"""
        try:
            # Shorts URL을 일반 watch URL로 변환
            video_id = self.extract_video_id(url)
            if video_id and 'shorts' in url:
                url = f'https://www.youtube.com/watch?v={video_id}'
            
            yt = YouTube(url)
            
            metadata = {
                'video_id': self.extract_video_id(url),
                'title': yt.title,
                'channel': yt.author,
                'channel_id': yt.channel_id,
                'description': yt.description,
                'duration': yt.length,
                'views': yt.views,
                'publish_date': yt.publish_date.isoformat() if yt.publish_date else None,
                'thumbnail_url': yt.thumbnail_url,
                'keywords': yt.keywords,
                'rating': yt.rating if hasattr(yt, 'rating') else None,
                'url': url
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
            request = self.youtube_api.commentThreads().list(
                part='snippet',
                videoId=video_id,
                maxResults=min(max_results, 100),
                order='relevance'  # 인기순 정렬
            )
            
            response = request.execute()
            
            for item in response.get('items', []):
                comment = item['snippet']['topLevelComment']['snippet']
                comments.append({
                    'text': comment['textDisplay'],
                    'author': comment['authorDisplayName'],
                    'likes': comment['likeCount'],
                    'published_at': comment['publishedAt'],
                    'updated_at': comment.get('updatedAt', comment['publishedAt'])
                })
            
            logger.info(f"{len(comments)}개의 댓글 수집 완료")
            return comments
            
        except HttpError as e:
            logger.error(f"YouTube API 오류: {e}")
            return []
        except Exception as e:
            logger.error(f"댓글 수집 실패: {e}")
            return []
    
    def format_for_jsonl(self, metadata: Dict, transcription: str, 
                        comments: List[Dict], analysis: Optional[str] = None) -> Dict:
        """JSONL 형식으로 데이터 포맷팅"""
        
        # 상위 3개 댓글 선택
        top_comments = sorted(comments, key=lambda x: x.get('likes', 0), reverse=True)[:3]
        
        # 입력 데이터 생성 (영상 분석 내용)
        input_text = self._generate_analysis_text(metadata, transcription, analysis)
        
        # 출력 데이터 (상위 댓글)
        output_texts = [comment['text'] for comment in top_comments]
        
        # 여러 개의 데이터 항목 생성
        jsonl_items = []
        for comment_text in output_texts:
            jsonl_items.append({
                'input': input_text,
                'output': comment_text,
                'metadata': {
                    'video_id': metadata.get('video_id'),
                    'title': metadata.get('title'),
                    'channel': metadata.get('channel'),
                    'views': metadata.get('views'),
                    'duration': metadata.get('duration')
                }
            })
        
        return jsonl_items
    
    def _generate_analysis_text(self, metadata: Dict, transcription: str, 
                                analysis: Optional[str] = None) -> str:
        """영상 분석 텍스트 생성"""
        
        title = metadata.get('title', 'Unknown')
        duration = metadata.get('duration', 0)
        
        # 시간대별 시나리오 생성
        scenario = self._generate_timeline_scenario(transcription, duration)
        
        # 종합 분석
        comprehensive_analysis = f"""## 유튜브 쇼츠 영상 분석: {title}

### 1. 시간대별 상세 시나리오
{scenario}

### 2. 영상 종합 분석

* **핵심 주제 및 메시지:** {analysis or '영상의 주요 내용을 분석 중입니다.'}

* **시각적 특징:** 영상의 시각적 구성과 편집 스타일 분석

* **청각적 특징:** 배경음악, 효과음, 나레이션 등의 청각적 요소 분석

### 3. 주요 키워드
{', '.join(metadata.get('keywords', [])) if metadata.get('keywords') else '키워드 추출 중'}
"""
        
        return comprehensive_analysis
    
    def _generate_timeline_scenario(self, transcription: str, duration: int) -> str:
        """시간대별 시나리오 생성"""
        
        if not transcription:
            return "* 음성 텍스트가 없습니다."
        
        # 간단한 시간대 분할 (실제로는 더 정교한 분석 필요)
        segments = []
        
        # 영상을 3등분하여 시나리오 생성
        segment_duration = duration // 3 if duration > 0 else 10
        
        segments.append(f"""* **[00:00-00:{segment_duration:02d}]:**
    - **시각 정보:** 영상 시작 부분
    - **청각 정보:** {transcription[:200] if len(transcription) > 200 else transcription}
""")
        
        if len(transcription) > 200:
            segments.append(f"""* **[00:{segment_duration:02d}-00:{segment_duration*2:02d}]:**
    - **시각 정보:** 영상 중간 부분
    - **청각 정보:** {transcription[200:400] if len(transcription) > 400 else transcription[200:]}
""")
        
        if len(transcription) > 400:
            segments.append(f"""* **[00:{segment_duration*2:02d}-끝]:**
    - **시각 정보:** 영상 마지막 부분
    - **청각 정보:** {transcription[400:]}
""")
        
        return '\n'.join(segments)


class YouTubeDatasetBuilder:
    def __init__(self, api_key: Optional[str] = None):
        """
        YouTube 데이터셋 빌더
        
        Args:
            api_key: YouTube Data API v3 키
        """
        self.analyzer = YouTubeAnalyzer(api_key)
        
        # 기존 모듈 임포트
        from video_downloader import VideoDownloader
        from audio_extractor import AudioExtractor
        from subtitle_generator import SubtitleGenerator
        
        self.downloader = VideoDownloader()
        self.audio_extractor = AudioExtractor()
        self.subtitle_generator = SubtitleGenerator(model_size="large-v3")
    
    def process_video(self, url: str, output_dir: str = "dataset") -> List[Dict]:
        """
        단일 영상 처리 및 데이터셋 생성
        
        Args:
            url: YouTube 영상 URL
            output_dir: 출력 디렉토리
        
        Returns:
            JSONL 형식의 데이터 리스트
        """
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        logger.info(f"영상 처리 시작: {url}")
        
        # 1. 메타데이터 수집
        metadata = self.analyzer.get_video_metadata(url)
        if not metadata:
            logger.error("메타데이터 수집 실패")
            return []
        
        video_id = metadata.get('video_id')
        
        # 2. 댓글 수집
        comments = self.analyzer.get_top_comments(video_id) if video_id else []
        
        # 3. 영상 다운로드
        video_path = self.downloader.download_video(url)
        if not video_path:
            logger.error("영상 다운로드 실패")
            return []
        
        # 4. 음성 추출
        audio_path = self.audio_extractor.extract_audio(str(video_path))
        
        # 5. 음성 텍스트 변환
        result = self.subtitle_generator.transcribe_audio(audio_path)
        transcription = result.get('text', '')
        
        # 6. JSONL 데이터 생성
        jsonl_items = self.analyzer.format_for_jsonl(
            metadata, 
            transcription, 
            comments,
            analysis="영상 내용 분석 완료"
        )
        
        # 7. 파일 정리
        if video_path.exists():
            os.remove(video_path)
        if Path(audio_path).exists():
            os.remove(audio_path)
        
        logger.info(f"데이터 생성 완료: {len(jsonl_items)}개 항목")
        return jsonl_items
    
    def process_multiple_videos(self, urls: List[str], output_file: str = "dataset.jsonl"):
        """
        여러 영상 처리 및 JSONL 파일 생성
        
        Args:
            urls: YouTube 영상 URL 리스트
            output_file: 출력 JSONL 파일명
        """
        all_data = []
        
        for i, url in enumerate(urls, 1):
            logger.info(f"\n[{i}/{len(urls)}] 처리 중...")
            try:
                data_items = self.process_video(url)
                all_data.extend(data_items)
            except Exception as e:
                logger.error(f"영상 처리 실패: {e}")
                continue
        
        # JSONL 파일로 저장
        with open(output_file, 'w', encoding='utf-8') as f:
            for item in all_data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        
        logger.info(f"✅ 데이터셋 생성 완료: {output_file}")
        logger.info(f"   총 {len(all_data)}개 데이터 항목 생성")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="YouTube 영상 분석 및 데이터셋 생성"
    )
    parser.add_argument("urls", nargs='+', help="YouTube 영상 URL(들)")
    parser.add_argument(
        "--api-key",
        help="YouTube Data API v3 키 (댓글 수집용)"
    )
    parser.add_argument(
        "--output",
        default="shorts_dataset.jsonl",
        help="출력 JSONL 파일명"
    )
    
    args = parser.parse_args()
    
    # API 키 설정
    if args.api_key:
        os.environ['YOUTUBE_API_KEY'] = args.api_key
    
    # 데이터셋 빌더 생성
    builder = YouTubeDatasetBuilder(api_key=args.api_key)
    
    # 영상 처리
    builder.process_multiple_videos(args.urls, args.output)


if __name__ == "__main__":
    main()