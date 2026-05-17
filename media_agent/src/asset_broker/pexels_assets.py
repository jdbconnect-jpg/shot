from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(WORKSPACE_ROOT / ".env")

API_KEY = os.getenv("PEXELS_API_KEY", "").strip()


def search_videos(query: str, per_page: int = 3) -> list[dict[str, Any]]:
    if not API_KEY:
        return []
    orientation = os.getenv("MEDIA_AGENT_PEXELS_ORIENTATION", "landscape").strip() or "landscape"
    response = requests.get(
        "https://api.pexels.com/videos/search",
        headers={"Authorization": API_KEY},
        params={"query": query, "per_page": per_page, "orientation": orientation, "size": "medium"},
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    results = []
    for item in data.get("videos", []):
        files = item.get("video_files", [])
        if orientation == "portrait":
            best = next(
                (f for f in files if f.get("height", 0) >= 1280 and f.get("height", 0) > f.get("width", 0)),
                files[0] if files else None,
            )
        else:
            best = next((f for f in files if f.get("width", 0) >= 1280), files[0] if files else None)
        results.append(
            {
                "provider_ref": item.get("id"),
                "duration": item.get("duration"),
                "url": best.get("link") if best else None,
                "width": best.get("width") if best else None,
                "height": best.get("height") if best else None,
                "image": item.get("image"),
            }
        )
    return results
