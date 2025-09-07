#!/usr/bin/env python3
"""
영상 프레임 분석 및 OCR 텍스트 추출
"""

import cv2
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
from PIL import Image
import easyocr
import torch
from collections import Counter
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VideoFrameAnalyzer:
    def __init__(self, languages: List[str] = None):
        """
        영상 프레임 분석기
        
        Args:
            languages: OCR 인식 언어 리스트 (기본: 한국어, 영어)
        """
        if languages is None:
            languages = ['ko', 'en']
        
        # GPU 사용 가능 여부 확인
        self.use_gpu = torch.cuda.is_available()
        logger.info(f"OCR GPU 사용: {self.use_gpu}")
        
        # EasyOCR 초기화
        try:
            self.reader = easyocr.Reader(languages, gpu=self.use_gpu)
            logger.info(f"EasyOCR 초기화 완료: 언어={languages}")
        except Exception as e:
            logger.error(f"EasyOCR 초기화 실패: {e}")
            self.reader = None
    
    def extract_frames(self, video_path: str, 
                      frame_interval: float = 1.0,
                      max_frames: int = 30) -> List[np.ndarray]:
        """
        영상에서 프레임 추출
        
        Args:
            video_path: 영상 파일 경로
            frame_interval: 프레임 추출 간격 (초)
            max_frames: 최대 추출 프레임 수
        
        Returns:
            추출된 프레임 리스트
        """
        frames = []
        cap = cv2.VideoCapture(str(video_path))
        
        if not cap.isOpened():
            logger.error(f"영상 파일을 열 수 없습니다: {video_path}")
            return frames
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_step = int(fps * frame_interval)
        
        logger.info(f"영상 정보: FPS={fps:.1f}, 총 프레임={total_frames}")
        
        frame_count = 0
        extracted_count = 0
        
        while cap.isOpened() and extracted_count < max_frames:
            ret, frame = cap.read()
            
            if not ret:
                break
            
            if frame_count % frame_step == 0:
                frames.append(frame)
                extracted_count += 1
                logger.debug(f"프레임 {frame_count} 추출 ({extracted_count}/{max_frames})")
            
            frame_count += 1
        
        cap.release()
        logger.info(f"총 {len(frames)}개 프레임 추출 완료")
        
        return frames
    
    def extract_text_from_frame(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        단일 프레임에서 텍스트 추출
        
        Args:
            frame: 영상 프레임 (numpy array)
        
        Returns:
            추출된 텍스트 정보 리스트
        """
        if self.reader is None:
            return []
        
        try:
            # OCR 수행
            results = self.reader.readtext(frame)
            
            text_info = []
            for (bbox, text, prob) in results:
                if prob > 0.5:  # 신뢰도 50% 이상만
                    text_info.append({
                        'text': text,
                        'confidence': prob,
                        'bbox': bbox
                    })
            
            return text_info
            
        except Exception as e:
            logger.error(f"OCR 처리 실패: {e}")
            return []
    
    def analyze_video_frames(self, video_path: str) -> Dict[str, Any]:
        """
        영상 전체 프레임 분석 및 OCR
        
        Args:
            video_path: 영상 파일 경로
        
        Returns:
            분석 결과
        """
        # 프레임 추출
        frames = self.extract_frames(video_path)
        
        if not frames:
            logger.warning("추출된 프레임이 없습니다")
            return {'texts': [], 'frame_count': 0}
        
        # 각 프레임에서 텍스트 추출
        all_texts = []
        text_counter = Counter()
        
        for i, frame in enumerate(frames):
            logger.info(f"프레임 {i+1}/{len(frames)} 분석 중...")
            
            text_info = self.extract_text_from_frame(frame)
            
            for info in text_info:
                text = info['text']
                all_texts.append(info)
                text_counter[text] += 1
        
        # 자주 등장하는 텍스트 정렬
        frequent_texts = [
            {'text': text, 'count': count}
            for text, count in text_counter.most_common(20)
        ]
        
        # 시간대별 텍스트 그룹화
        timeline_texts = self._group_texts_by_time(all_texts, len(frames))
        
        analysis_result = {
            'total_frames_analyzed': len(frames),
            'total_texts_found': len(all_texts),
            'unique_texts': len(text_counter),
            'frequent_texts': frequent_texts,
            'timeline_texts': timeline_texts,
            'all_texts': all_texts[:100]  # 최대 100개만 저장
        }
        
        logger.info(f"프레임 분석 완료: {len(all_texts)}개 텍스트 발견")
        
        return analysis_result
    
    def _group_texts_by_time(self, texts: List[Dict], 
                             frame_count: int) -> Dict[str, List[str]]:
        """텍스트를 시간대별로 그룹화"""
        
        if frame_count == 0:
            return {}
        
        # 3개 구간으로 나누기
        segments = {
            'beginning': [],
            'middle': [],
            'end': []
        }
        
        segment_size = frame_count // 3
        
        for i, text_info in enumerate(texts):
            frame_idx = i * frame_count // len(texts) if texts else 0
            
            if frame_idx < segment_size:
                segments['beginning'].append(text_info.get('text', ''))
            elif frame_idx < segment_size * 2:
                segments['middle'].append(text_info.get('text', ''))
            else:
                segments['end'].append(text_info.get('text', ''))
        
        # 중복 제거
        for key in segments:
            segments[key] = list(set(segments[key]))[:10]  # 각 구간당 최대 10개
        
        return segments
    
    def detect_scene_changes(self, frames: List[np.ndarray], 
                            threshold: float = 30.0) -> List[int]:
        """
        장면 전환 감지
        
        Args:
            frames: 프레임 리스트
            threshold: 장면 전환 임계값
        
        Returns:
            장면 전환이 감지된 프레임 인덱스 리스트
        """
        scene_changes = []
        
        for i in range(1, len(frames)):
            # 프레임 간 차이 계산
            diff = cv2.absdiff(frames[i-1], frames[i])
            mean_diff = np.mean(diff)
            
            if mean_diff > threshold:
                scene_changes.append(i)
        
        logger.info(f"{len(scene_changes)}개 장면 전환 감지")
        return scene_changes


class AdvancedVideoAnalyzer:
    """고급 영상 분석기 (OCR + 음성 + 메타데이터 통합)"""
    
    def __init__(self):
        self.frame_analyzer = VideoFrameAnalyzer()
        
        # 기존 모듈 임포트
        from subtitle_generator import SubtitleGenerator
        from audio_extractor import AudioExtractor
        
        self.audio_extractor = AudioExtractor()
        self.subtitle_generator = SubtitleGenerator(model_size="large-v3")
    
    def comprehensive_analysis(self, video_path: str) -> Dict[str, Any]:
        """
        영상 종합 분석
        
        Args:
            video_path: 영상 파일 경로
        
        Returns:
            종합 분석 결과
        """
        logger.info(f"종합 분석 시작: {video_path}")
        
        analysis = {}
        
        # 1. 프레임 분석 및 OCR
        logger.info("1. 프레임 분석 중...")
        frame_analysis = self.frame_analyzer.analyze_video_frames(video_path)
        analysis['ocr'] = frame_analysis
        
        # 2. 음성 추출 및 텍스트 변환
        logger.info("2. 음성 분석 중...")
        try:
            audio_path = self.audio_extractor.extract_audio(str(video_path))
            transcription_result = self.subtitle_generator.transcribe_audio(audio_path)
            
            analysis['audio'] = {
                'transcription': transcription_result.get('text', ''),
                'language': transcription_result.get('language', 'unknown'),
                'segments': transcription_result.get('segments', [])
            }
            
            # 음성 파일 정리
            Path(audio_path).unlink(missing_ok=True)
            
        except Exception as e:
            logger.error(f"음성 분석 실패: {e}")
            analysis['audio'] = {'transcription': '', 'language': 'unknown'}
        
        # 3. 시나리오 생성
        logger.info("3. 시나리오 생성 중...")
        analysis['scenario'] = self._generate_scenario(
            frame_analysis,
            analysis['audio']
        )
        
        logger.info("종합 분석 완료")
        return analysis
    
    def _generate_scenario(self, ocr_data: Dict, audio_data: Dict) -> str:
        """OCR과 음성 데이터를 바탕으로 시나리오 생성"""
        
        scenario_parts = []
        
        # 시작 부분
        beginning_texts = ocr_data.get('timeline_texts', {}).get('beginning', [])
        scenario_parts.append(f"""### 영상 시작 부분
- OCR 텍스트: {', '.join(beginning_texts[:5]) if beginning_texts else '텍스트 없음'}
- 음성: {audio_data.get('transcription', '')[:200]}
""")
        
        # 중간 부분
        middle_texts = ocr_data.get('timeline_texts', {}).get('middle', [])
        transcription = audio_data.get('transcription', '')
        scenario_parts.append(f"""### 영상 중간 부분
- OCR 텍스트: {', '.join(middle_texts[:5]) if middle_texts else '텍스트 없음'}
- 음성: {transcription[200:400] if len(transcription) > 200 else ''}
""")
        
        # 끝 부분
        end_texts = ocr_data.get('timeline_texts', {}).get('end', [])
        scenario_parts.append(f"""### 영상 끝 부분
- OCR 텍스트: {', '.join(end_texts[:5]) if end_texts else '텍스트 없음'}
- 음성: {transcription[400:] if len(transcription) > 400 else ''}
""")
        
        # 주요 키워드
        frequent_texts = [item['text'] for item in ocr_data.get('frequent_texts', [])[:10]]
        scenario_parts.append(f"""### 주요 키워드
OCR: {', '.join(frequent_texts) if frequent_texts else '없음'}
언어: {audio_data.get('language', 'unknown')}
""")
        
        return '\n'.join(scenario_parts)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python video_frame_analyzer.py <video_file>")
        sys.exit(1)
    
    analyzer = AdvancedVideoAnalyzer()
    result = analyzer.comprehensive_analysis(sys.argv[1])
    
    # 결과 출력
    print("\n=== 영상 종합 분석 결과 ===")
    print(result['scenario'])
    
    # JSON 파일로 저장
    output_file = Path(sys.argv[1]).stem + "_analysis.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n분석 결과 저장: {output_file}")