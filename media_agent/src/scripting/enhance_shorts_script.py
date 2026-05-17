from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

try:
    from google import genai
    from google.genai import types
except Exception:  # pragma: no cover
    genai = None
    types = None


WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(WORKSPACE_ROOT / ".env")

ROOT = Path(__file__).resolve().parents[2]
DATA_SUBDIR = os.getenv("MEDIA_AGENT_DATA_SUBDIR", "data_shorts")
SCRIPTS_DIR = ROOT / DATA_SUBDIR / "scripts"
SCENES_DIR = ROOT / DATA_SUBDIR / "scenes"

VALID_OBJECTIVES = {"hook", "background", "evidence", "mechanism", "etf_link", "risk", "close"}


SYSTEM_PROMPT = """당신은 한국어 경제/ETF 유튜브 쇼츠의 헤드라이터이자 편집 디렉터다.
목표는 기존 사실과 claim_id를 유지하면서 시청 지속률이 높은 45~58초 쇼츠 대본으로 개선하는 것이다.

품질 기준:
- 책/다큐 쇼츠처럼 차분하지만 첫 2초에 궁금증이 생겨야 한다.
- 문장은 짧고, 말로 들었을 때 바로 이해되어야 한다.
- 각 장면은 한 메시지만 말한다.
- 장면마다 화면에 올릴 title_text와 subtitle_text는 1~2줄로 짧게 만든다.
- 숫자는 기존 입력에 있는 것만 사용한다. 새 수치, 새 종목, 새 사실을 만들지 않는다.
- 투자 권유처럼 단정하지 않는다. 정보 제공, 체크포인트, 리스크 균형을 지킨다.
- 레퍼런스 영상의 문장/전개를 베끼지 않고, 화면 밀도와 몰입감의 원칙만 참고한다.

출력은 JSON 객체 하나만 허용한다."""


USER_TEMPLATE = """아래 기존 쇼츠 script JSON과 scenes JSON을 개선하라.

반드시 지킬 출력 형식:
{
  "script": {
    기존 script의 주요 메타데이터,
    "title": string,
    "description": string,
    "target_duration_sec": number,
    "sections": [
      {"section_id": "sec_001", "objective": "hook", "narration": string, "claim_ids": [...]}
    ]
  },
  "scenes": [
    {
      "scene_id": "sc_001",
      "script_id": string,
      "start_sec": number,
      "end_sec": number,
      "objective": string,
      "narration": string,
      "title_text": string,
      "subtitle_text": string,
      "claim_ids": [...],
      "visual_modes": [...]
    }
  ]
}

작성 규칙:
- scene은 6개로 유지한다.
- 전체 길이는 45~58초.
- hook은 4~6초, risk와 close는 각각 7~10초.
- narration은 장면당 1~2문장.
- title_text는 16자 이내를 우선한다.
- subtitle_text는 24자 이내를 우선한다.
- objective 순서는 hook → background → evidence → etf_link/mechanism → risk → close.
- claim_ids는 입력에 있던 값만 사용한다.
- source_articles, ledger_id 등 근거 메타데이터는 유지한다.

script_json:
{{script_json}}

scenes_json:
{{scenes_json}}"""


def _json_from_text(text: str) -> dict[str, Any] | None:
    try:
        return json.loads(text)
    except Exception:
        pass
    match = re.search(r"\{.*\}", text, flags=re.S)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except Exception:
        return None


def _path_from_env(name: str, default_dir: Path, pattern: str) -> Path:
    explicit = os.getenv(name, "").strip()
    if explicit:
        path = Path(explicit)
        return path if path.is_absolute() else ROOT / path
    files = sorted(default_dir.glob(pattern))
    if not files:
        raise FileNotFoundError(f"no files for {name or pattern}")
    return files[-1]


def _load_inputs() -> tuple[Path, Path, dict[str, Any], list[dict[str, Any]]]:
    script_path = _path_from_env("MEDIA_AGENT_SCRIPT_FILE", SCRIPTS_DIR, "scr_*.json")
    scenes_path = _path_from_env("MEDIA_AGENT_SCENES_FILE", SCENES_DIR, "scr_*_scenes.json")
    return (
        script_path,
        scenes_path,
        json.loads(script_path.read_text(encoding="utf-8")),
        json.loads(scenes_path.read_text(encoding="utf-8")),
    )


def _gemini_enhance(script: dict[str, Any], scenes: list[dict[str, Any]]) -> dict[str, Any] | None:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or genai is None or types is None:
        return None
    prompt = "SYSTEM\n" + SYSTEM_PROMPT + "\n\nUSER\n" + USER_TEMPLATE.replace(
        "{{script_json}}", json.dumps(script, ensure_ascii=False, indent=2)
    ).replace("{{scenes_json}}", json.dumps(scenes, ensure_ascii=False, indent=2))
    config = types.GenerateContentConfig(response_mime_type="application/json")
    preferred = os.getenv("GEMINI_SCRIPT_MODEL", "gemini-2.5-flash").strip()
    models = [preferred, "gemini-2.5-flash", "gemini-3.1-flash-lite-preview", "gemini-2.5-flash-lite"]
    client = genai.Client(api_key=api_key)
    for model in dict.fromkeys(models):
        try:
            response = client.models.generate_content(model=model, contents=prompt, config=config)
            parsed = _json_from_text(response.text or "")
            if isinstance(parsed, dict) and isinstance(parsed.get("script"), dict) and isinstance(parsed.get("scenes"), list):
                return parsed
        except Exception as e:
            print(f"warning=gemini_script_enhance_failed model={model} reason={type(e).__name__}:{e}")
    return None


def _clean_text(value: Any, limit: int | None = None) -> str:
    text = " ".join(str(value or "").split())
    return text[:limit].rstrip() if limit else text


def _normalize(script: dict[str, Any], scenes: list[dict[str, Any]], enhanced: dict[str, Any] | None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if enhanced is None:
        return script, scenes

    allowed_claims = {claim for scene in scenes for claim in scene.get("claim_ids", [])}
    allowed_claims.update({claim for section in script.get("sections", []) for claim in section.get("claim_ids", [])})

    new_script = {**script, **enhanced.get("script", {})}
    new_script["script_id"] = script.get("script_id")
    new_script["cluster_id"] = script.get("cluster_id")
    new_script["source_article_ids"] = script.get("source_article_ids", [])
    new_script["source_articles"] = script.get("source_articles", [])
    new_script["ledger_id"] = script.get("ledger_id")
    new_script["tone"] = "premium_gemini_finance_shorts_ko"
    new_script["target_duration_sec"] = max(45, min(58, int(new_script.get("target_duration_sec", 52))))

    sections = []
    raw_sections = new_script.get("sections", [])
    for idx, item in enumerate(raw_sections[:6], start=1):
        objective = item.get("objective") if item.get("objective") in VALID_OBJECTIVES else (scenes[idx - 1].get("objective") if idx <= len(scenes) else "background")
        claim_ids = [c for c in item.get("claim_ids", []) if c in allowed_claims]
        if not claim_ids and idx <= len(scenes):
            claim_ids = [c for c in scenes[idx - 1].get("claim_ids", []) if c in allowed_claims]
        sections.append(
            {
                "section_id": f"sec_{idx:03d}",
                "objective": objective,
                "narration": _clean_text(item.get("narration") or (scenes[idx - 1].get("narration") if idx <= len(scenes) else "")),
                "claim_ids": claim_ids,
            }
        )
    if len(sections) < 6:
        for idx in range(len(sections) + 1, min(6, len(scenes)) + 1):
            scene = scenes[idx - 1]
            sections.append(
                {
                    "section_id": f"sec_{idx:03d}",
                    "objective": scene.get("objective", "background"),
                    "narration": _clean_text(scene.get("narration")),
                    "claim_ids": [c for c in scene.get("claim_ids", []) if c in allowed_claims],
                }
            )
    new_script["sections"] = sections

    raw_scenes = enhanced.get("scenes", [])
    durations = [5, 8, 8, 9, 8, max(7, new_script["target_duration_sec"] - 38)]
    cursor = 0
    new_scenes = []
    for idx, section in enumerate(sections, start=1):
        base = scenes[idx - 1] if idx <= len(scenes) else {}
        candidate = raw_scenes[idx - 1] if idx <= len(raw_scenes) else {}
        duration = durations[idx - 1] if idx <= len(durations) else 8
        start = cursor
        end = cursor + duration
        cursor = end
        objective = section["objective"]
        new_scenes.append(
            {
                "scene_id": f"sc_{idx:03d}",
                "script_id": script.get("script_id"),
                "start_sec": start,
                "end_sec": end,
                "objective": objective,
                "narration": section["narration"],
                "title_text": _clean_text(candidate.get("title_text") or base.get("title_text") or section["narration"], 24),
                "subtitle_text": _clean_text(candidate.get("subtitle_text") or base.get("subtitle_text") or section["narration"], 34),
                "claim_ids": section["claim_ids"],
                "visual_modes": candidate.get("visual_modes") or base.get("visual_modes") or ["stock_video", "headline_card"],
                "asset_ids": [],
            }
        )
    return new_script, new_scenes


def run() -> tuple[Path, Path]:
    script_path, scenes_path, script, scenes = _load_inputs()
    enhanced = _gemini_enhance(script, scenes)
    new_script, new_scenes = _normalize(script, scenes, enhanced)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    script_path.replace(script_path.with_suffix(f".pre_gemini_{stamp}.json"))
    scenes_path.replace(scenes_path.with_suffix(f".pre_gemini_{stamp}.json"))
    script_path.write_text(json.dumps(new_script, ensure_ascii=False, indent=2), encoding="utf-8")
    scenes_path.write_text(json.dumps(new_scenes, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved_script={script_path}")
    print(f"saved_scenes={scenes_path}")
    print(f"engine={'gemini' if enhanced else 'fallback_no_change'}")
    return script_path, scenes_path


if __name__ == "__main__":
    run()
