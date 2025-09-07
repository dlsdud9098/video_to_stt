1. 프로젝트 위치  
  우분투: /home/apic/python/video_to_stt  

2. 파이썬: UV 사용(.venv)  

3. 테스트용 파일을 만들지 말 것. 만약 만들어야 한다면 테스트 후 바로 삭제할 것.  

4. 5. 대화 일지 자동 저장 규칙:  
   - 사용자와의 각 대화(하나의 질문-응답 쌍)가 끝날 때마다 반드시 일지 저장  
   - 저장 경로: /home/apic/Documents/gltr_days/일지/YYYY-MM-DD/  
   - 파일명 형식: NNN_작업요약.md (NNN은 001부터 시작하는 순번)  
   - 기존 파일 개수를 확인하여 다음 번호로 자동 생성  
   - 예: 001_웹툰생성.md, 002_설정확인.md, 003_코드수정.md ...  
   - 짧은 대화도 모두 기록 (예: "안녕" → 003_인사.md)  
1  
5. 응답이 끝나면 https://github.com/dlsdud9098/video_to_stt 여기에 commit & push 할 것  