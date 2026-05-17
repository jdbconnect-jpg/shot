from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA_SUBDIR = "data_shorts"
DEFAULT_DOWNLOADS = Path.home() / "Downloads"
DEFAULT_MEDIA_DIR = ROOT / DATA_SUBDIR / "generated_media"
MEDIA_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".mp4", ".mov", ".webm", ".m4v"}


def _latest_scenes(script_id: str | None) -> list[str]:
    scenes_dir = ROOT / DATA_SUBDIR / "scenes"
    files = sorted(scenes_dir.glob("*_scenes.json"))
    if script_id:
        files = [p for p in files if p.name.startswith(script_id)]
    if not files:
        return [f"sc_{i:03d}" for i in range(1, 7)]
    scenes = json.loads(files[-1].read_text(encoding="utf-8"))
    return [scene["scene_id"] for scene in scenes]


def _script_id_from_scenes(script_id: str | None) -> str:
    if script_id:
        return script_id
    scenes_dir = ROOT / DATA_SUBDIR / "scenes"
    files = sorted(scenes_dir.glob("*_scenes.json"))
    if not files:
        raise FileNotFoundError("scenes file not found")
    scenes = json.loads(files[-1].read_text(encoding="utf-8"))
    return scenes[0].get("script_id") or files[-1].name.replace("_scenes.json", "")


def import_downloads(script_id: str | None, source_dir: Path, limit_minutes: int) -> list[Path]:
    script = _script_id_from_scenes(script_id)
    scene_ids = _latest_scenes(script)
    target_dir = DEFAULT_MEDIA_DIR / script
    target_dir.mkdir(parents=True, exist_ok=True)

    cutoff = None
    if limit_minutes > 0:
        import time

        cutoff = time.time() - (limit_minutes * 60)

    files = [
        p
        for p in source_dir.iterdir()
        if p.is_file()
        and p.suffix.lower() in MEDIA_EXTENSIONS
        and (cutoff is None or p.stat().st_mtime >= cutoff)
    ]
    files = sorted(files, key=lambda p: p.stat().st_mtime)

    copied: list[Path] = []
    used_sources: set[Path] = set()

    for scene_id in scene_ids:
        matches = [
            p
            for p in files
            if p not in used_sources
            and (
                scene_id.lower() in p.stem.lower()
                or scene_id.replace("_", "-").lower() in p.stem.lower()
            )
        ]
        if not matches:
            continue
        src = matches[-1]
        used_sources.add(src)
        dest = target_dir / f"{scene_id}{src.suffix.lower()}"
        shutil.copy2(src, dest)
        copied.append(dest)

    remaining_scene_ids = [sid for sid in scene_ids if not any(p.stem == sid for p in copied)]
    remaining_files = [p for p in files if p not in used_sources]
    for scene_id, src in zip(remaining_scene_ids, remaining_files):
        dest = target_dir / f"{scene_id}{src.suffix.lower()}"
        shutil.copy2(src, dest)
        copied.append(dest)

    return copied


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--script-id", default=None)
    parser.add_argument("--source-dir", default=str(DEFAULT_DOWNLOADS))
    parser.add_argument("--limit-minutes", type=int, default=180)
    args = parser.parse_args()

    copied = import_downloads(args.script_id, Path(args.source_dir).expanduser(), args.limit_minutes)
    for path in copied:
        print(f"copied={path}")
    print(f"count={len(copied)}")


if __name__ == "__main__":
    main()
