#!/bin/zsh
set -euo pipefail
cd /Users/ahramlee/.openclaw/workspace
VENV_DIR=".venv-shorts"
PYTHON_BIN="${VENV_DIR}/bin/python"
PIP_BIN="${VENV_DIR}/bin/pip"
if [ ! -d "${VENV_DIR}" ]; then
  python3 -m venv "${VENV_DIR}"
fi
"${PIP_BIN}" install -q -r media_agent/requirements-longform.txt
export MEDIA_AGENT_DATA_SUBDIR="data_shorts"
export MEDIA_AGENT_WIDTH="1080"
export MEDIA_AGENT_HEIGHT="1920"
export MEDIA_AGENT_FPS="30"
export MEDIA_AGENT_SUBTITLE_FONT_SCALE="1.3"
export MEDIA_AGENT_SUBTITLE_RAISE_RATIO="0.2"
export MEDIA_AGENT_SUBTITLE_MAX_LINES="2"
export MEDIA_AGENT_TTS_RATE="+10%"
export MEDIA_AGENT_TITLE_Y_RATIO="0.16"
export MEDIA_AGENT_SUBTITLE_CENTER_RATIO="0.50"
export MEDIA_AGENT_SCENES_FILE="data_shorts/scenes/scr_20260505_183300_scenes.json"
export MEDIA_AGENT_ASSET_PLAN_FILE="data_shorts/assets/asset_plan_latest.json"
"${PYTHON_BIN}" media_agent/src/render/render_longform.py
