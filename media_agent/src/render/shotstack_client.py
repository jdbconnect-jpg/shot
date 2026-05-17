from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

import requests
from dotenv import load_dotenv
from pathlib import Path


WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(WORKSPACE_ROOT / ".env")

SHOTSTACK_API_KEY = os.getenv("SHOTSTACK_API_KEY", "").strip()
SHOTSTACK_ENV = os.getenv("SHOTSTACK_ENV", "stage").strip().lower() or "stage"


@dataclass(frozen=True)
class ShotstackEndpoint:
    name: str
    render_url: str


def endpoint() -> ShotstackEndpoint:
    if SHOTSTACK_ENV in {"production", "prod"}:
        return ShotstackEndpoint("production", "https://api.shotstack.io/edit/v1/render")
    return ShotstackEndpoint("stage", "https://api.shotstack.io/edit/stage/render")


def _headers() -> dict[str, str]:
    if not SHOTSTACK_API_KEY:
        raise RuntimeError("SHOTSTACK_API_KEY missing")
    return {
        "x-api-key": SHOTSTACK_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def submit_render(edit: dict[str, Any]) -> dict[str, Any]:
    """Submit a Shotstack edit payload.

    This intentionally stays small: the existing pipeline uses Remotion for final
    local rendering, while Shotstack is available as a remote renderer once media
    assets are public URLs.
    """
    response = requests.post(endpoint().render_url, headers=_headers(), json=edit, timeout=60)
    response.raise_for_status()
    return response.json()


def validate_key() -> dict[str, Any]:
    """Validate key + endpoint without creating a render.

    Shotstack authenticates before validating the payload. A 400 validation error
    means the key reached the correct API environment; 401/403 means auth/env is
    wrong.
    """
    invalid_edit = {"timeline": {"tracks": []}, "output": {"format": "mp4", "resolution": "sd"}}
    ep = endpoint()
    response = requests.post(ep.render_url, headers=_headers(), json=invalid_edit, timeout=60)
    if response.status_code == 400:
        return {"ok": True, "environment": ep.name, "status": response.status_code, "mode": "validated_without_render"}
    return {
        "ok": response.ok,
        "environment": ep.name,
        "status": response.status_code,
        "response": response.text[:300],
    }


if __name__ == "__main__":
    print(json.dumps(validate_key(), ensure_ascii=False, indent=2))
