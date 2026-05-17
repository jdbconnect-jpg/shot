from __future__ import annotations

import json
import os
from pathlib import Path

from coverr_assets import search_videos as search_coverr_videos
from local_generated_media import find_scene_image, find_scene_video
from pexels_assets import search_videos as search_pexels_videos
from pexels_photos import search_photos as search_pexels_photos
from pixabay_assets import search_videos as search_pixabay_videos
from pixabay_photos import search_photos as search_pixabay_photos

ROOT = Path(__file__).resolve().parents[2]
DATA_SUBDIR = os.getenv("MEDIA_AGENT_DATA_SUBDIR", "data")
SCENES_DIR = ROOT / DATA_SUBDIR / "scenes"
ASSETS_DIR = ROOT / DATA_SUBDIR / "assets"
VISUALS_DIR = ROOT / DATA_SUBDIR / "visuals"

QUERY_MAP = {
    "hook": "monthly income passive income investing",
    "today_core": "stock market office trading",
    "background": "dividend income financial planning calculator",
    "evidence": "investment portfolio analytics dividend chart",
    "mechanism": "covered call options stock market strategy",
    "etf_link": "nasdaq technology stocks trading screen",
    "implication": "investment portfolio planning",
    "risk": "stock market volatility risk warning chart",
    "what_to_watch": "calendar dashboard planning",
    "close": "financial independence portfolio summary",
}

PROVIDER_ORDER = ["pexels", "coverr", "pixabay"]


def _provider_cycle(scene_id: str) -> list[str]:
    return PROVIDER_ORDER


def _normalize_asset(provider: str, scene_id: str, rank: int, payload: dict, score: float, asset_type: str) -> dict:
    return {
        "asset_id": f"{scene_id}_{provider}_{rank}",
        "asset_type": asset_type,
        "provider": provider,
        "provider_ref": payload.get("provider_ref"),
        "url": payload.get("url"),
        "preview_image": payload.get("image"),
        "license_class": "stock-free",
        "usage_rights_ok": True,
        "score": score,
        "width": payload.get("width"),
        "height": payload.get("height"),
        "duration": payload.get("duration"),
    }


def _media_type_for(objective: str, visual_prompt: dict) -> str:
    explicit = str(visual_prompt.get("media_type") or visual_prompt.get("search_intent") or "").strip().lower()
    if explicit in {"video", "stock_video"}:
        return "video"
    if explicit in {"image", "photo", "stock_photo"}:
        return "image"
    if explicit in {"infographic", "chart", "graphic", "ai_video"}:
        return explicit
    if objective in {"evidence", "risk", "close"}:
        return "chart"
    if objective in {"background", "etf_link", "mechanism"}:
        return "image"
    return "video"


def latest_scenes_path() -> Path:
    explicit = os.getenv("MEDIA_AGENT_SCENES_FILE", "").strip()
    if explicit:
        path = Path(explicit)
        if not path.is_absolute():
            path = ROOT / explicit
        if not path.exists():
            raise FileNotFoundError(f"scenes file not found: {path}")
        return path
    files = sorted(SCENES_DIR.glob("*_scenes.json"))
    if not files:
        raise FileNotFoundError("scenes file not found")
    return files[-1]


def load_visual_prompts() -> dict:
    explicit = os.getenv("MEDIA_AGENT_VISUAL_PROMPTS_FILE", "").strip()
    path = Path(explicit) if explicit else VISUALS_DIR / "visual_prompt_latest.json"
    if explicit and not path.is_absolute():
        path = ROOT / explicit
    if not path.exists():
        return {}
    data = json.loads(path.read_text())
    return {item.get("scene_id"): item for item in data.get("scenes", []) if item.get("scene_id")}


def run() -> Path:
    scenes = json.loads(latest_scenes_path().read_text())
    script_id = scenes[0].get("script_id") if scenes else None
    visual_prompts = load_visual_prompts()
    plan = []
    for scene in scenes:
        objective = scene.get("objective", "hook")
        visual_prompt = visual_prompts.get(scene.get("scene_id"), {})
        media_type = _media_type_for(objective, visual_prompt)
        prompt_queries = visual_prompt.get("stock_queries") or []
        query = prompt_queries[0] if prompt_queries else QUERY_MAP.get(objective, "business economy office")
        def safe_search(label: str, fn, search_query: str):
            try:
                return fn(search_query, per_page=2)
            except Exception as e:
                print(f"warning=asset_search_failed provider={label} reason={type(e).__name__}:{e}")
                return []

        provider_hits = {"pexels": [], "pixabay": [], "coverr": [], "pexels_photo": [], "pixabay_photo": []}
        local_generated_image = find_scene_image(scene["scene_id"], script_id=script_id)
        local_generated_video = find_scene_video(scene["scene_id"], script_id=script_id)
        queries_to_try = [q for q in prompt_queries[:3] if q] or [query]
        for search_query in queries_to_try:
            if media_type in {"video"}:
                provider_hits["pexels"] = provider_hits["pexels"] or safe_search("pexels", search_pexels_videos, search_query)
                provider_hits["coverr"] = provider_hits["coverr"] or safe_search("coverr", search_coverr_videos, search_query)
                provider_hits["pixabay"] = provider_hits["pixabay"] or safe_search("pixabay", search_pixabay_videos, search_query)
            elif media_type in {"image", "photo"}:
                provider_hits["pexels_photo"] = provider_hits["pexels_photo"] or safe_search("pexels_photo", search_pexels_photos, search_query)
                provider_hits["pixabay_photo"] = provider_hits["pixabay_photo"] or safe_search("pixabay_photo", search_pixabay_photos, search_query)
            elif media_type in {"infographic", "chart", "graphic"}:
                # Prefer deterministic local graphics, but keep one photo fallback for texture.
                provider_hits["pexels_photo"] = provider_hits["pexels_photo"] or safe_search("pexels_photo", search_pexels_photos, search_query)
            if any(provider_hits.values()) or media_type in {"infographic", "chart", "graphic"}:
                query = search_query
                break
        selected_assets = []
        rank = 1
        if local_generated_video:
            selected_assets.append(
                _normalize_asset("gemini_local", scene["scene_id"], rank, local_generated_video, 0.98, "stock_video")
            )
            rank += 1
        if local_generated_image:
            selected_assets.append(
                _normalize_asset("gemini_local", scene["scene_id"], rank, local_generated_image, 0.96, "stock_photo")
            )
            rank += 1
        if media_type in {"image", "photo"}:
            provider_order = ["pexels_photo", "pixabay_photo"]
        elif media_type in {"infographic", "chart", "graphic"}:
            provider_order = ["pexels_photo"]
        else:
            provider_order = _provider_cycle(scene.get("scene_id", "sc_001"))
        for provider in provider_order:
            hits = provider_hits.get(provider) or []
            if not hits:
                continue
            asset_type = "stock_photo" if provider.endswith("_photo") else "stock_video"
            selected_assets.append(_normalize_asset(provider, scene["scene_id"], rank, hits[0], 0.8 - (rank * 0.02), asset_type))
            rank += 1
        selected_assets.append(
            {
                "asset_id": f"{scene['scene_id']}_card_1",
                "asset_type": "title_card",
                "provider": "local",
                "license_class": "owned",
                "usage_rights_ok": True,
                "score": 0.65,
            }
        )
        plan.append(
            {
                "scene_id": scene["scene_id"],
                "query": query,
                "media_type": media_type,
                "visual_prompt": visual_prompt,
                "selected_assets": selected_assets,
                "provider_hits": {k: len(v) for k, v in provider_hits.items()},
            }
        )
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    explicit_output = os.getenv("MEDIA_AGENT_ASSET_PLAN_FILE", "").strip()
    output = Path(explicit_output) if explicit_output else ASSETS_DIR / "asset_plan_latest.json"
    if explicit_output and not output.is_absolute():
        output = ROOT / explicit_output
    output.write_text(json.dumps(plan, ensure_ascii=False, indent=2))
    print(f"saved={output}")
    return output


if __name__ == "__main__":
    run()
