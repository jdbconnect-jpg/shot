from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(WORKSPACE_ROOT / ".env")

API_KEY = os.getenv("PIXABAY_API_KEY", "").strip()


def search_videos(query: str, per_page: int = 3) -> list[dict[str, Any]]:
    if not API_KEY:
        return []
    safe_per_page = max(3, min(200, per_page))
    response = requests.get(
        "https://pixabay.com/api/videos/",
        params={
            "key": API_KEY,
            "q": query,
            "per_page": safe_per_page,
            "safesearch": "true",
        },
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    results: list[dict[str, Any]] = []
    for item in data.get("hits", []):
        videos = item.get("videos", {})
        candidate_order = ["large", "medium", "small", "tiny"]
        best = next((videos.get(name) for name in candidate_order if videos.get(name)), None)
        if not best:
            continue
        results.append(
            {
                "provider_ref": item.get("id"),
                "duration": item.get("duration"),
                "url": best.get("url"),
                "width": best.get("width"),
                "height": best.get("height"),
                "image": best.get("thumbnail"),
            }
        )
    return results
