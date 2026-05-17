# 2026-05-17 US ETF TOP3 Upload Session

## Goal

- 현재 쇼츠 영상에 맞는 썸네일을 개선하고, 최종 영상과 썸네일을 YouTube에 업로드한다.
- 이전에 정한 쇼츠 제작 규칙을 유지한다.
  - Taehyung 목소리
  - 팬더 얼굴 일관성
  - 복장/제스처는 장면별 자유
  - 하단 프로그레스바 없음
  - 한글 텍스트는 깨지지 않도록 로컬 고해상도 합성

## Final Video

- File: `media_agent/data_shorts/renders/scr_20260517_us_etf_top3_panda_taehyung_no_progress_720p.mp4`
- Topic: 미장 ETF TOP3, SPY/IVV/VOO
- Final metadata: `media_agent/data_shorts/metadata/scr_20260517_us_etf_top3_panda_youtube_upload.json`

## Thumbnail Iterations

- OpenAI dark fintech style thumbnail was generated first.
- User requested a less 1980s/retro look, so a 2026 modern fintech version was generated.
- User then requested a style similar to `scr_20260517_kr_etf_top3_api_generated_thumbnail.png`.
- Final direction:
  - bright white finance explainer style
  - large Korean headline at top
  - left ranking/role card
  - panda presenter on right
  - dark navy conclusion box at bottom
- Text rendering issue:
  - Generated-image text can look broken or inaccurate.
  - Final Korean text was rendered locally on a 4x high-resolution canvas and downsampled for smoother edges.
- Final selected thumbnail:
  - PNG: `media_agent/data_shorts/thumbnails/scr_20260517_us_etf_top3_integrated_clean_thumbnail_centered_bottom.png`
  - JPG: `media_agent/data_shorts/thumbnails/scr_20260517_us_etf_top3_integrated_clean_thumbnail_centered_bottom.jpg`

## Upload

- YouTube upload initially failed because the Google Cloud project used by the old OAuth client did not have YouTube Data API v3 enabled.
- User provided a new OAuth client.
- Local setup was updated:
  - Previous `client_secret.json` was backed up under `.secrets/`.
  - Previous YouTube token was backed up under `.secrets/`.
  - A new token was generated through browser OAuth.
- Sensitive OAuth secret values are intentionally not recorded here and must not be committed.

## Published Result

- Video ID: `AHNgbpKsw1M`
- URL: https://www.youtube.com/watch?v=AHNgbpKsw1M
- Uploaded result file: `media_agent/data_shorts/metadata/scr_20260517_us_etf_top3_panda_youtube_upload.uploaded.json`

## Lessons To Keep

- Do not commit `client_secret.json`, `.secrets/`, tokens, or raw secrets.
- Keep upload metadata and uploaded result JSON in git because they are useful project artifacts.
- For Korean thumbnail text, prefer local high-resolution text composition over direct model-generated text.
- When a thumbnail text box looks off-center, calculate the full text block height and center it within the box, rather than placing each line by fixed visual guesses.
