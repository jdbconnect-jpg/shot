# 롱폼 경제/ETF 유튜브 에이전트 재구축 계획

## 1) 현재 상태 진단
현재 워크스페이스의 자동화는 **쇼츠 전용 단일 스크립트 구조**에 가깝다.

### 확인된 현재 구조
- `constant_factory.py`
  - Google News RSS 1개 쿼리 기반 수집
  - Gemini로 30~45초 쇼츠 대본 생성
  - 5개 scene 중심의 세로형 영상 생성
- `run_daily_shorts.sh`
  - 쇼츠 생성 후 최신 결과를 바로 업로드
- `upload_to_youtube.py`
  - YouTube 업로드만 담당
- 산출물 디렉토리
  - `final_shorts/`, `temp_assets/`, `analytics/`

### 현재 구조의 한계
1. **롱폼 구조가 아님**
   - 3~5분 또는 10분 분량의 섹션형 해설 구조 부재
2. **사실 검증 계층 없음**
   - claim / evidence ledger / 공식 통계 교차검증 없음
3. **경제 도메인 모델링 부족**
   - 엔터티 추출, 영향도 점수, 이벤트 클러스터링 없음
4. **자산 선택 정책 부족**
   - 장면 목적별 B-roll / 차트 / 인포그래픽 분리 없음
5. **법무/라이선스 통제 약함**
   - 라이선스 hard filter, 출처 ledger, publish hold 부재
6. **업로드 메타데이터 부족**
   - 합성미디어 고지, 설명란 출처, 자막 업로드 자동화 미흡

---

## 2) 방향 전환 결론
이 프로젝트는 기존 쇼츠 공장을 조금 손보는 수준이 아니라,
**“경제 뉴스 기반 롱폼 해설 파이프라인”으로 재설계**하는 게 맞다.

즉, 현재 `constant_factory.py`를 계속 비대화시키는 대신 아래처럼 분리해야 한다.

- ingest
- dedupe
- relevance
- entities
- clustering
- evidence
- script
- scenes
- assets
- render
- publish

---

## 3) 권장 MVP 범위 (현실적인 1차 목표)
우선 10분 전체 스펙보다, **3~5분 롱폼 MVP**부터 만드는 게 좋다.

### MVP 목표
- 입력: 경제 뉴스 RSS + 공식 통계 일부
- 출력: 3~5분 한국어 롱폼 영상 1편
- 스타일: 차분한 경제 해설
- 주제: 경제 / 투자 / ETF
- 형식: 16:9 1080p
- 자산: Pexels + 자체 생성 차트 + 텍스트 카드
- 업로드: private 또는 unlisted
- 게시 전: 사람 승인 1회

### MVP에서 반드시 포함할 것
1. RSS 수집 레지스트리
2. URL/유사 중복 제거
3. 경제 관련도 필터
4. 핵심 엔터티 추출
5. 이벤트 클러스터링
6. claim/evidence ledger 최소 버전
7. 3~5분 스크립트 생성
8. 15~30초 장면 분할
9. Pexels + 차트 중심 자산 선택
10. TTS + 자막 + FFmpeg 렌더
11. YouTube 설명란 출처 자동 생성
12. publish 전 qa_hold

### MVP에서 제외해도 되는 것
- 음성 클로닝
- 사용자 제공 유튜브 채널 클립 자동 활용
- 고급 아바타
- 실시간 시장 데이터 초단위 반영
- 완전 무인 public 게시

---

## 4) 추천 기술 선택

### 데이터
- RSS: 매일경제, 한국경제, 필요 시 Google News는 보조
- 공식 데이터: ECOS, KOSIS
- 해외 비교: FRED (2단계)

### LLM / NLP
- 기사 요약 / 스크립트: 현재 사용 중인 LLM 유지 가능
- 임베딩: `bge-m3` 또는 다국어 계열
- 관련도 분류: 초기에는 규칙 + LLM fallback
- 엔터티 추출: 1차는 규칙 + 사전 기반으로 시작

### TTS
- 1순위: ElevenLabs 또는 Google Cloud TTS
- 단, **한국어 자연스러움 / 비용 / 자동화 적합성** 기준으로 벤치 필요
- 초기 MVP는 1개 엔진만 고정

### 자산
- 무료 B-roll: Pexels
- 차트: matplotlib / plotly + 이미지 렌더
- 텍스트 카드 / lower-third: Pillow 또는 ffmpeg drawtext

### 렌더
- FFmpeg 중심
- MoviePy는 유지 가능하지만 최종적으로는 FFmpeg 조합을 더 추천

---

## 5) 제안 디렉토리 구조
```text
media_agent/
  config/
    feeds.yaml
    providers.yaml
    policy.yaml
  data/
    raw/
    normalized/
    ledgers/
    scripts/
    scenes/
    assets/
    renders/
  src/
    ingest/
    normalize/
    dedupe/
    relevance/
    entities/
    clustering/
    evidence/
    scripting/
    scene_planner/
    asset_broker/
    tts/
    captions/
    render/
    publish/
  tests/
```

---

## 6) 현재 코드 기준 즉시 바꿔야 할 것

### A. `constant_factory.py` 역할 축소
지금 이 파일은 너무 많은 책임을 갖고 있다.

분리 대상:
- 뉴스 수집
- 대본 생성
- 장면 생성
- 그래픽 생성
- 음성 생성
- 영상 렌더
- 메타데이터 작성

### B. 세로형 고정 탈피
현재 쇼츠 중심이라 9:16 설계가 강하다.
롱폼은 기본을 **16:9 / 1920x1080**으로 바꿔야 한다.

### C. 업로드 메타데이터 강화
`upload_to_youtube.py`에 아래가 추가되어야 한다.
- 설명란 출처 블록
- 합성미디어 고지
- 자막 파일 연결
- privacy/schedule 분리
- 추후 `status.containsSyntheticMedia` 대응

### D. 단일 RSS 쿼리 의존 제거
Google News 검색 RSS 하나만 쓰면 품질이 흔들린다.
반드시 **복수 공식 경제 RSS 레지스트리**로 바꿔야 한다.

---

## 7) 4단계 실행 로드맵

### Phase 1. 기반 재설계 (1주)
- 피드 레지스트리 작성
- 기사 정규화 스키마 작성
- 기존 쇼츠 코드에서 ingest / generation 분리
- longform 전용 출력 디렉토리 추가

### Phase 2. 뉴스 이해 계층 (1~2주)
- exact dedupe
- near dedupe
- relevance filter
- entity extraction
- event clustering

### Phase 3. 해설 생성 계층 (1~2주)
- evidence ledger
- outline 생성
- 섹션별 본문 생성
- scene planner
- subtitle normalizer

### Phase 4. 미디어/게시 계층 (1~2주)
- Pexels 검색 연동
- 차트 생성기
- TTS 파이프라인
- ffmpeg 렌더
- YouTube publish + description/captions
- qa_hold 승인 흐름

---

## 8) 장면 설계 원칙 (3~5분 MVP)
3~5분이면 대략 **10~14개 장면**이 적당하다.

추천 구조:
1. hook
2. 오늘 핵심
3. 배경 설명
4. 데이터 1
5. 데이터 2
6. 시장 의미
7. ETF 연결
8. 생활/산업 영향
9. 리스크/반론
10. 체크포인트
11. 요약
12. 클로징

장면 길이 가이드:
- 평균 20~30초
- 숫자 많은 장면은 차트 우선
- 주장 1개당 장면 1개 원칙

---

## 9) 영상 스타일 제안
사용자가 준 레퍼런스 방향을 기준으로, 이 채널은 아래 포지션이 좋다.

### 채널 포지션
- “뉴스를 ETF 언어로 번역하는 차분한 경제 해설 채널”

### 톤
- 과장 금지
- 투자 권유 금지
- 근거 우선
- 숫자를 쉽게 풀어 설명
- 초보자도 이해 가능

### 시각 스타일
- 뉴스 클립 재사용보다 **자체 차트 + 깔끔한 B-roll + 카드형 요약** 중심
- 화면을 복잡하게 하지 말고,
  “핵심 문장 1개 + 보조 시각 1개” 원칙 유지

---

## 10) 보안 / 운영상 매우 중요한 점
이번 메시지에 **외부 서비스 API 키가 평문으로 들어왔다.**
이건 바로 처리하는 게 좋다.

권장 조치:
1. ElevenLabs 키 재발급
2. Pexels 키 재발급
3. Shotstack 키 재발급
4. 새 키는 `.env` 또는 secret manager에만 저장
5. 문서/채팅/코드에 다시 평문으로 남기지 않기

즉, **지금 공유된 키는 노출된 것으로 보고 교체하는 게 안전하다.**

---

## 11) 내가 추천하는 바로 다음 작업 순서
1. 롱폼 전용 파이프라인 디렉토리 생성
2. 피드 레지스트리와 기사 스키마 작성
3. 3~5분용 스크립트/씬 JSON 스키마 구현
4. Pexels + 차트 기반 asset broker 구현
5. ElevenLabs 또는 TTS 엔진 1개 고정 연결
6. 1편을 private로 end-to-end 생성
7. 결과 보고 나서 품질 튜닝

---

## 12) 첫 구현 스프린트의 구체적 산출물
- `LONGFORM_AGENT_SPEC.md`
- `feeds.yaml`
- `schemas/article.schema.json`
- `schemas/script.schema.json`
- `schemas/scene.schema.json`
- `src/ingest/rss_ingest.py`
- `src/dedupe/dedupe.py`
- `src/scripting/generate_longform_script.py`
- `src/scene_planner/plan_scenes.py`
- `src/render/render_longform.py`
- `src/publish/publish_youtube.py`

---

## 13) 성공 기준
MVP 성공 기준은 아래 정도가 현실적이다.
- 3~5분 영상 자동 생성 성공
- 16:9 1080p 렌더 성공
- 공식/허용 자산만 사용
- 설명란 출처 자동 포함
- 투자권유형 문구 없음
- 사람이 2~5분 안에 검수 가능
- 최소 1편을 private 업로드까지 완료

---

## 14) 한 줄 결론
이건 “쇼츠 개선”이 아니라 **롱폼 경제 해설 시스템으로의 재구축**이 맞고,
가장 좋은 전략은 **3~5분 MVP를 먼저 완성한 뒤 10분급으로 확장**하는 것이다.
