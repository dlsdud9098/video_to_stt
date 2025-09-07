#!/usr/bin/env python3
"""
YouTube 쇼츠 데이터셋 생성 도구
영상 분석 + 댓글 수집 → JSONL 형식 데이터셋
"""

import json
import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 커스텀 모듈
from youtube_analyzer import YouTubeAnalyzer
from video_frame_analyzer import AdvancedVideoAnalyzer
from video_downloader import VideoDownloader
from audio_extractor import AudioExtractor
from subtitle_generator import SubtitleGenerator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class YouTubeShortsDatasetCreator:
    """YouTube 쇼츠 데이터셋 생성기"""
    
    def __init__(self, api_key: Optional[str] = None, 
                 use_ocr: bool = True,
                 model_size: str = "large-v3"):
        """
        초기화
        
        Args:
            api_key: YouTube Data API v3 키 (댓글 수집용)
            use_ocr: OCR 사용 여부
            model_size: Whisper 모델 크기
        """
        self.api_key = api_key or os.getenv('YOUTUBE_API_KEY')
        self.use_ocr = use_ocr
        
        # 분석 도구 초기화
        self.youtube_analyzer = YouTubeAnalyzer(api_key=self.api_key)
        self.downloader = VideoDownloader()
        self.audio_extractor = AudioExtractor()
        self.subtitle_generator = SubtitleGenerator(model_size=model_size)
        
        if use_ocr:
            try:
                self.video_analyzer = AdvancedVideoAnalyzer()
                logger.info("OCR 기능 활성화됨")
            except Exception as e:
                logger.warning(f"OCR 초기화 실패, OCR 없이 진행: {e}")
                self.use_ocr = False
                self.video_analyzer = None
        else:
            self.video_analyzer = None
    
    def process_single_video(self, url: str, 
                           keep_files: bool = False) -> List[Dict[str, Any]]:
        """
        단일 영상 처리
        
        Args:
            url: YouTube 영상 URL
            keep_files: 다운로드 파일 보관 여부
        
        Returns:
            JSONL 데이터 항목 리스트
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"영상 처리 시작: {url}")
        logger.info(f"{'='*60}")
        
        try:
            # 1. 메타데이터 수집
            logger.info("[1/6] 메타데이터 수집 중...")
            metadata = self.youtube_analyzer.get_video_metadata(url)
            if not metadata:
                logger.error("메타데이터 수집 실패")
                return []
            
            video_id = metadata.get('video_id')
            title = metadata.get('title', 'Unknown')
            
            logger.info(f"제목: {title}")
            logger.info(f"채널: {metadata.get('channel')}")
            logger.info(f"조회수: {metadata.get('views'):,}")
            
            # 2. 댓글 수집
            logger.info("[2/6] 댓글 수집 중...")
            comments = []
            if video_id and self.api_key:
                comments = self.youtube_analyzer.get_top_comments(video_id, max_results=50)
                logger.info(f"수집된 댓글: {len(comments)}개")
            else:
                logger.warning("API 키가 없어 댓글을 수집할 수 없습니다")
            
            # 3. 영상 다운로드
            logger.info("[3/6] 영상 다운로드 중...")
            video_path = self.downloader.download_video(url)
            if not video_path:
                logger.error("영상 다운로드 실패")
                return []
            
            # 4. 음성 추출 및 텍스트 변환
            logger.info("[4/6] 음성 추출 및 텍스트 변환 중...")
            audio_path = self.audio_extractor.extract_audio(str(video_path))
            transcription_result = self.subtitle_generator.transcribe_audio(audio_path)
            transcription = transcription_result.get('text', '')
            detected_language = transcription_result.get('language', 'unknown')
            
            logger.info(f"감지된 언어: {detected_language}")
            logger.info(f"텍스트 길이: {len(transcription)} 문자")
            
            # 5. OCR 분석 (선택사항)
            ocr_analysis = {}
            if self.use_ocr and self.video_analyzer:
                logger.info("[5/6] 영상 프레임 OCR 분석 중...")
                try:
                    full_analysis = self.video_analyzer.comprehensive_analysis(str(video_path))
                    ocr_analysis = full_analysis.get('ocr', {})
                    logger.info(f"OCR 텍스트 발견: {ocr_analysis.get('total_texts_found', 0)}개")
                except Exception as e:
                    logger.warning(f"OCR 분석 실패: {e}")
            
            # 6. 데이터 포맷팅
            logger.info("[6/6] 데이터 포맷팅 중...")
            dataset_items = self._format_dataset_items(
                metadata=metadata,
                transcription=transcription,
                comments=comments,
                ocr_data=ocr_analysis,
                language=detected_language
            )
            
            # 파일 정리
            if not keep_files:
                if video_path.exists():
                    os.remove(video_path)
                if Path(audio_path).exists():
                    os.remove(audio_path)
                logger.info("임시 파일 정리 완료")
            
            logger.info(f"✅ 처리 완료: {len(dataset_items)}개 데이터 항목 생성")
            return dataset_items
            
        except Exception as e:
            logger.error(f"영상 처리 중 오류: {e}")
            return []
    
    def _format_dataset_items(self, metadata: Dict, transcription: str,
                             comments: List[Dict], ocr_data: Dict,
                             language: str) -> List[Dict]:
        """데이터셋 항목 포맷팅"""
        
        # 영상 분석 텍스트 생성
        analysis_text = self._generate_analysis_text(
            metadata, transcription, ocr_data, language
        )
        
        # 상위 댓글 선택 (좋아요 순)
        top_comments = sorted(
            comments, 
            key=lambda x: x.get('likes', 0), 
            reverse=True
        )[:10]  # 상위 10개
        
        # 각 댓글에 대해 데이터 항목 생성
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
                    'language': language,
                    'comment_likes': comment.get('likes', 0)
                }
            })
        
        return dataset_items
    
    def _generate_analysis_text(self, metadata: Dict, transcription: str,
                               ocr_data: Dict, language: str) -> str:
        """영상 분석 텍스트 생성"""
        
        title = metadata.get('title', 'Unknown')
        duration = metadata.get('duration', 0)
        
        # OCR 텍스트 정리
        ocr_texts = []
        if ocr_data:
            frequent = ocr_data.get('frequent_texts', [])
            ocr_texts = [item['text'] for item in frequent[:10]]
        
        # 시간대별 시나리오
        scenario = self._create_timeline_scenario(
            transcription, ocr_data, duration
        )
        
        # 분석 텍스트 조합
        analysis = f"""## 유튜브 쇼츠 영상 분석: {title}

### 1. 시간대별 상세 시나리오
{scenario}

### 2. 영상 종합 분석

* **핵심 주제 및 메시지:** {self._extract_main_theme(transcription, title)}

* **시각적 특징:** {self._describe_visual_features(ocr_data)}

* **청각적 특징:** {self._describe_audio_features(transcription, language)}

### 3. 주요 키워드
{self._extract_keywords(metadata, transcription, ocr_texts)}
"""
        
        return analysis
    
    def _create_timeline_scenario(self, transcription: str, 
                                 ocr_data: Dict, duration: int) -> str:
        """시간대별 시나리오 생성"""
        
        segments = []
        segment_duration = max(duration // 3, 5)
        
        # OCR 시간대별 텍스트
        timeline_texts = ocr_data.get('timeline_texts', {}) if ocr_data else {}
        
        # 시작 부분
        beginning_ocr = timeline_texts.get('beginning', [])
        trans_start = transcription[:300] if transcription else ""
        
        segments.append(f"""* **[00:00-00:{segment_duration:02d}]:**
    - **시각 정보:** {', '.join(beginning_ocr[:5]) if beginning_ocr else '영상 시작 장면'}
    - **청각 정보:** {trans_start if trans_start else '음성 없음'}""")
        
        # 중간 부분
        if duration > 15:
            middle_ocr = timeline_texts.get('middle', [])
            trans_middle = transcription[300:600] if len(transcription) > 300 else ""
            
            segments.append(f"""* **[00:{segment_duration:02d}-00:{segment_duration*2:02d}]:**
    - **시각 정보:** {', '.join(middle_ocr[:5]) if middle_ocr else '영상 중간 장면'}
    - **청각 정보:** {trans_middle if trans_middle else '계속'}""")
        
        # 끝 부분
        end_ocr = timeline_texts.get('end', [])
        trans_end = transcription[600:] if len(transcription) > 600 else transcription[300:]
        
        segments.append(f"""* **[00:{segment_duration*2 if duration > 15 else segment_duration:02d}-끝]:**
    - **시각 정보:** {', '.join(end_ocr[:5]) if end_ocr else '영상 마무리 장면'}
    - **청각 정보:** {trans_end if trans_end else '마무리'}""")
        
        return '\n'.join(segments)
    
    def _extract_main_theme(self, transcription: str, title: str) -> str:
        """주요 주제 추출"""
        if not transcription:
            return f"{title}에 대한 영상"
        
        # 간단한 주제 추출 (실제로는 더 정교한 NLP 필요)
        words = transcription.split()[:50]
        return f"{title} - {' '.join(words[:20])}..." if words else title
    
    def _describe_visual_features(self, ocr_data: Dict) -> str:
        """시각적 특징 설명"""
        if not ocr_data:
            return "영상의 시각적 구성 분석"
        
        text_count = ocr_data.get('total_texts_found', 0)
        if text_count > 50:
            return "텍스트가 많은 정보성 영상, 자막과 그래픽 요소 다수 포함"
        elif text_count > 20:
            return "적절한 텍스트와 시각적 요소의 균형"
        else:
            return "비주얼 중심의 영상, 최소한의 텍스트"
    
    def _describe_audio_features(self, transcription: str, language: str) -> str:
        """청각적 특징 설명"""
        if not transcription:
            return "배경음악 또는 효과음 중심"
        
        word_count = len(transcription.split())
        if word_count > 200:
            return f"대화/나레이션 중심 ({language}), 정보 전달 목적"
        elif word_count > 50:
            return f"적절한 나레이션과 배경음 ({language})"
        else:
            return f"짧은 멘트와 효과음 중심 ({language})"
    
    def _extract_keywords(self, metadata: Dict, transcription: str, 
                         ocr_texts: List[str]) -> str:
        """키워드 추출"""
        keywords = []
        
        # 메타데이터 키워드
        if metadata.get('keywords'):
            keywords.extend(metadata['keywords'][:5])
        
        # OCR 키워드
        keywords.extend(ocr_texts[:5])
        
        # 제목에서 키워드
        title_words = metadata.get('title', '').split()
        keywords.extend([w for w in title_words if len(w) > 3][:3])
        
        # 중복 제거 및 정리
        unique_keywords = []
        seen = set()
        for kw in keywords:
            if kw.lower() not in seen:
                unique_keywords.append(kw)
                seen.add(kw.lower())
        
        return ', '.join(unique_keywords[:15]) if unique_keywords else "shorts, video"
    
    def create_dataset(self, urls: List[str], 
                       output_file: str = "shorts_dataset.jsonl",
                       keep_files: bool = False):
        """
        여러 영상으로 데이터셋 생성
        
        Args:
            urls: YouTube 영상 URL 리스트
            output_file: 출력 JSONL 파일명
            keep_files: 다운로드 파일 보관 여부
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"데이터셋 생성 시작")
        logger.info(f"총 {len(urls)}개 영상 처리 예정")
        logger.info(f"{'='*60}")
        
        all_items = []
        success_count = 0
        
        for i, url in enumerate(urls, 1):
            logger.info(f"\n[{i}/{len(urls)}] 처리 중...")
            
            try:
                items = self.process_single_video(url, keep_files)
                if items:
                    all_items.extend(items)
                    success_count += 1
                    logger.info(f"성공: {len(items)}개 항목 추가")
                else:
                    logger.warning(f"실패: 데이터 생성 실패")
                    
            except Exception as e:
                logger.error(f"오류 발생: {e}")
                continue
        
        # JSONL 파일로 저장
        if all_items:
            with open(output_file, 'w', encoding='utf-8') as f:
                for item in all_items:
                    f.write(json.dumps(item, ensure_ascii=False) + '\n')
            
            logger.info(f"\n{'='*60}")
            logger.info(f"✅ 데이터셋 생성 완료!")
            logger.info(f"파일: {output_file}")
            logger.info(f"성공: {success_count}/{len(urls)} 영상")
            logger.info(f"총 데이터: {len(all_items)}개 항목")
            logger.info(f"{'='*60}")
        else:
            logger.error("생성된 데이터가 없습니다")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="YouTube 쇼츠 분석 데이터셋 생성",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예제:
  # 단일 영상 처리
  python create_dataset.py https://youtube.com/shorts/xxx
  
  # 여러 영상 처리
  python create_dataset.py URL1 URL2 URL3
  
  # API 키와 함께 (댓글 수집)
  python create_dataset.py URL --api-key YOUR_API_KEY
  
  # OCR 비활성화 (빠른 처리)
  python create_dataset.py URL --no-ocr
  
  # 파일 보관
  python create_dataset.py URL --keep-files
        """
    )
    
    parser.add_argument(
        "urls",
        nargs='+',
        help="YouTube 영상 URL(들)"
    )
    parser.add_argument(
        "--api-key",
        help="YouTube Data API v3 키 (댓글 수집용)"
    )
    parser.add_argument(
        "--output",
        default="shorts_dataset.jsonl",
        help="출력 JSONL 파일명 (기본: shorts_dataset.jsonl)"
    )
    parser.add_argument(
        "--no-ocr",
        action="store_true",
        help="OCR 분석 비활성화 (빠른 처리)"
    )
    parser.add_argument(
        "--model",
        default="large-v3",
        choices=["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"],
        help="Whisper 모델 크기 (기본: large-v3)"
    )
    parser.add_argument(
        "--keep-files",
        action="store_true",
        help="다운로드한 영상 파일 보관"
    )
    
    args = parser.parse_args()
    
    # API 키 설정
    if args.api_key:
        os.environ['YOUTUBE_API_KEY'] = args.api_key
    
    # 데이터셋 생성기 초기화
    creator = YouTubeShortsDatasetCreator(
        api_key=args.api_key,
        use_ocr=not args.no_ocr,
        model_size=args.model
    )
    
    # 데이터셋 생성
    creator.create_dataset(
        urls=args.urls,
        output_file=args.output,
        keep_files=args.keep_files
    )


if __name__ == "__main__":
    main()