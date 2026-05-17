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
DATA_SUBDIR = os.getenv("MEDIA_AGENT_DATA_SUBDIR", "data")
SCENES_DIR = ROOT / DATA_SUBDIR / "scenes"
VISUALS_DIR = ROOT / DATA_SUBDIR / "visuals"


VISUAL_SYSTEM = """당신은 한국어 유튜브 쇼츠의 비주얼 디렉터다.
목표는 정보 신뢰감을 해치지 않으면서 시청자가 끝까지 보게 만드는 장면 설계다.
타 채널의 문장, 자막, 구체적 편집을 베끼지 말고 원칙만 참고한다.
ETF/투자 영상에서는 과장된 부자 이미지보다 데이터, 현금흐름, 시장 리스크를 시각적으로 명확히 보여준다.
채널 팬더 캐릭터는 얼굴만 고정한다. 젊은 남자 팬더 진행자이며 얼굴은 동그랗고 부드러운 흰 털, 큰 검은 귀, 선명한 검은 눈무늬, 둥근 검은 안경, 따뜻한 갈색 눈, 작은 미소를 유지한다. 얼굴 비율, 안경 모양, 눈무늬 배치, 나이대 인상은 장면마다 바꾸지 않는다. 의상, 자세, 소품, 제스처, 배경은 장면에 맞게 자유롭게 바꾼다.
레퍼런스 품질 기준:
- 화면은 프리미엄 북/다큐 쇼츠처럼 차분하고 밀도 있게 보이게 한다.
- 한 장면은 하나의 감정과 하나의 핵심 메시지만 가진다.
- B-roll은 손, 책상, 종이, 모바일 앱, 차트, 도시 야경, 노트, 계산기처럼 실제 촬영 가능한 소재를 우선한다.
- 자막과 배경이 경쟁하지 않게 어두운 여백, 명확한 피사체, 큰 대비를 확보한다.
- 금융 과장 이미지(슈퍼카, 돈다발, 호화 요트)는 쓰지 않는다.
출력은 JSON 객체 하나만 허용한다."""


VISUAL_USER_TEMPLATE = """아래 scenes JSON을 바탕으로 각 장면의 비주얼 프롬프트를 만들어라.

요구사항:
- scene_id별 항목을 만든다.
- stock_queries는 영어 검색어 3개. Pexels/Storyblocks/Artgrid에서 실제 B-roll을 찾기 좋은 표현으로 쓴다.
- stock_queries는 넓은 키워드보다 장면이 바로 떠오르는 검색어로 쓴다. 예: "close up hands checking investment app", "moody desk with notebook and calculator".
- ai_video_prompt는 Runway/Luma/Kling/Pika/Veo에 넣을 수 있는 영어 프롬프트로 쓴다.
- thumbnail_prompt는 OpenAI Image/Ideogram용 영어 프롬프트로 쓴다.
- motion_direction은 Remotion 템플릿에서 쓸 수 있게 한국어로 짧게 쓴다.
- on_screen_emphasis는 한국어 강조어 2~3개만 쓴다. 각 항목은 12자 이내로 짧게 쓴다.
- visual_style은 calm_finance, data_driven, caution, summary 중 하나.
- media_type은 video, image, infographic, chart 중 하나. 무조건 동영상을 고르지 말고, 대본 설명에 가장 적합한 매체를 고른다.
- realism_score는 0~1. 실제 stock이 더 적합하면 높게, AI 생성이 더 적합하면 낮게.
- search_intent는 stock, ai_video, graphic 중 하나.
- 숫자/ETF 정보는 scenes에 있는 말만 사용하고 새 사실을 만들지 않는다.
- hook 장면은 궁금증을 만들고, risk 장면은 긴장감을 주며, close 장면은 정리감이 강해야 한다.

scenes:
{{scenes_json}}"""


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


def _extract_json(text: str) -> dict[str, Any] | None:
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


def _gemini_visuals(scenes: list[dict]) -> dict[str, Any] | None:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or genai is None or types is None:
        return None
    client = genai.Client(api_key=api_key)
    prompt = f"SYSTEM\n{VISUAL_SYSTEM}\n\nUSER\n" + VISUAL_USER_TEMPLATE.replace(
        "{{scenes_json}}", json.dumps(scenes, ensure_ascii=False, indent=2)
    )
    config = types.GenerateContentConfig(response_mime_type="application/json")
    preferred = os.getenv("GEMINI_VISUAL_MODEL", "gemini-2.5-flash").strip()
    models = [preferred, "gemini-2.5-flash", "gemini-3.1-flash-lite-preview", "gemini-2.5-flash-lite"]
    for model in dict.fromkeys(models):
        try:
            response = client.models.generate_content(model=model, contents=prompt, config=config)
            parsed = _extract_json(response.text)
            if parsed:
                return parsed
        except Exception as e:
            print(f"warning=gemini_visual_failed model={model} reason={type(e).__name__}:{e}")
    return None


def _fallback_visual_for_scene(scene: dict) -> dict[str, Any]:
    objective = scene.get("objective", "background")
    title = scene.get("title_text") or scene.get("subtitle_text") or "finance explainer"
    narration = scene.get("narration", "")
    maps = {
        "hook": ["passive income investing", "monthly dividend income", "personal finance question"],
        "background": ["dividend income calculator", "financial planning spreadsheet", "investment portfolio review"],
        "evidence": ["investment analytics dashboard", "dividend chart analysis", "portfolio performance data"],
        "mechanism": ["covered call options strategy", "stock options trading screen", "financial derivatives explanation"],
        "etf_link": ["nasdaq technology stocks", "ETF portfolio trading screen", "stock market data monitor"],
        "risk": ["stock market volatility warning", "investment risk chart", "red market dashboard"],
        "close": ["financial independence summary", "portfolio checklist", "calm finance recap"],
    }
    queries = maps.get(objective, ["financial data dashboard", "investment planning", "stock market analysis"])
    return {
        "scene_id": scene["scene_id"],
        "stock_queries": queries,
        "ai_video_prompt": (
            "Vertical 9:16 realistic finance explainer shot, calm cinematic lighting, "
            f"visual metaphor for: {title}. No readable brand logos, no fake text."
        ),
        "thumbnail_prompt": (
            "Vertical YouTube Shorts thumbnail, premium Korean finance channel style, "
            "consistent young male panda presenter face matching the channel identity: round soft white fur, "
            "large black ears, clear black eye patches, round black glasses, warm brown eyes, small friendly smile, "
            "same face proportions and glasses shape in every scene. Wardrobe, pose, props, and gesture are flexible and should fit the scene. "
            f"clear focal point about {title}, bold readable Korean headline space, trustworthy tone."
        ),
        "motion_direction": "천천히 줌인, 핵심 숫자 등장 시 살짝 강조",
        "on_screen_emphasis": [title[:18], "숫자로 확인", "주의점"],
        "visual_style": "caution" if objective == "risk" else "summary" if objective == "close" else "data_driven",
        "realism_score": 0.85,
        "media_type": "chart" if objective in {"evidence", "risk", "close"} else "image" if objective in {"background", "etf_link"} else "video",
        "search_intent": "stock",
        "source_hint": narration[:120],
    }


def normalize_visuals(raw: dict[str, Any] | None, scenes: list[dict]) -> dict[str, Any]:
    raw_items = []
    if isinstance(raw, list):
        raw_items = raw
    elif isinstance(raw, dict):
        if isinstance(raw.get("scenes"), list):
            raw_items = raw["scenes"]
        elif isinstance(raw.get("visual_prompts"), list):
            raw_items = raw["visual_prompts"]
    by_scene = {item.get("scene_id"): item for item in raw_items if isinstance(item, dict)}
    items = []
    for scene in scenes:
        fallback = _fallback_visual_for_scene(scene)
        candidate = by_scene.get(scene["scene_id"], {})
        merged = {**fallback, **candidate}
        queries = merged.get("stock_queries") or fallback["stock_queries"]
        merged["stock_queries"] = [str(q).strip() for q in queries if str(q).strip()][:3] or fallback["stock_queries"]
        emphasis = merged.get("on_screen_emphasis") or fallback["on_screen_emphasis"]
        merged["on_screen_emphasis"] = [str(e).strip() for e in emphasis if str(e).strip()][:2]
        merged["realism_score"] = float(merged.get("realism_score", fallback["realism_score"]))
        merged["media_type"] = str(merged.get("media_type") or fallback["media_type"])
        items.append(merged)
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "script_id": scenes[0].get("script_id") if scenes else None,
        "engine": "gemini_or_fallback",
        "reference_style": "bookvore_visual_quality_only",
        "character_reference": "channel_panda_consistent_face",
        "scenes": items,
    }


def run() -> Path:
    scenes = json.loads(latest_scenes_path().read_text(encoding="utf-8"))
    raw = _gemini_visuals(scenes)
    visual_plan = normalize_visuals(raw, scenes)

    VISUALS_DIR.mkdir(parents=True, exist_ok=True)
    explicit_output = os.getenv("MEDIA_AGENT_VISUAL_PROMPTS_FILE", "").strip()
    output = Path(explicit_output) if explicit_output else VISUALS_DIR / "visual_prompt_latest.json"
    if explicit_output and not output.is_absolute():
        output = ROOT / explicit_output
    output.write_text(json.dumps(visual_plan, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved={output}")
    return output


if __name__ == "__main__":
    run()
