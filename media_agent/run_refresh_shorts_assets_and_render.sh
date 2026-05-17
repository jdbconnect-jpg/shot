#!/bin/zsh
set -euo pipefail
cd /Users/ahramlee/.openclaw/workspace/media_agent
VENV_DIR=".venv-shorts"
PYTHON_BIN="${VENV_DIR}/bin/python"
PIP_BIN="${VENV_DIR}/bin/pip"
if [ ! -d "${VENV_DIR}" ]; then
  python3 -m venv "${VENV_DIR}"
fi
"${PIP_BIN}" install -q -r requirements-longform.txt ../requirements-shorts.txt python-dotenv
export MEDIA_AGENT_DATA_SUBDIR="data_shorts"
export MEDIA_AGENT_SCENES_FILE="data_shorts/scenes/scr_20260505_183300_scenes.json"
export MEDIA_AGENT_ASSET_PLAN_FILE="data_shorts/assets/asset_plan_latest.json"
export MEDIA_AGENT_VISUAL_PROMPTS_FILE="data_shorts/visuals/visual_prompt_latest.json"
export MEDIA_AGENT_PEXELS_ORIENTATION="portrait"
"${PYTHON_BIN}" src/visual_planner/generate_visual_prompts.py
"${PYTHON_BIN}" src/asset_broker/select_assets.py
./run_render_shorts.sh
