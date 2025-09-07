# YouTube Video to Text Converter & Dataset Creator

YouTube 영상을 다운로드하고 음성을 텍스트로 변환하며, 댓글과 함께 데이터셋을 생성하는 종합 도구입니다.

## 🚀 주요 기능

### 1. 기본 기능
- **YouTube 영상 다운로드**: YouTube URL에서 영상 자동 다운로드
- **음성 추출**: 영상에서 음성 트랙 분리
- **고정확도 음성-텍스트 변환**: OpenAI Whisper 모델 사용 (large-v3 기본)
- **다양한 출력 형식**: TXT, SRT (자막), JSON 지원

### 2. 데이터셋 생성 기능 (NEW!)
- **영상 종합 분석**: 메타데이터, 음성, OCR 텍스트 통합 분석
- **댓글 수집**: YouTube Data API를 통한 인기 댓글 수집
- **OCR 텍스트 추출**: 영상 프레임에서 텍스트 추출
- **JSONL 데이터셋**: 학습용 데이터셋 자동 생성

## 📦 설치 방법

```bash
# 1. 저장소 클론
git clone https://github.com/yourusername/video_to_stt.git
cd video_to_stt

# 2. Python 환경 설정 (Python 3.10+ 필요)
# uv 사용 시:
uv sync

# 또는 pip 사용 시:
pip install -r requirements.txt

# 3. ffmpeg 설치 (필수)
# Windows: https://ffmpeg.org/download.html
# Mac: brew install ffmpeg
# Linux: sudo apt-get install ffmpeg
```

## 🎯 사용법

### 1. 간단한 텍스트 변환

```bash
# YouTube 영상을 텍스트로 변환 (최고 정확도)
python youtube_to_text.py https://youtube.com/watch?v=VIDEO_ID

# 모델 선택
python youtube_to_text.py URL --model medium

# 언어 지정
python youtube_to_text.py URL --language ko
```

### 2. 데이터셋 생성 (영상 분석 + 댓글)

```bash
# 단일 영상으로 데이터셋 생성
python create_dataset.py https://youtube.com/shorts/VIDEO_ID

# 여러 영상 처리
python create_dataset.py URL1 URL2 URL3

# YouTube API 키와 함께 (댓글 수집)
python create_dataset.py URL --api-key YOUR_API_KEY

# OCR 없이 빠른 처리
python create_dataset.py URL --no-ocr

# 다운로드 파일 보관
python create_dataset.py URL --keep-files
```

### 3. YouTube API 키 설정

댓글 수집을 위해서는 YouTube Data API v3 키가 필요합니다:

1. [Google Cloud Console](https://console.cloud.google.com/) 접속
2. 새 프로젝트 생성 또는 기존 프로젝트 선택
3. YouTube Data API v3 활성화
4. 인증 정보 > API 키 생성
5. 환경 변수 설정:
   ```bash
   export YOUTUBE_API_KEY="your-api-key-here"
   ```

## 📊 출력 데이터 형식

### JSONL 데이터셋 구조

```json
{
  "input": "영상 분석 내용 (시나리오, OCR, 음성 텍스트 등)",
  "output": "상위 댓글 텍스트",
  "metadata": {
    "video_id": "VIDEO_ID",
    "title": "영상 제목",
    "channel": "채널명",
    "views": 조회수,
    "duration": 영상길이,
    "language": "감지된 언어"
  }
}
```

## 🎛️ Whisper 모델 선택 가이드

| 모델 | 파라미터 | 정확도 | VRAM 요구사항 | 속도 |
|------|----------|--------|---------------|------|
| **large-v3** | 1550M | ⭐⭐⭐⭐⭐ (최고) | ~10GB | 느림 |
| large-v2 | 1550M | ⭐⭐⭐⭐⭐ | ~10GB | 느림 |
| medium | 769M | ⭐⭐⭐ | ~5GB | 보통 |
| small | 244M | ⭐⭐ | ~2GB | 빠름 |
| base | 74M | ⭐ | ~1GB | 매우 빠름 |
| tiny | 39M | ⭐ | ~1GB | 가장 빠름 |

## 📁 프로젝트 구조

```
video_to_stt/
├── create_dataset.py        # 데이터셋 생성 메인 스크립트 ⭐
├── youtube_to_text.py       # 간편 텍스트 변환 스크립트
├── youtube_analyzer.py      # YouTube 메타데이터 및 댓글 수집
├── video_frame_analyzer.py  # OCR 및 프레임 분석
├── video_downloader.py      # YouTube 다운로드 모듈
├── audio_extractor.py       # 음성 추출 모듈
├── subtitle_generator.py    # STT 및 자막 생성 모듈
├── main.py                  # 기본 실행 파일
├── downloads/               # 다운로드된 영상 저장
├── output/                  # 변환 결과 저장
└── *.jsonl                  # 생성된 데이터셋 파일
```

## ✨ 주요 특징

### 음성 인식
- **VAD (Voice Activity Detection)**: 음성 구간 자동 감지
- **Beam Search**: 정확한 텍스트 생성을 위한 빔 서치
- **GPU 가속**: CUDA 지원 시 자동 GPU 사용
- **다국어 지원**: 99개 언어 자동 감지 및 변환

### 영상 분석
- **OCR 텍스트 추출**: EasyOCR을 통한 프레임 텍스트 감지
- **시간대별 분석**: 영상을 구간별로 나누어 분석
- **장면 전환 감지**: 주요 장면 변화 포인트 감지

### 데이터셋
- **종합 분석**: 음성, 영상, 텍스트 통합 분석
- **댓글 매칭**: 영상 내용과 인기 댓글 매칭
- **학습 준비**: 바로 사용 가능한 JSONL 형식

## 🛠️ 시스템 요구사항

- Python 3.10 이상
- ffmpeg
- CUDA 지원 GPU (선택사항, 속도 향상)
- RAM: 최소 8GB (large 모델 사용 시 16GB 권장)
- 저장공간: 영상 다운로드를 위한 충분한 공간

## 🔧 문제 해결

### GPU 메모리 부족
```bash
# 더 작은 모델 사용
python create_dataset.py URL --model medium
```

### 다운로드 실패
- YouTube URL 확인
- pytube 업데이트: `pip install --upgrade pytube`

### OCR 설치 문제
```bash
# EasyOCR 재설치
pip install --upgrade easyocr
```

### API 할당량 초과
- YouTube Data API 일일 할당량 확인
- 댓글 수집 없이 진행: API 키 제외

## 📝 예제

### 전체 파이프라인 실행
```bash
# YouTube 쇼츠 10개로 데이터셋 생성
python create_dataset.py \
  https://youtube.com/shorts/xxx1 \
  https://youtube.com/shorts/xxx2 \
  https://youtube.com/shorts/xxx3 \
  --api-key YOUR_KEY \
  --output my_dataset.jsonl \
  --model large-v3
```

## 📜 라이선스

MIT License

## 🤝 기여

Issues와 Pull Requests를 환영합니다!