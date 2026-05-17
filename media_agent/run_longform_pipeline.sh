#!/bin/zsh
set -euo pipefail

cd /Users/ahramlee/.openclaw/workspace

VENV_DIR=".venv-shorts"
PYTHON_BIN="${VENV_DIR}/bin/python"
PIP_BIN="${VENV_DIR}/bin/pip"

if [ ! -d "${VENV_DIR}" ]; then
  python3 -m venv "${VENV_DIR}"
fi

"${PIP_BIN}" install --upgrade pip >/dev/null
"${PIP_BIN}" install -r media_agent/requirements-longform.txt >/dev/null

"${PYTHON_BIN}" media_agent/src/ingest/rss_ingest.py
"${PYTHON_BIN}" media_agent/src/dedupe/dedupe.py
"${PYTHON_BIN}" media_agent/src/relevance/filter.py
"${PYTHON_BIN}" media_agent/src/entities/extract_entities.py
"${PYTHON_BIN}" media_agent/src/clustering/cluster_events.py
"${PYTHON_BIN}" media_agent/src/evidence/build_ledger.py
"${PYTHON_BIN}" media_agent/src/scripting/generate_longform_script.py
"${PYTHON_BIN}" media_agent/src/scene_planner/plan_scenes.py
"${PYTHON_BIN}" media_agent/src/asset_broker/select_assets.py
"${PYTHON_BIN}" media_agent/src/render/render_longform.py
"${PYTHON_BIN}" media_agent/src/publish/publish_youtube.py
