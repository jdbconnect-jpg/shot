#!/bin/zsh
set -euo pipefail

cd /Users/ahramlee/.openclaw/workspace

VENV_DIR=".venv-shorts"
PYTHON_BIN="${VENV_DIR}/bin/python"
PIP_BIN="${VENV_DIR}/bin/pip"

if [ ! -d "${VENV_DIR}" ]; then
  python3 -m venv "${VENV_DIR}"
fi

"${PIP_BIN}" install -q -r media_agent/requirements-longform.txt -r requirements-shorts.txt

if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

export MEDIA_AGENT_DATA_SUBDIR="data_shorts"
export MEDIA_AGENT_WIDTH="1080"
export MEDIA_AGENT_HEIGHT="1920"
export MEDIA_AGENT_FPS="30"
export MEDIA_AGENT_SUBTITLE_FONT_SCALE="1.3"
export MEDIA_AGENT_SUBTITLE_MAX_LINES="2"
export MEDIA_AGENT_TTS_RATE="+10%"
export MEDIA_AGENT_TITLE_Y_RATIO="0.16"
export MEDIA_AGENT_SUBTITLE_CENTER_RATIO="0.50"
export MEDIA_AGENT_SCRIPT_FILE="${MEDIA_AGENT_SCRIPT_FILE:-data_shorts/scripts/scr_20260505_183300.json}"
export MEDIA_AGENT_SCENES_FILE="${MEDIA_AGENT_SCENES_FILE:-data_shorts/scenes/scr_20260505_183300_scenes.json}"
export MEDIA_AGENT_ASSET_PLAN_FILE="${MEDIA_AGENT_ASSET_PLAN_FILE:-data_shorts/assets/asset_plan_latest.json}"
export MEDIA_AGENT_VISUAL_PROMPTS_FILE="${MEDIA_AGENT_VISUAL_PROMPTS_FILE:-data_shorts/visuals/visual_prompt_latest.json}"
export MEDIA_AGENT_PEXELS_ORIENTATION="${MEDIA_AGENT_PEXELS_ORIENTATION:-portrait}"
export GEMINI_SCRIPT_MODEL="${GEMINI_SCRIPT_MODEL:-gemini-2.5-flash}"
export GEMINI_VISUAL_MODEL="${GEMINI_VISUAL_MODEL:-gemini-2.5-flash}"

if [ "${MEDIA_AGENT_ENHANCE_SCRIPT:-0}" = "1" ]; then
  "${PYTHON_BIN}" media_agent/src/scripting/enhance_shorts_script.py
fi
"${PYTHON_BIN}" media_agent/src/visual_planner/generate_visual_prompts.py
"${PYTHON_BIN}" media_agent/src/asset_broker/select_assets.py
"${PYTHON_BIN}" media_agent/src/render/prepare_remotion_shorts.py

cd media_agent/remotion
if [ ! -d node_modules ]; then
  npm install
fi

npx remotion render src/index.ts ShortsVideo ../data_shorts/renders/scr_20260505_183300_remotion.mp4 \
  --props=public/shorts-job.json \
  --codec=h264 \
  --pixel-format=yuv420p \
  --audio-codec=aac \
  --overwrite

ffmpeg -hide_banner -y -i ../data_shorts/renders/scr_20260505_183300_remotion.mp4 \
  -map 0:v:0 -map 0:a:0 \
  -vf "scale=720:1280:flags=lanczos:in_range=pc:out_range=tv,format=yuv420p" \
  -c:v libx264 -profile:v baseline -level 3.1 -preset medium -crf 21 \
  -x264-params "bframes=0:keyint=60:min-keyint=30:scenecut=0" \
  -color_range tv -colorspace bt709 -color_primaries bt709 -color_trc bt709 \
  -r 30 -fps_mode cfr \
  -af "loudnorm=I=-16:TP=-1.5:LRA=11,volume=1.4" \
  -c:a aac -b:a 192k -ar 44100 -ac 2 \
  -movflags +faststart \
  ../data_shorts/renders/scr_20260505_183300_remotion_playable_720p.mp4
