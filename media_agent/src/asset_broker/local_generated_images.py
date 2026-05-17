from __future__ import annotations

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA_SUBDIR = os.getenv("MEDIA_AGENT_DATA_SUBDIR", "data")
DEFAULT_GENERATED_DIR = ROOT / DATA_SUBDIR / "generated_images"
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def _base_dir(script_id: str | None = None) -> Path:
    explicit = os.getenv("MEDIA_AGENT_GENERATED_IMAGE_DIR", "").strip()
    if explicit:
        path = Path(explicit)
        return path if path.is_absolute() else ROOT / explicit
    if script_id:
        return DEFAULT_GENERATED_DIR / script_id
    return DEFAULT_GENERATED_DIR


def find_scene_image(scene_id: str, script_id: str | None = None) -> dict | None:
    base = _base_dir(script_id)
    if not base.exists():
        return None

    candidates = []
    for path in base.iterdir():
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        stem = path.stem.lower()
        if stem == scene_id.lower() or stem.startswith(f"{scene_id.lower()}_") or stem.startswith(f"{scene_id.lower()}-"):
            candidates.append(path)
    if not candidates:
        return None

    selected = sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)[0]
    return {
        "provider_ref": selected.name,
        "url": selected.resolve().as_uri(),
        "image": selected.resolve().as_uri(),
        "width": None,
        "height": None,
        "duration": None,
    }
