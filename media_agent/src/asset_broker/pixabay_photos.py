from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(WORKSPACE_ROOT / ".env")

API_KEY = os.getenv("PIXABAY_API_KEY", "").strip()


def search_photos(query: str, per_page: int = 3) -> list[dict[str, Any]]:
    if not API_KEY:
        return []
    orientation = os.getenv("MEDIA_AGENT_PIXABAY_ORIENTATION", "vertical").strip() or "vertical"
    response = requests.get(
        "https://pixabay.com/api/",
        params={
            "key": API_KEY,
            "q": query,
            "per_page": max(3, min(200, per_page)),
            "safesearch": "true",
            "orientation": orientation,
            "image_type": "photo",
        },
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    results: list[dict[str, Any]] = []
    for item in data.get("hits", []):
        url = item.get("largeImageURL") or item.get("webformatURL")
        if not url:
            continue
        results.append(
            {
                "provider_ref": item.get("id"),
                "url": url,
                "width": item.get("imageWidth") or item.get("webformatWidth"),
                "height": item.get("imageHeight") or item.get("webformatHeight"),
                "image": item.get("previewURL") or url,
                "tags": item.get("tags"),
            }
        )
    return results
