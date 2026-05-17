from __future__ import annotations

import os
from pathlib import Path

import requests
from dotenv import load_dotenv

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(WORKSPACE_ROOT / ".env")

API_KEY = os.getenv("ELEVENLABS_API_KEY", "").strip()
VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "").strip()
MODEL_ID = os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2").strip()


def synthesize(text: str, output_path: Path) -> Path:
    if not API_KEY or not VOICE_ID:
        raise RuntimeError("ELEVENLABS_API_KEY or ELEVENLABS_VOICE_ID missing")
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
