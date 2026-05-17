from __future__ import annotations

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA_SUBDIR = os.getenv("MEDIA_AGENT_DATA_SUBDIR", "data")
DEFAULT_GENERATED_DIR = ROOT / DATA_SUBDIR / "generated_media"
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".m4v"}


def _base_dirs(script_id: str | None = None) -> list[Path]:
    explicit = os.getenv("MEDIA_AGENT_GENERATED_MEDIA_DIR", "").strip()
    if explicit:
        path = Path(explicit)
        return [path if path.is_absolute() else ROOT / explicit]
    dirs = [DEFAULT_GENERATED_DIR / script_id] if script_id else [DEFAULT_GENERATED_DIR]
    # Backward compatible path used by the earlier ChatGPT image flow.
    legacy = ROOT / DATA_SUBDIR / "generated_images"
    dirs.append(legacy / script_id if script_id else legacy)
    return dirs


def _find_scene_file(scene_id: str, extensions: set[str], script_id: str | None = None) -> Path | None:
    candidates: list[Path] = []
    for base in _base_dirs(script_id):
        if not base.exists():
            continue
        for path in base.iterdir():
            if not path.is_file() or path.suffix.lower() not in extensions:
                continue
            stem = path.stem.lower()
            scene = scene_id.lower()
            if stem == scene or stem.startswith(f"{scene}_") or stem.startswith(f"{scene}-"):
                candidates.append(path)
    if not candidates:
        return None
    return sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)[0]


def find_scene_image(scene_id: str, script_id: str | None = None) -> dict | None:
    selected = _find_scene_file(scene_id, IMAGE_EXTENSIONS, script_id=script_id)
    if not selected:
        return None
    uri = selected.resolve().as_uri()
    return {
        "provider_ref": selected.name,
        "url": uri,
        "image": uri,
        "width": None,
        "height": None,
        "duration": None,
    }


def find_scene_video(scene_id: str, script_id: str | None = None) -> dict | None:
    selected = _find_scene_file(scene_id, VIDEO_EXTENSIONS, script_id=script_id)
    if not selected:
        return None
    uri = selected.resolve().as_uri()
    return {
        "provider_ref": selected.name,
        "url": uri,
        "image": None,
        "width": None,
        "height": None,
        "duration": None,
    }
