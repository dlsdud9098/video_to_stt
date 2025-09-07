# Video to Subtitle UI

## 실행 방법

### 1. 백엔드 서버 실행

```bash
# 백엔드 디렉토리로 이동
cd backend

# 의존성 설치 (처음 한 번만)
pip install -r requirements.txt

# FastAPI 서버 실행
python app.py
```

서버가 http://localhost:8000 에서 실행됩니다.

### 2. 프론트엔드 실행

새 터미널을 열고:

```bash
# 프론트엔드 디렉토리로 이동
cd frontend

# React 개발 서버 실행
npm start
```

브라우저에서 http://localhost:3000 으로 접속합니다.

## 기능

- 드래그 앤 드롭 또는 파일 선택으로 비디오 업로드
- Whisper 모델 크기 선택 (Tiny, Base, Small, Medium, Large)
- 언어 설정 (자동 감지 또는 수동 지정)
- 자막 형식 선택 (SRT, JSON, TXT)
- 영어 번역 옵션
- 실시간 진행 상황 표시 (WebSocket)
- 자막 파일 다운로드

## 주의사항

- 백엔드 서버가 먼저 실행되어야 합니다
- CUDA가 설치되어 있으면 자동으로 GPU를 사용합니다
- 큰 비디오 파일은 처리 시간이 오래 걸릴 수 있습니다