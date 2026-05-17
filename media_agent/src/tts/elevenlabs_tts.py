from __future__ import annotations

import os
from pathlib import Path

import requests
from dotenv import load_dotenv

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(WORKSPACE_ROOT / ".env")

API_KEY = os.getenv("ELEVENLABS_API_KEY", "").strip()
DEFAULT_VOICE_ID = "m3gJBS8OofDJfycyA2Ip"
DEFAULT_VOICE_NAME = "Taehyung - Natural, Friendly and Clear"
DEFAULT_MODEL_ID = "eleven_multilingual_v2"
ALLOW_CUSTOM_VOICE = os.getenv("MEDIA_AGENT_ALLOW_CUSTOM_ELEVENLABS_VOICE", "0").strip().lower() in {"1", "true", "yes"}
VOICE_ID = (
    os.getenv("ELEVENLABS_VOICE_ID", DEFAULT_VOICE_ID).strip() or DEFAULT_VOICE_ID
    if ALLOW_CUSTOM_VOICE
    else DEFAULT_VOICE_ID
)
MODEL_ID = os.getenv("ELEVENLABS_MODEL_ID", DEFAULT_MODEL_ID).strip() or DEFAULT_MODEL_ID


def synthesize(text: str, output_path: Path) -> Path:
    if not API_KEY:
        raise RuntimeError("ELEVENLABS_API_KEY missing")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
    payload = {
        "text": text,
        "model_id": MODEL_ID,
        "voice_settings": {
            "stability": 0.45,
            "similarity_boost": 0.7,
            "style": 0.15,
            "use_speaker_boost": True,
        },
    }
    response = requests.post(
        url,
        headers={
            "xi-api-key": API_KEY,
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=120,
    )
    if not response.ok:
        try:
            detail = response.json().get("detail", {})
            message = detail.get("message") or detail
        except Exception:
            message = response.text[:500]
        raise RuntimeError(f"ElevenLabs TTS failed: HTTP {response.status_code}: {message}")
    output_path.write_bytes(response.content)
    return output_path
