# LONGFORM_AGENT_SPEC

## 목표
경제 뉴스 RSS와 공식 데이터 기반으로 3~5분 한국어 경제/ETF 유튜브 영상을 자동 생성한다.

## MVP 범위
- 입력: 경제 RSS, 공식 통계(추후 ECOS/KOSIS)
- 처리: 수집 → 정규화 → 중복 제거 → 관련도 판단 → 스크립트 → 장면 계획 → 렌더 → 게시 준비
- 출력: 16:9 1080p 영상, 설명란, 자막, 메타데이터
- 게시: 기본 private, 사람 승인 후 공개

## 핵심 원칙
1. 각 단계는 명시적 입력/출력을 가진다.
2. 뉴스 기사와 해석을 분리한다.
3. 근거 없는 주장보다 보수적 재서술을 우선한다.
4. 자산은 라이선스 fail-closed가 기본이다.
5. 투자 권유형 문구를 금지한다.

## 파이프라인
1. ingest
2. normalize
3. dedupe
4. relevance
5. entities
6. clustering
7. evidence
8. scripting
9. scene_planner
10. asset_broker
11. tts/captions
12. render
13. publish

## 산출물
- article.json
- dedupe_result.json
- cluster.json
- evidence_ledger.json
- script.json
- scenes.json
- render_job.json
- publish_payload.json

## 1차 구현 우선순위
- feeds.yaml 기반 RSS 수집
- article 스키마 저장
- exact dedupe
- 간단 relevance 규칙
- 스크립트/씬 JSON 생성기
- 렌더러 인터페이스 정의

## 채널 톤
- 차분한 경제 해설
- 초보자도 이해 가능
- 숫자는 쉽게 풀어 말함
- 과장 금지, 투자 권유 금지
