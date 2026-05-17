from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(WORKSPACE_ROOT / ".env")

API_KEY = os.getenv("COVERR_API_KEY", "").strip()
APP_ID = os.getenv("COVERR_APP_ID", "").strip()


def _headers() -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "x-api-key": API_KEY,
        "Accept": "application/json",
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 Chrome/126 Safari/537.36"
        ),
        "Referer": "https://coverr.co/",
    }
    if APP_ID:
        headers["x-app-id"] = APP_ID
    return headers


def _best_rendition(item: dict[str, Any]) -> dict[str, Any] | None:
    urls = item.get("urls") or {}
    default_variant = item.get("default_variant") or {}
    renditions = default_variant.get("renditions") or []
    if renditions:
        free_renditions = [r for r in renditions if not r.get("is_plus")]
        candidates = free_renditions or renditions
        preferred = sorted(
            candidates,
            key=lambda r: (
                0 if str(r.get("type")) == "hd" else 1 if str(r.get("type")) == "fhd" else 2,
                abs(int(r.get("height") or 0) - 1280),
            ),
        )
        best = preferred[0]
        if best.get("url"):
            return best
    if urls.get("mp4"):
        return {
            "url": urls.get("mp4"),
            "width": item.get("max_width"),
            "height": item.get("max_height"),
        }
    return None


def _video_detail(video_id: str) -> dict[str, Any] | None:
    try:
        response = requests.get(f"https://api.coverr.co/videos/{video_id}", headers=_headers(), timeout=60)
        response.raise_for_status()
        return response.json()
    except Exception:
        return None


def _normalize_item(item: dict[str, Any]) -> dict[str, Any] | None:
    detail = _video_detail(str(item.get("id") or item.get("objectID") or item.get("video_id") or "")) or item
    best = _best_rendition(detail)
    if not best:
        return None
    return {
        "provider_ref": detail.get("id") or detail.get("objectID") or detail.get("slug"),
        "duration": float(detail.get("duration") or 0) if detail.get("duration") is not None else None,
        "url": best.get("url"),
        "width": best.get("width") or detail.get("max_width"),
        "height": best.get("height") or detail.get("max_height"),
        "image": detail.get("thumbnail") or detail.get("poster") or detail.get("image"),
    }


def search_videos(query: str, per_page: int = 3) -> list[dict[str, Any]]:
    if not API_KEY:
        return []

    params = {"query": query, "page_size": per_page, "per_page": per_page}
    response = requests.get("https://api.coverr.co/videos", headers=_headers(), params=params, timeout=60)
    response.raise_for_status()
    data = response.json()
    items = data.get("hits") or data.get("videos") or data.get("results") or data.get("data") or []
    results: list[dict[str, Any]] = []
    for item in items:
        normalized = _normalize_item(item)
        if normalized and normalized.get("url"):
            results.append(normalized)
    return results
