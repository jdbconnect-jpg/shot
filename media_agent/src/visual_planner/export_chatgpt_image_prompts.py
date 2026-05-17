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
GENERATED_DIR = ROOT / DATA_SUBDIR / "generated_images"


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


def _scene_prompt(scene: dict, visual: dict) -> dict:
    scene_id = scene["scene_id"]
    title = scene.get("title_text") or scene.get("subtitle_text") or "finance scene"
    narration = " ".join(str(scene.get("narration", "")).split())
    style = visual.get("visual_style", "calm_finance")
    media_type = visual.get("media_type", "image")
    emphasis = ", ".join(visual.get("on_screen_emphasis") or [])
    ai_prompt = visual.get("thumbnail_prompt") or visual.get("ai_video_prompt") or title
    prompt = (
        "Create one premium vertical 9:16 image for a Korean finance YouTube Shorts scene. "
        "Use a cinematic documentary/book-review channel look: calm, refined, realistic, high contrast, "
        "soft directional lighting, clear negative space for Korean subtitles in the lower third. "
        "Use the channel's consistent young male panda presenter face: round soft white fur, large black ears, "
        "clear black eye patches, round black glasses, warm brown eyes, and a small friendly smile. "
        "Keep the same face proportions, glasses shape, eye-patch layout, and age impression in every scene. "
        "Wardrobe and gestures may change naturally for the scene: smart-casual finance narrator, relaxed shoulders, subtle hand gesture, "
        "tablet, notes, or chart interaction when useful. Avoid a stiff teacher-at-a-chalkboard look. "
        "No readable text, no logos, no watermark, no UI brand names, no money piles, no luxury flex imagery. "
        "The image should support this scene, not explain it with text. "
        f"Scene id: {scene_id}. "
        f"Scene title: {title}. "
        f"Scene objective: {scene.get('objective', '')}. "
        f"Visual style: {style}. Preferred medium: {media_type}. "
        f"Key visual idea: {ai_prompt}. "
        f"Emotional emphasis: {emphasis}. "
        f"Narration context: {narration[:260]} "
        "Composition: one strong focal subject, uncluttered background, premium editorial lighting, "
        "vertical crop, safe dark area near the bottom for subtitles."
    )
    return {
        "scene_id": scene_id,
        "filename": f"{scene_id}.png",
        "title": title,
        "prompt": prompt,
    }


def _combined_prompt(script_id: str, out_dir: Path, prompts: list[dict]) -> str:
    lines = [
        "아래 요청대로 유튜브 쇼츠용 이미지를 생성해줘.",
        "",
        "공통 규칙:",
        "- 각 장면마다 세로 9:16 이미지 1장씩 생성",
        "- 프리미엄 다큐/북리뷰 쇼츠 느낌, 차분하고 고급스럽게",
        "- 이미지 안에 글자, 로고, 워터마크, 브랜드명 넣지 않기",
        "- 하단 25%는 한국어 자막이 올라갈 수 있게 비교적 어둡고 단순하게",
        "- 팬더 얼굴은 채널 헤더 기준으로 고정: 젊은 남자 팬더, 둥근 흰 얼굴, 큰 검은 귀/눈무늬, 둥근 검은 안경, 따뜻한 눈, 작은 미소",
        "- 얼굴 비율, 안경 모양, 눈무늬 배치, 나이대 인상은 장면마다 바꾸지 않기",
        "- 복장과 제스처는 남자 내레이션과 어울리게 자연스럽게: 스마트캐주얼, 태블릿/메모/차트 설명, 편안한 손짓",
        "- 칠판 앞 선생님처럼 딱딱한 구도는 피하기",
        "- 돈다발, 슈퍼카, 과장된 부자 이미지는 금지",
        "- 생성 후 파일명은 아래 filename 기준으로 저장할 수 있게 구분해줘",
        "",
        f"저장할 폴더: {out_dir}",
        f"script_id: {script_id}",
        "",
    ]
    for item in prompts:
        lines.extend(
            [
                f"## {item['scene_id']} / filename: {item['filename']}",
                item["prompt"],
                "",
            ]
        )
    return "\n".join(lines)


def _copy_to_clipboard(text: str) -> None:
    subprocess.run(["pbcopy"], input=text, text=True, check=True)


def _open_chatgpt() -> None:
    subprocess.run(["open", "-a", "ChatGPT"], check=False)


def run() -> Path:
    scenes = json.loads(latest_scenes_path().read_text(encoding="utf-8"))
    script_id = scenes[0].get("script_id") if scenes else datetime.now().strftime("%Y%m%d_%H%M%S")
    visual_prompts = load_visual_prompts()
    out_dir = GENERATED_DIR / str(script_id)
    out_dir.mkdir(parents=True, exist_ok=True)

    prompts = [_scene_prompt(scene, visual_prompts.get(scene["scene_id"], {})) for scene in scenes]
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "script_id": script_id,
        "image_dir": str(out_dir),
        "naming_rule": "Save each downloaded image as <scene_id>.png, for example sc_001.png.",
        "scenes": prompts,
    }
    json_path = out_dir / "chatgpt_image_prompts.json"
    txt_path = out_dir / "chatgpt_image_prompts.txt"
    combined = _combined_prompt(str(script_id), out_dir, prompts)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    txt_path.write_text(combined, encoding="utf-8")

    if os.getenv("MEDIA_AGENT_COPY_CHATGPT_PROMPT", "1") != "0":
        _copy_to_clipboard(combined)
        print(f"copied_to_clipboard={txt_path}")
    if os.getenv("MEDIA_AGENT_OPEN_CHATGPT", "0") == "1":
        _open_chatgpt()
        print("opened_chatgpt=true")
    print(f"saved={json_path}")
    print(f"prompt_text={txt_path}")
    print(f"image_dir={out_dir}")
    return json_path


if __name__ == "__main__":
    run()
