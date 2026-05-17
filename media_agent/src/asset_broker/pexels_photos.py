from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(WORKSPACE_ROOT / ".env")

API_KEY = os.getenv("PEXELS_API_KEY", "").strip()


def search_photos(query: str, per_page: int = 3) -> list[dict[str, Any]]:
    if not API_KEY:
        return []
    orientation = os.getenv("MEDIA_AGENT_PEXELS_ORIENTATION", "portrait").strip() or "portrait"
    response = requests.get(
        "https://api.pexels.com/v1/search",
        headers={"Authorization": API_KEY},
        params={"query": query, "per_page": per_page, "orientation": orientation},
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    results: list[dict[str, Any]] = []
    for item in data.get("photos", []):
        src = item.get("src", {})
        url = src.get("large2x") or src.get("large") or src.get("portrait") or src.get("original")
        if not url:
            continue
        results.append(
            {
                "provider_ref": item.get("id"),
                "url": url,
                "width": item.get("width"),
                "height": item.get("height"),
                "image": src.get("medium") or url,
                "photographer": item.get("photographer"),
            }
        )
    return results
