# Current Shorts Screen Layout

Updated: 2026-05-19 KST

이 문서는 현재 ETF/경제 쇼츠의 기준 화면 비율, 타이틀, 영상 영역, 자막 포맷을 다른 세션에서도 그대로 재사용하기 위한 고정 레퍼런스다. 별도 지시가 없으면 새 쇼츠는 이 값을 기본값으로 둔다.

## Quick Use

```bash
MEDIA_AGENT_WIDTH=1080 \
MEDIA_AGENT_HEIGHT=1920 \
MEDIA_AGENT_FPS=30 \
MEDIA_AGENT_TITLE_FONT_SCALE=1.4 \
MEDIA_AGENT_TITLE_FONT_WEIGHT_SCALE=1.2 \
MEDIA_AGENT_SUBTITLE_THEME=black_band \
MEDIA_AGENT_SUBTITLE_CENTER_RATIO=0.75 \
MEDIA_AGENT_SUBTITLE_FONT_SCALE=1.43 \
MEDIA_AGENT_SUBTITLE_MAX_LINES=2 \
MEDIA_AGENT_TTS_RATE="+10%" \
bash media_agent/run_render_shorts_remotion.sh <script_id>
```

## Canvas

- Master canvas: `1080 x 1920`, vertical Shorts ratio `9:16`.
- Delivery render: `720 x 1280`.
- FPS: `30`.
- Base background: black.
- Final render must have no bottom progress bar.

## Top Title Band

- Position: top black title band.
- Coordinates on `1080 x 1920` canvas:
  - `top: 38px`
  - `left/right margin: 46px`
  - `height: 536px`
- Alignment: centered.
- Font family: `Apple SD Gothic Neo`, fallback `Noto Sans KR`, sans-serif.
- Base font size:
  - `82px` for short lines.
  - `70px` for longer lines.
- Current scale: `MEDIA_AGENT_TITLE_FONT_SCALE=1.4`.
- Weight scale: `MEDIA_AGENT_TITLE_FONT_WEIGHT_SCALE=1.2`.
- Effective weight: cap at `1000`.
- Color:
  - 기본: white.
  - 핵심 단어: yellow.
- Shadow: heavy black text shadow for phone readability.
- Hook rule:
  - First 3 seconds must use one strong question, contradiction, or warning.
  - Keep the top hook to 2 lines max when possible.
  - Target 9-12 Korean characters per line.
  - Highlight the strongest keyword in yellow: amount, ticker, risk word, or comparison word.
  - Avoid openings like `오늘은 ~ 알아볼게요`.

## Main Visual Band

- Position: middle image/video area.
- Coordinates on `1080 x 1920` canvas:
  - `top: 604px`
  - `height: 738px`
  - `width: 100%`
- Border: 6px dark divider on top and bottom.
- Image treatment:
  - Cover crop to fill the full band.
  - Slow zoom and slight upward slide.
  - Keep subject readable after crop on `720 x 1280`.
- Visual style:
  - Cute, high-quality animation.
  - Use the consistent young male Panda Teacher character when appropriate.
  - If Panda Teacher is not in the scene, use cute finance, ETF, semiconductor, chart, or market imagery.
  - Generated images must not include readable logos, trademarks, or fake text.
  - The visual must match the script beat, not act as generic decoration.

## Bottom Subtitle Band

- Theme: `black_band`.
- Position: below the main visual, not overlapping it.
- Current center ratio: `MEDIA_AGENT_SUBTITLE_CENTER_RATIO=0.75`.
- Approximate center Y on `1080 x 1920`: `1440px`.
- Box:
  - `left/right margin: 5.4%`
  - `min-height: 118px` before scaling
  - `padding: 20px 34px`
  - `background: #050505`
  - `border: none`
  - no white subtitle box for this style
- Text:
  - color: white
  - weight: `900`
  - base size: `45px`
  - scale: `MEDIA_AGENT_SUBTITLE_FONT_SCALE=1.43`
  - effective size: about `64px`
  - line height: `1.14`
  - max lines: `2`
- Caption copy rule:
  - Keep each subtitle short enough to scan in one glance.
  - Do not cover the character face, chart, ticker, or key visual clue.
  - If text wraps into more than 2 lines, shorten the narration segment instead of shrinking the whole UI.

## Current Reference Render

- Topic: `삼성전자 vs SK하이닉스, ETF로 사면 결과가 다른 이유`
- Reference file: `media_agent/data_shorts/renders/scr_20260518_semiconductor_etf_hqv2_sub143_720p.mp4`
- Treat this as the visual baseline for the current black-band subtitle style.
- Do not upload automatically unless explicitly requested.

## Production Checklist

- `ffprobe` confirms `720 x 1280`, `30fps`, audio present, and expected duration.
- First frame shows the title hook clearly.
- Top title is bigger and heavier than the subtitle.
- Subtitle sits below the visual band and remains readable on mobile.
- No bottom progress bar.
- Panda Teacher face identity stays consistent when used.
- Thumbnails and upload metadata can vary by topic, but the video layout should stay consistent unless testing a deliberate variant.

