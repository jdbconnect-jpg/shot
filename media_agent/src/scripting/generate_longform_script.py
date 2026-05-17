from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

sys.path.append(str(Path(__file__).resolve().parents[1]))
from prompts import SCRIPT_SYSTEM, SCRIPT_USER_TEMPLATE

try:
    from google import genai
    from google.genai import types
except Exception:  # pragma: no cover
    genai = None
    types = None

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(WORKSPACE_ROOT / ".env")

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "data" / "scripts"
NORMALIZED_DIR = ROOT / "data" / "normalized"
LEDGERS_DIR = ROOT / "data" / "ledgers"
SCHEMAS_DIR = ROOT / "schemas"

NUMERIC_RE = re.compile(r"\d")
VALID_OBJECTIVES = {
    "hook", "today_core", "background", "evidence", "mechanism", "etf_link", "implication", "risk", "what_to_watch", "close"
}


def load_articles() -> list[dict]:
    path = NORMALIZED_DIR / "relevance_latest.json"
    if not path.exists():
        raise FileNotFoundError("relevance_latest.json not found")
    return json.loads(path.read_text())


def load_schema() -> dict[str, Any]:
    path = SCHEMAS_DIR / "script.schema.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def pick_top_cluster() -> tuple[dict, list[dict], dict | None]:
    clusters_path = NORMALIZED_DIR / "clusters_latest.json"
    ledgers_path = LEDGERS_DIR / "evidence_ledgers_latest.json"
    articles = {a["article_id"]: a for a in load_articles()}

    if not clusters_path.exists():
        relevant = [a for a in articles.values() if a.get("relevance_label") == "relevant"]
        relevant.sort(key=lambda a: (a.get("relevance_score", 0), a.get("published_at", "")), reverse=True)
        return {"cluster_id": "evt_stub", "title": "오늘 경제 뉴스 묶음"}, relevant[:5], None

    clusters = json.loads(clusters_path.read_text())
    clusters.sort(key=lambda c: (c.get("impact_score", 0), c.get("coherence", 0)), reverse=True)
    cluster = clusters[0] if clusters else {"cluster_id": "evt_stub", "title": "오늘 경제 뉴스 묶음"}
    picked_articles = [articles[article_id] for article_id in cluster.get("article_ids", []) if article_id in articles][:5]

    ledger = None
    if ledgers_path.exists():
        ledgers = json.loads(ledgers_path.read_text())
        ledger = next((item for item in ledgers if item.get("cluster_id") == cluster.get("cluster_id")), None)

    return cluster, picked_articles, ledger


def clean_title(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = text.replace('"', "").replace("'", "")
    return text[:48].rstrip(" ,.-…") or "오늘 경제 뉴스 핵심 정리"


def article_briefs_for_prompt(articles: list[dict]) -> list[dict]:
    return [
        {
            "article_id": a.get("article_id"),
            "title": a.get("title"),
            "summary": a.get("summary", "")[:280],
            "published_at": a.get("published_at"),
            "entities": a.get("entities", []),
            "relevance_score": a.get("relevance_score"),
            "canonical_url": a.get("canonical_url"),
            "source_name": a.get("source_name"),
        }
        for a in articles[:5]
    ]


def claim_map_for_ledger(ledger: dict | None) -> dict[str, dict]:
    claims = (ledger or {}).get("claims", [])
    return {claim.get("claim_id"): claim for claim in claims if claim.get("claim_id")}


def source_article_ids(articles: list[dict], ledger: dict | None) -> list[str]:
    ids = [a.get("article_id") for a in articles if a.get("article_id")]
    for article_id in (ledger or {}).get("source_article_ids", []):
        if article_id and article_id not in ids:
            ids.append(article_id)
    return ids


def infer_claim_ids(narration: str, all_claim_ids: list[str], fallback_count: int = 2) -> list[str]:
    if not all_claim_ids:
        return []
    if NUMERIC_RE.search(narration):
        return all_claim_ids[: min(len(all_claim_ids), max(1, fallback_count))]
    return all_claim_ids[:1]


def llm_script(cluster: dict, articles: list[dict], ledger: dict | None) -> dict | None:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or genai is None or types is None:
        return None

    client = genai.Client(api_key=api_key)
    article_briefs = article_briefs_for_prompt(articles)
    ledger_claims = (ledger or {}).get("claims", [])[:8]

    prompt = (
        f"SYSTEM\n{SCRIPT_SYSTEM}\n\n"
        + "출력은 JSON 객체 하나만 허용한다.\n"
        + "반드시 아래 키를 포함한다:\n- title\n- description\n- target_duration_sec\n- sections\n\n"
        + "sections 규칙:\n"
        + "- 10~12개 section\n"
        + "- 각 section은 section_id, objective, narration, claim_ids 포함\n"
        + "- narration은 2~4문장\n"
        + "- objective는 hook, today_core, background, evidence, mechanism, etf_link, implication, risk, what_to_watch, close 중에서 고를 것\n"
        + "- claim_ids는 evidence_ledger에 있는 claim_id만 써야 한다\n"
        + "- evidence_ledger에 없는 숫자는 새로 만들지 말 것\n"
        + "- 숫자나 비율을 쓰는 section은 claim_ids를 최소 1개 이상 반드시 연결할 것\n"
        + "- ETF 연결은 정보 제공 관점으로만 서술할 것\n\n"
        + "USER\n"
        + SCRIPT_USER_TEMPLATE
            .replace("{{cluster_summary}}", json.dumps({"cluster": cluster, "articles": article_briefs}, ensure_ascii=False))
            .replace("{{evidence_ledger}}", json.dumps({"claims": ledger_claims}, ensure_ascii=False))
    )

    config = types.GenerateContentConfig(response_mime_type="application/json")
    models = [
        "gemini-2.5-flash-lite",
        "gemini-2.5-flash",
        "gemini-3.1-flash-lite-preview",
    ]
    for model in models:
        try:
            res = client.models.generate_content(model=model, contents=prompt, config=config)
            data = json.loads(res.text)
            if isinstance(data, dict) and isinstance(data.get("sections"), list) and len(data["sections"]) >= 8:
                return data
        except Exception:
            continue
    return None


def normalize_sections(sections: list[dict], ledger: dict | None) -> list[dict]:
    normalized = []
    claim_map = claim_map_for_ledger(ledger)
    all_claim_ids = list(claim_map.keys())
    previous_claim_ids: list[str] = []

    for idx, section in enumerate(sections, start=1):
        narration = section.get("narration", "")
        if isinstance(narration, list):
            narration = " ".join(str(item).strip() for item in narration if str(item).strip())
        narration = " ".join(str(narration).split())
        objective = section.get("objective", "background")
        if objective not in VALID_OBJECTIVES:
            objective = "background"

        raw_claim_ids = [claim_id for claim_id in section.get("claim_ids", []) if claim_id in claim_map]
        if not raw_claim_ids:
            raw_claim_ids = infer_claim_ids(narration, all_claim_ids)
        if NUMERIC_RE.search(narration) and not raw_claim_ids:
            raw_claim_ids = previous_claim_ids[:1] if previous_claim_ids else infer_claim_ids(narration, all_claim_ids, fallback_count=2)

        normalized_section = {
            "section_id": section.get("section_id") or f"sec_{idx:03d}",
            "objective": objective,
            "narration": narration,
            "claim_ids": raw_claim_ids,
        }
        normalized.append(normalized_section)
        if raw_claim_ids:
            previous_claim_ids = raw_claim_ids
    return normalized


def source_articles_payload(articles: list[dict], ledger: dict | None) -> list[dict]:
    merged: list[dict] = []
    seen: set[str] = set()
    for article in articles:
        article_id = article.get("article_id")
        if not article_id or article_id in seen:
            continue
        merged.append(
            {
                "article_id": article_id,
                "title": article.get("title"),
                "source_name": article.get("source_name"),
                "canonical_url": article.get("canonical_url"),
                "published_at": article.get("published_at"),
            }
        )
        seen.add(article_id)
    for article in (ledger or {}).get("source_articles", []):
        article_id = article.get("article_id")
        if not article_id or article_id in seen:
            continue
        merged.append(article)
        seen.add(article_id)
    return merged


def validate_script(script: dict[str, Any], schema: dict[str, Any] | None = None) -> None:
    required = (schema or {}).get("required") or [
        "script_id", "cluster_id", "title", "tone", "description", "target_duration_sec", "source_article_ids", "ledger_id", "sections"
    ]
    missing = [field for field in required if field not in script]
    if missing:
        raise ValueError(f"script missing required fields: {missing}")
    if not script.get("source_article_ids"):
        raise ValueError("script must include source_article_ids")
    if not script.get("ledger_id"):
        raise ValueError("script must include ledger_id")
    if not isinstance(script.get("sections"), list) or len(script["sections"]) < 5:
        raise ValueError("script.sections must contain at least 5 sections")
    for section in script["sections"]:
        if not section.get("section_id") or not section.get("objective") or not section.get("narration"):
            raise ValueError(f"invalid section: {section}")
        if section["objective"] not in VALID_OBJECTIVES:
            raise ValueError(f"invalid objective: {section['objective']}")
        if NUMERIC_RE.search(section["narration"]) and not section.get("claim_ids"):
            raise ValueError(f"numeric section missing claim_ids: {section['section_id']}")


def build_fallback_sections(ledger: dict | None) -> list[dict]:
    claim_ids = list(claim_map_for_ledger(ledger).keys())
    c1 = claim_ids[:1]
    c2 = claim_ids[:2]
    return [
        {"section_id": "sec_001", "objective": "hook", "narration": "오늘 시장은 같은 숫자라도 어떤 배경에서 나왔는지에 따라 해석이 완전히 달라집니다.", "claim_ids": c1},
        {"section_id": "sec_002", "objective": "today_core", "narration": "이번 뉴스 묶음에서는 정책과 수급, 그리고 경기 민감 업종 반응이 동시에 보였습니다.", "claim_ids": c1},
        {"section_id": "sec_003", "objective": "background", "narration": "기사들을 함께 보면 단일 호재보다 여러 변수의 방향이 엇갈리는 구간이라는 점이 반복됩니다.", "claim_ids": c1},
        {"section_id": "sec_004", "objective": "evidence", "narration": "실제 기사 근거를 기준으로 보면 수출과 환율, 금리 민감도가 함께 언급되며 시장 해석의 기준점이 만들어지고 있습니다.", "claim_ids": c2},
        {"section_id": "sec_005", "objective": "etf_link", "narration": "ETF 관점에서는 개별 종목보다 어떤 변수에 민감한 섹터인지 먼저 묶어서 보는 편이 더 보수적입니다.", "claim_ids": c1},
        {"section_id": "sec_006", "objective": "implication", "narration": "즉 오늘은 방향성을 단정하기보다 어떤 지표가 다음 움직임의 조건이 되는지 정리하는 날에 가깝습니다.", "claim_ids": c1},
        {"section_id": "sec_007", "objective": "risk", "narration": "숫자 하나만 강조하면 과장 해석으로 이어질 수 있기 때문에, 출처와 시점을 함께 보는 습관이 중요합니다.", "claim_ids": c1},
        {"section_id": "sec_008", "objective": "close", "narration": "정리하면 오늘 뉴스는 단일 추천보다 근거가 쌓이는 방향을 확인하는 데 더 의미가 있습니다.", "claim_ids": c1},
    ]


def generate_stub_script(cluster: dict, articles: list[dict], ledger: dict | None) -> dict:
    title_seed = clean_title(articles[0]["title"] if articles else cluster.get("title", "오늘 경제 뉴스 핵심 정리"))
    llm_data = llm_script(cluster, articles, ledger)
    sections = normalize_sections(llm_data.get("sections", []), ledger) if llm_data else build_fallback_sections(ledger)
    script = {
        "script_id": f"scr_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "cluster_id": cluster.get("cluster_id", "evt_stub"),
        "title": clean_title((llm_data or {}).get("title", title_seed)),
        "tone": "calm_economic_explainer_ko",
        "description": (llm_data or {}).get("description", "경제 뉴스 흐름을 바탕으로 ETF 관점에서 핵심만 차분하게 정리한 롱폼 초안입니다."),
        "target_duration_sec": int((llm_data or {}).get("target_duration_sec", 240)),
        "source_article_ids": source_article_ids(articles, ledger),
        "source_articles": source_articles_payload(articles, ledger),
        "ledger_id": ledger.get("ledger_id") if ledger else None,
        "sections": sections,
    }
    validate_script(script, load_schema())
    return script


def run() -> Path:
    cluster, articles, ledger = pick_top_cluster()
    if ledger is None:
        raise FileNotFoundError("evidence ledger missing for selected cluster")
    script = generate_stub_script(cluster, articles, ledger)
    SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    output = SCRIPTS_DIR / f"{script['script_id']}.json"
    output.write_text(json.dumps(script, ensure_ascii=False, indent=2))
    print(f"saved={output}")
    return output


if __name__ == "__main__":
    run()
