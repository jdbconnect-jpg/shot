# Shorts Video Playbook

이 문서는 ETF/금융 쇼츠를 반복 제작할 때 따라야 할 작업 패턴과, 이번 작업 중 반복적으로 어려웠던 지점을 정리한 운영 문서다.

## Default Pattern

1. 주제와 기준을 먼저 고정한다.
   - 예: `미장 ETF TOP3`, `국장 인기 TOP5`, `월분배 ETF 비교`
   - 순위형 콘텐츠는 기준을 반드시 적는다. AUM, 거래대금, 시가총액, 인기 검색 등 기준 없이 TOP 문구를 쓰지 않는다.
2. 스크립트는 40~55초 분량으로 만든다.
   - 첫 문장은 궁금증을 만든다.
   - 중간은 3~5개 장면으로 압축한다.
   - 마지막은 투자 권유가 아니라 선택 기준으로 닫는다.
3. 장면은 하나의 메시지만 가진다.
   - 한 장면에 ETF 하나, 리스크 하나, 선택 기준 하나처럼 분리한다.
   - 자막은 한 번에 1~2줄만 노출한다.
4. 이미지는 장면을 설명하는 역할이다.
   - 팬더 얼굴은 일관되게 유지하되, 복장/제스처/소품/자세는 장면에 맞게 자유롭게 바꾼다.
5. 최종 영상은 reference layout을 기본으로 렌더한다.
   - 검정 상단 타이틀
   - 노란 강조어
   - 중앙 이미지
   - 하단 자막 밴드
   - 하단 프로그레스바 없음

## Voice Policy

- 최종 쇼츠 TTS는 ElevenLabs `Taehyung - Natural, Friendly and Clear`를 기본으로 고정한다.
- voice id는 `m3gJBS8OofDJfycyA2Ip`다.
- `.env`의 범용 `ELEVENLABS_VOICE_ID`가 다른 값이어도, 쇼츠 기본 렌더에서는 Taehyung을 우선한다.
- ElevenLabs가 실패했는데 Edge TTS나 macOS `say`로 조용히 fallback된 파일을 최종본처럼 전달하지 않는다.

## Panda Visual Policy

- 팬더는 채널 캐릭터로 고정한다.
- 얼굴 고정 요소:
  - 젊은 남자 팬더 진행자
  - 둥근 흰 얼굴
  - 큰 검은 귀
  - 명확한 검은 눈무늬
  - 둥근 검은 안경
  - 따뜻한 눈과 작은 미소
- 복장과 제스처는 고정하지 않는다.
  - 장면의 감정, 정보 구조, 구도에 맞춰 자유롭게 선택한다.
  - 정장, 캐주얼, 책상, 스튜디오, 차트 앞, 거리, 태블릿, 손짓 등 모두 가능하다.
- 피해야 할 것:
  - 장면마다 얼굴 비율이나 안경 모양이 달라지는 것

## Thumbnail Policy

- OpenAI 이미지 생성은 썸네일 배경과 팬더 장면을 만드는 데 사용한다.
- 한글 문구와 숫자는 로컬 합성으로 넣는다.
- OpenAI 생성 프롬프트에는 `no readable text, no letters, no numbers, no logos`를 넣는다.
- 최종 썸네일은 JPG와 PNG를 함께 저장한다.
- 업로드 메타데이터는 최종 JPG를 가리키게 한다.

## Repeated Difficulties And Fixes

- 문제: `.env`의 `ELEVENLABS_VOICE_ID`가 Taehyung 대신 다른 목소리를 쓰게 만들었다.
  - 해결: `media_agent/src/tts/elevenlabs_tts.py`에서 기본 쇼츠 목소리는 Taehyung으로 강제하고, 명시적 예외는 `MEDIA_AGENT_ALLOW_CUSTOM_ELEVENLABS_VOICE=1`일 때만 허용한다.
- 문제: TTS fallback이 조용히 적용되면 사용자가 원하는 남자 목소리가 아닌 결과물이 나온다.
  - 해결: `MEDIA_AGENT_REQUIRE_ELEVENLABS=1`을 기본으로 두고 ElevenLabs 실패 시 최종 전달 전에 멈춘다.
- 문제: Remotion 렌더가 특정 상황에서 멈추거나 오래 걸렸다.
  - 해결: reference layout 영상은 `media_agent/src/render/render_reference_layout.py`의 Pillow + FFmpeg 경로로 안정적으로 렌더한다.
- 문제: 이미지 생성 모델이 한글 썸네일 텍스트를 깨뜨릴 수 있다.
  - 해결: OpenAI는 배경 이미지만 만들고, 제목/숫자/티커는 Pillow로 합성한다.
- 문제: 하단 프로그레스바가 참고 레이아웃과 맞지 않고 시선을 분산했다.
  - 해결: Remotion 템플릿과 reference layout 렌더러에서 프로그레스바를 제거했다.
- 문제: 팬더 얼굴이 장면마다 달라질 수 있다.
  - 해결: visual prompt 생성기와 ChatGPT/OpenAI 이미지 프롬프트 export에는 얼굴 고정 문구만 반복 주입하고, 복장/제스처는 자유롭게 둔다.

## Pre-Delivery Checklist

- 스크립트 JSON, scenes JSON, metadata JSON이 같은 `script_id`를 기준으로 연결되어 있는가?
- TTS 로그가 Taehyung 사용을 보여주는가?
- 최종 영상에 하단 프로그레스바가 없는가?
- 팬더 얼굴이 채널 캐릭터와 일관적인가?
- 자막이 720x1280 모바일 화면에서 겹치지 않고 읽히는가?
- 썸네일 한글 문구가 정확하고 큰가?
- metadata의 `video_path`, `thumbnail_path`가 최종 파일을 가리키는가?
