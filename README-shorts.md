# ETF Shorts 자동화 실행 가이드

## 1. 환경 파일 준비
`.env.example`를 복사해서 `.env`를 만들고 값을 채우세요.

```bash
cp .env.example .env
```

최소 필수값:

```env
GEMINI_API_KEY=실제_Gemini_API_키
YOUTUBE_CLIENT_SECRETS_FILE=client_secret.json
YOUTUBE_TOKEN_FILE=.secrets/youtube-token.json
YOUTUBE_PRIVACY_STATUS=private
SHORTS_SCHEDULE_HOUR=9
SHORTS_SCHEDULE_MINUTE=0
```

## 2. 실행
이 스크립트는 처음 실행 시 자동으로 가상환경을 만들고, 필요한 Python 패키지를 설치합니다.

```bash
./run_daily_shorts.sh
```

## 3. 결과물
- 영상: `final_shorts/*.mp4`
- 업로드 메타데이터: `final_shorts/*.json`

## 4. YouTube 업로드 설정
1. Google Cloud Console에서 YouTube Data API v3를 활성화합니다.
2. OAuth 클라이언트(Desktop app)를 만들고 JSON을 내려받아 `client_secret.json`으로 저장합니다.
3. `.env`의 `YOUTUBE_CLIENT_SECRETS_FILE` 경로를 맞춥니다.
4. 첫 실행 시 브라우저 인증이 열리며, 성공하면 토큰이 `.secrets/youtube-token.json`에 저장됩니다.

## 5. 현재 상태
- 영상 생성 파이프라인: 준비됨
- YouTube 업로드: 연결됨 (OAuth 파일 필요)
- 일일 자동 실행: 아직 cron 등록 필요
