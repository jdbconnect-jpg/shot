# 파이프라인 로직

## Overview

이 저장소의 쇼츠 제작 로직은 “데이터/뉴스 → 스크립트 → 장면 → 이미지/TTS → 렌더링 → 썸네일/메타데이터” 흐름이다.
반복 제작 시에는 docs/shorts-production-rules.md와 docs/shorts-video-playbook.md를 우선 적용한다.

## 1. Script

- 위치: `media_agent/data_shorts/scripts/`
- 역할:
  - 영상 제목
  - 톤
  - 출처
  - 순위/수치 데이터
  - 장면별 내레이션
- 최근 예시:
  - `scr_20260517_kr_etf_top5.json`
  - `scr_20260517_kr_etf_top3.json`

## 2. Scene Planning

- 위치: `media_agent/data_shorts/scenes/`
- 역할:
  - 스크립트를 쇼츠 장면 단위로 분해
  - 장면별 목적, 내레이션, 화면 강조 문구를 정의
- 목표:
  - 한 장면에 한 메시지
  - 하단 자막은 짧게
  - 상단 훅은 모바일에서 즉시 읽히게 구성

## 3. Visual Planning

- 위치: `media_agent/data_shorts/visuals/`
- 역할:
  - 장면별 이미지 생성 프롬프트 작성
  - 팬더 남자 해설자, 금융 차트, 뉴스룸, ETF 순위 보드 같은 시각적 톤 정의
- 한글 텍스트는 이미지 생성 모델에 직접 맡기지 않고, 후처리 합성을 우선한다.
- 고정 제작 규칙은 `docs/shorts-production-rules.md`를 우선한다. 특히 Taehyung 목소리와 채널 팬더 얼굴 일관성은 특별 지시가 없으면 바꾸지 않는다.

## 4. Rendering

### Remotion

- 위치: `media_agent/remotion/`
- 주요 파일:
  - `media_agent/remotion/src/ShortsVideo.tsx`
  - `media_agent/src/render/prepare_remotion_shorts.py`
- 장점:
  - React 기반 템플릿
  - 자막, 장면 전환, 오디오 싱크 관리가 체계적

### Pillow + FFmpeg

- 위치: `media_agent/src/render/render_reference_layout.py`
- 사용 이유:
  - Remotion 렌더가 특정 단계에서 멈췄을 때 빠르게 대체 가능
  - 참고 쇼츠형 고정 레이아웃을 직접 프레임으로 생성하기 좋음
- 역할:
  - 상단 큰 훅 문구
  - 중앙 이미지
  - 하단 흰색 자막 박스
  - FFmpeg 인코딩
- 정책:
  - 최종본에는 하단 프로그레스바를 넣지 않는다.
  - Remotion이 멈추면 reference layout 경로를 대체 렌더러로 사용한다.

## 5. Thumbnail

- 위치: `media_agent/data_shorts/thumbnails/`
- 현재 방식:
  - OpenAI 이미지 생성 API로 텍스트 없는 배경 생성
  - Pillow로 한글 텍스트 합성
  - 모바일 가독성 검수
- 이유:
  - 이미지 생성 모델은 한글 텍스트 정확도가 불안정함
  - 로컬 합성이 굵기, 위치, 문구 수정에 빠름
- OpenAI 이미지 생성이 가능하면 배경은 OpenAI로 만들고, 한글/숫자/티커는 로컬 합성으로 고정한다.

## 6. Upload Metadata

- 위치: `media_agent/data_shorts/metadata/`
- 포함:
  - 추천 타이틀
  - 대체 타이틀
  - 설명
  - 해시태그
  - 태그
  - 썸네일 카피
