# Shot

ETF/경제 뉴스 기반 YouTube Shorts 자동화 작업 저장소입니다.

현재 초점은 국내/해외 ETF 소재를 짧은 스크립트, 장면 이미지, 남자 내레이션, 쇼츠 레이아웃, 썸네일, 업로드 메타데이터까지 하나의 제작 흐름으로 묶는 것입니다.

## Current Pipeline

1. 경제/ETF 소재 수집 또는 수동 입력
2. LLM 기반 스크립트 작성 및 장면 분리
3. 장면별 이미지 프롬프트 작성
4. 이미지 생성 API로 배경/일러스트 생성
5. TTS로 남자 내레이션 생성
6. Remotion 또는 Pillow+FFmpeg로 720x1280 쇼츠 렌더링
7. 고조회 쇼츠형 썸네일 제작
8. YouTube 업로드용 제목, 설명, 태그 작성

## Important Paths

- `media_agent/src/`: 파이프라인 Python 로직
- `media_agent/remotion/`: Remotion 기반 쇼츠 렌더링 템플릿
- `media_agent/data_shorts/scripts/`: 쇼츠 스크립트 JSON 예시
- `media_agent/data_shorts/scenes/`: 장면 분리 JSON 예시
- `media_agent/data_shorts/metadata/`: 업로드용 메타데이터
- `docs/`: 작업 회고, 의사결정, 문제 해결 기록

## Setup

```bash
cp .env.example .env
python3 -m venv .venv-shorts
.venv-shorts/bin/pip install -r requirements-shorts.txt
```

Then fill the required API keys in `.env`.

## Run

```bash
./run_daily_shorts.sh
```

The script generates metadata and can upload to YouTube when OAuth credentials are configured.

## Notes

Generated videos, local credentials, OAuth tokens, virtual environments, and private workspace memory are intentionally excluded from Git.

