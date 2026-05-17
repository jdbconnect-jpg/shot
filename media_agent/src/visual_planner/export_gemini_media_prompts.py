from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA_SUBDIR = os.getenv("MEDIA_AGENT_DATA_SUBDIR", "data")
SCENES_DIR = ROOT / DATA_SUBDIR / "scenes"
VISUALS_DIR = ROOT / DATA_SUBDIR / "visuals"
GENERATED_DIR = ROOT / DATA_SUBDIR / "generated_media"


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
    data = json.loads(path.read_text(encoding="utf-8"))
    return {item.get("scene_id"): item for item in data.get("scenes", []) if item.get("scene_id")}


def _media_request(scene: dict, visual: dict) -> str:
    media_type = str(visual.get("media_type") or "").lower()
    objective = scene.get("objective", "")
    if media_type == "video" or objective in {"hook", "background", "etf_link"}:
        return "If video generation is available, create an 8-second vertical 9:16 video. If not, create a single vertical 9:16 image."
    return "Create a single vertical 9:16 image."


def _scene_prompt(scene: dict, visual: dict) -> dict:
    scene_id = scene["scene_id"]
    title = scene.get("title_text") or scene.get("subtitle_text") or "finance scene"
    narration = " ".join(str(scene.get("narration", "")).split())
    emphasis = ", ".join(visual.get("on_screen_emphasis") or [])
    visual_idea = visual.get("ai_video_prompt") or visual.get("thumbnail_prompt") or title
    prompt = (
        f"{_media_request(scene, visual)} "
        "Premium Korean finance documentary shorts style. Calm, cinematic, refined, realistic, editorial lighting. "
        "No readable text inside the image/video, no Korean or English letters, no logos, no watermark, no brand UI. "
        "Avoid money piles, supercars, yachts, luxury flex visuals, cartoon characters, and exaggerated wealth symbols. "
        "Use one strong focal subject with uncluttered background and a dark, simple lower third for subtitles. "
        f"Scene id: {scene_id}. Scene title: {title}. Scene objective: {scene.get('objective', '')}. "
        f"Core idea: {visual_idea}. Emphasis: {emphasis}. Narration context: {narration[:260]} "
        "Make it feel like a premium book-review/documentary channel visual, but for ETF/investing education."
    )
    return {
        "scene_id": scene_id,
        "suggested_image_filename": f"{scene_id}.png",
        "suggested_video_filename": f"{scene_id}.mp4",
        "title": title,
        "prompt": prompt,
    }


def _combined_prompt(script_id: str, out_dir: Path, prompts: list[dict]) -> str:
    lines = [
        "아래 장면별로 유튜브 쇼츠용 이미지/영상을 만들어줘.",
        "",
        "공통 규칙:",
        "- 각 장면은 세로 9:16",
        "- Gemini에서 영상 생성이 가능하면 video 장면은 8초 영상, 아니면 이미지로 생성",
        "- 이미지/영상 안에는 글자, 로고, 워터마크, 브랜드 UI를 넣지 않기",
        "- 하단 25%는 자막이 올라갈 수 있게 어둡고 단순하게",
        "- 돈다발, 슈퍼카, 요트 같은 과장된 부자 이미지는 금지",
        "- 생성물을 다운로드한 뒤 파일명은 sc_001.png 또는 sc_001.mp4처럼 scene_id로 저장",
        "",
        f"저장할 폴더: {out_dir}",
        f"script_id: {script_id}",
        "",
    ]
    for item in prompts:
        lines.extend(
            [
                f"## {item['scene_id']}",
                f"download filename: {item['suggested_video_filename']} 또는 {item['suggested_image_filename']}",
                item["prompt"],
                "",
            ]
        )
    return "\n".join(lines)


def _copy_to_clipboard(text: str) -> None:
    subprocess.run(["pbcopy"], input=text, text=True, check=True)


def _open_gemini() -> None:
    subprocess.run(["open", "https://gemini.google.com/app"], check=False)


def run() -> Path:
    scenes = json.loads(latest_scenes_path().read_text(encoding="utf-8"))
    script_id = scenes[0].get("script_id") if scenes else datetime.now().strftime("%Y%m%d_%H%M%S")
    visual_prompts = load_visual_prompts()
    out_dir = GENERATED_DIR / str(script_id)
    out_dir.mkdir(parents=True, exist_ok=True)

    prompts = [_scene_prompt(scene, visual_prompts.get(scene["scene_id"], {})) for scene in scenes]
    combined = _combined_prompt(str(script_id), out_dir, prompts)
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "script_id": script_id,
        "media_dir": str(out_dir),
        "naming_rule": "Save each downloaded asset as <scene_id>.png or <scene_id>.mp4.",
        "scenes": prompts,
    }
    json_path = out_dir / "gemini_media_prompts.json"
    txt_path = out_dir / "gemini_media_prompts.txt"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    txt_path.write_text(combined, encoding="utf-8")

    if os.getenv("MEDIA_AGENT_COPY_GEMINI_PROMPT", "1") != "0":
        _copy_to_clipboard(combined)
        print(f"copied_to_clipboard={txt_path}")
    if os.getenv("MEDIA_AGENT_OPEN_GEMINI", "1") != "0":
        _open_gemini()
        print("opened_gemini=true")
    print(f"saved={json_path}")
    print(f"prompt_text={txt_path}")
    print(f"media_dir={out_dir}")
    return json_path


if __name__ == "__main__":
    run()
