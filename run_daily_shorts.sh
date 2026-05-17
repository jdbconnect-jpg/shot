#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
cd "${SCRIPT_DIR}"

VENV_DIR=".venv-shorts"
PYTHON_BIN="${VENV_DIR}/bin/python"
PIP_BIN="${VENV_DIR}/bin/pip"

if [ ! -d "${VENV_DIR}" ]; then
  python3 -m venv "${VENV_DIR}"
fi

"${PIP_BIN}" install --upgrade pip >/dev/null
"${PIP_BIN}" install -r requirements-shorts.txt

if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

"${PYTHON_BIN}" constant_factory.py

LATEST_META=$(ls -t final_shorts/*.json 2>/dev/null | grep -v '\.uploaded\.json$' | head -n 1 || true)
if [ -z "${LATEST_META}" ]; then
  echo "No metadata JSON found; skipping upload."
  exit 0
fi

echo "Generated metadata: ${LATEST_META}"

if [ -n "${YOUTUBE_CLIENT_SECRETS_FILE:-}" ] && [ -f "${YOUTUBE_CLIENT_SECRETS_FILE}" ]; then
  SHORTS_METADATA_FILE="${LATEST_META}" "${PYTHON_BIN}" upload_to_youtube.py
else
  echo "YOUTUBE_CLIENT_SECRETS_FILE not configured or file missing; skipping YouTube upload."
fi
