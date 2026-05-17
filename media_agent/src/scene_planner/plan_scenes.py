from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "data" / "scripts"
SCENES_DIR = ROOT / "data" / "scenes"


def latest_script_path() -> Path:
    files = sorted(SCRIPTS_DIR.glob("scr_*.json"))
    if not files:
        raise FileNotFoundError("script file not found")
    return files[-1]


def subtitle_for(text: str) -> str:
    compact = " ".join(text.strip().replace("\n", " ").split())
    return compact


def title_for(objective: str, narration: str) -> str:
    presets = {
        "hook": "SDIV로 월배당 100만원 받는 법",
        "today_core": "오늘 고른 ETF는 SDIV",
        "background": "먼저 계산 전제부터",
        "evidence": "숫자로 바로 계산해보자",
        "mechanism": "월 100만원 목표는 가능할까",
        "etf_link": "ETF로 보는 배당 구조",
        "implication": "이 숫자의 의미",
        "risk": "고배당 ETF의 리스크",
        "what_to_watch": "시간이 지나면 얼마나 늘까",
        "close": "오늘 핵심 정리",
    }
    return presets.get(objective, narration.split(".")[0][:18].strip() or "핵심 포인트")


def run() -> Path:
    script = json.loads(latest_script_path().read_text())
    sections = script.get("sections", [])
    duration = script.get("target_duration_sec", 240)
    per_scene = max(27, min(33, round(duration / max(1, len(sections)))))
    scenes = []
    start = 0
    for idx, section in enumerate(sections, start=1):
        end = start + per_scene
        scenes.append(
            {
                "scene_id": f"sc_{idx:03d}",
                "script_id": script["script_id"],
                "start_sec": start,
                "end_sec": end,
                "objective": section["objective"],
                "narration": section["narration"],
                "title_text": title_for(section["objective"], section["narration"]),
                "subtitle_text": subtitle_for(section["narration"]),
                "claim_ids": section.get("claim_ids", []),
                "visual_modes": ["stock_video", "headline_card" if section["objective"] in {"hook", "today_core", "close"} else "chart"],
                "asset_ids": [],
            }
        )
        start = end

    SCENES_DIR.mkdir(parents=True, exist_ok=True)
    output = SCENES_DIR / f"{script['script_id']}_scenes.json"
    output.write_text(json.dumps(scenes, ensure_ascii=False, indent=2))
    print(f"saved={output}")
    return output


if __name__ == "__main__":
    run()
