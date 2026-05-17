#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

SCRIPT_ID="${1:-scr_20260516_schd_dividend}"
SCENES_FILE="${MEDIA_AGENT_SCENES_FILE:-media_agent/data_shorts/scenes/${SCRIPT_ID}_scenes.json}"
VISUALS_FILE="${MEDIA_AGENT_VISUAL_PROMPTS_FILE:-media_agent/data_shorts/visuals/${SCRIPT_ID}_mixed_media_visual_prompts.json}"
ASSET_PLAN_FILE="${MEDIA_AGENT_ASSET_PLAN_FILE:-media_agent/data_shorts/assets/${SCRIPT_ID}_generated_media_asset_plan.json}"
OUT_FILE="media_agent/data_shorts/renders/${SCRIPT_ID}_generated_media_playable_720p.mp4"
RAW_FILE="media_agent/data_shorts/renders/${SCRIPT_ID}.mp4"

set -a
source .env
set +a

export MEDIA_AGENT_DATA_SUBDIR=data_shorts
export MEDIA_AGENT_SCENES_FILE="${SCENES_FILE#media_agent/}"
export MEDIA_AGENT_VISUAL_PROMPTS_FILE="${VISUALS_FILE#media_agent/}"
export MEDIA_AGENT_ASSET_PLAN_FILE="${ASSET_PLAN_FILE#media_agent/}"
export MEDIA_AGENT_WIDTH=720
export MEDIA_AGENT_HEIGHT=1280
export MEDIA_AGENT_FPS=30
export MEDIA_AGENT_SUBTITLE_CENTER_RATIO="${MEDIA_AGENT_SUBTITLE_CENTER_RATIO:-0.77}"
export MEDIA_AGENT_SUBTITLE_FONT_SCALE="${MEDIA_AGENT_SUBTITLE_FONT_SCALE:-0.96}"

.venv-shorts/bin/python media_agent/src/asset_broker/import_gemini_downloads.py --script-id "$SCRIPT_ID"
.venv-shorts/bin/python media_agent/src/asset_broker/select_assets.py
.venv-shorts/bin/python media_agent/src/render/render_longform.py

ffmpeg -y -i "$RAW_FILE" \
  -vf "scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2,format=yuv420p" \
  -af "loudnorm=I=-16:TP=-1.5:LRA=11" \
  -c:v libx264 -profile:v baseline -level 3.1 -preset veryfast -crf 18 \
  -c:a aac -b:a 160k -movflags +faststart "$OUT_FILE"

open "$OUT_FILE"
echo "video=$OUT_FILE"
