from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

from render_longform import (  # noqa: E402
    FPS,
    ROOT,
    TEMP_DIR,
    audio_duration,
    download_asset,
    latest_scenes_path,
    load_asset_plan,
    render_scene_card,
    subtitle_segments,
    synthesize_audio,
)


REMOTION_DIR = ROOT / "remotion"
PUBLIC_DIR = REMOTION_DIR / "public"
PUBLIC_MEDIA_DIR = PUBLIC_DIR / "media"


def _copy_to_public(src: Path, dest_name: str) -> str:
    PUBLIC_MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    dest = PUBLIC_MEDIA_DIR / dest_name
    shutil.copyfile(src, dest)
    return f"media/{dest.name}"


def _probe_duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return max(0.1, float(result.stdout.strip()))


def run() -> Path:
    scenes = json.loads(latest_scenes_path().read_text(encoding="utf-8"))
    asset_plan = load_asset_plan()
    script_id = scenes[0]["script_id"] if scenes else "shorts"

    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    PUBLIC_MEDIA_DIR.mkdir(parents=True, exist_ok=True)

    prepared_scenes = []
    cursor_frames = 0

    for idx, scene in enumerate(scenes, start=1):
        scene_id = scene["scene_id"]
        card_path = TEMP_DIR / f"{script_id}_remotion_scene_{idx:03d}.png"
        audio_path = TEMP_DIR / f"{script_id}_remotion_scene_{idx:03d}.aiff"

        render_scene_card(scene, card_path)
        effective_audio_path = synthesize_audio(scene.get("narration", ""), audio_path)
        duration = audio_duration(effective_audio_path) + 0.3
        duration_frames = max(1, round(duration * FPS))

        scene_assets = asset_plan.get(scene_id, {})
        selected_assets = scene_assets.get("selected_assets", [])
        visual_prompt = scene_assets.get("visual_prompt", {})
        stock_video = None
        stock_photo = None
        if os.getenv("MEDIA_AGENT_DISABLE_STOCK_VIDEO", "").strip() not in {"1", "true", "yes"}:
            stock_video = next((a for a in selected_assets if a.get("asset_type") == "stock_video" and a.get("url")), None)
        if os.getenv("MEDIA_AGENT_DISABLE_STOCK_PHOTO", "").strip() not in {"1", "true", "yes"}:
            stock_photo = next((a for a in selected_assets if a.get("asset_type") == "stock_photo" and a.get("url")), None)

        background = None
        background_image = None
        background_duration = duration
        if stock_video:
            bg_path = TEMP_DIR / f"{scene_id}_remotion_bg.mp4"
            if not bg_path.exists():
                download_asset(stock_video["url"], bg_path)
            background = _copy_to_public(bg_path, f"{script_id}_{scene_id}_bg.mp4")
            background_duration = _probe_duration(bg_path)
        elif stock_photo:
            suffix = Path(str(stock_photo["url"]).split("?", 1)[0]).suffix or ".jpg"
            bg_path = TEMP_DIR / f"{scene_id}_remotion_bg{suffix}"
            if not bg_path.exists():
                download_asset(stock_photo["url"], bg_path)
            background_image = _copy_to_public(bg_path, f"{script_id}_{scene_id}_bg{suffix}")

        card = _copy_to_public(card_path, f"{script_id}_{scene_id}_card.png")
        audio = _copy_to_public(effective_audio_path, f"{script_id}_{scene_id}_audio{effective_audio_path.suffix}")

        subtitles = [
            {
                "text": text,
                "startFrame": max(0, round(start * FPS)),
                "durationFrames": max(1, round((end - start) * FPS)),
            }
            for text, start, end in subtitle_segments(scene.get("narration", ""), duration)
        ]

        prepared_scenes.append(
            {
                "sceneId": scene_id,
                "objective": scene.get("objective", ""),
                "durationFrames": duration_frames,
                "startFrame": cursor_frames,
                "card": card,
                "audio": audio,
                "background": background,
                "backgroundImage": background_image,
                "backgroundLoopFrames": max(1, round(background_duration * FPS)),
                "visualPrompt": visual_prompt,
                "subtitles": subtitles,
            }
        )
        cursor_frames += duration_frames

    job = {
        "scriptId": script_id,
        "fps": FPS,
        "width": int(os.getenv("MEDIA_AGENT_WIDTH", "1080")),
        "height": int(os.getenv("MEDIA_AGENT_HEIGHT", "1920")),
        "subtitleCenterRatio": float(os.getenv("MEDIA_AGENT_SUBTITLE_CENTER_RATIO", "0.52")),
        "durationFrames": cursor_frames,
        "scenes": prepared_scenes,
    }

    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    output = PUBLIC_DIR / "shorts-job.json"
    output.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved={output}")
    print(f"duration_frames={cursor_frames}")
    return output


if __name__ == "__main__":
    run()
