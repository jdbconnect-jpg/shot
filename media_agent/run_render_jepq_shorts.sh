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
"${PYTHON_BIN}" media_agent/src/render/render_longform.py
