from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

sys.path.append(str(Path(__file__).resolve().parents[1]))
from prompts import CLAIM_EXTRACTION_SYSTEM, CLAIM_EXTRACTION_USER_TEMPLATE
from official_stats import fetch_official_stats_for_cluster

try:
    from google import genai
    from google.genai import types
except Exception:  # pragma: no cover
    genai = None
    types = None

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(WORKSPACE_ROOT / ".env")

ROOT = Path(__file__).resolve().parents[2]
NORMALIZED_DIR = ROOT / "data" / "normalized"
LEDGERS_DIR = ROOT / "data" / "ledgers"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def truncate(text: str, limit: int = 280) -> str:
    compact = " ".join(str(text or "").split())
    return compact[:limit].rstrip()


def article_source_record(article: dict[str, Any]) -> dict[str, Any]:
    return {
        "article_id": article.get("article_id"),
        "source_id": article.get("source_id"),
        "source_name": article.get("source_name"),
        "title": article.get("title"),
        "canonical_url": article.get("canonical_url"),
        "published_at": article.get("published_at"),
        "summary": truncate(article.get("summary", ""), 240),
        "trust_tier": article.get("trust_tier"),
    }


def evidence_item_from_article(article: dict[str, Any], *, confidence: float | None = None, notes: str | None = None) -> dict[str, Any]:
    return {
        "evidence_id": f"ev_{article.get('article_id', 'unknown')}",
        "source_type": "article",
        "source_ref": article.get("article_id") or article.get("canonical_url") or "",
        "article_id": article.get("article_id"),
        "canonical_url": article.get("canonical_url"),
        "source_title": article.get("title", ""),
        "publisher": article.get("source_name", ""),
        "published_at": article.get("published_at"),
        "excerpt_or_value": truncate(article.get("summary", article.get("title", "")), 280),
        "observed_at": article.get("published_at"),
        "checked_at": utc_now_iso(),
        "confidence": confidence,
        "notes": notes,
    }


def base_claim(cluster_id: str, idx: int, claim_text: str) -> dict[str, Any]:
    return {
        "claim_id": f"{cluster_id}_cl_{idx:02d}",
        "claim_text": truncate(claim_text, 220),
        "claim_type": "event",
        "source_type": "article",
        "source_ref": "",
        "evidence_text": "",
        "calc_formula": None,
        "support_level": "weak",
        "primary_source_required": True,
        "conflict_flag": False,
        "rewrite_policy": "attribute",
        "confidence": None,
        "uncertainty_reason": None,
        "normalized_value": None,
        "unit": None,
        "direction": None,
        "time_scope": None,
        "subject_entity_ids": [],
        "evidence_spans": [],
        "evidence_items": [],
        "checked_at": utc_now_iso(),
        "notes": None,
    }


def normalize_llm_claim(raw_claim: dict[str, Any], cluster_id: str, idx: int) -> dict[str, Any]:
    evidence_spans = raw_claim.get("evidence_spans", [])
    fallback_text = next((truncate(span, 220) for span in evidence_spans if str(span).strip()), "")
    claim = base_claim(cluster_id, idx, raw_claim.get("text") or raw_claim.get("claim_text") or fallback_text)
    claim.update(
        {
            "claim_id": str(raw_claim.get("claim_id")) if raw_claim.get("claim_id") is not None else claim["claim_id"],
            "claim_text": truncate(raw_claim.get("text") or raw_claim.get("claim_text") or fallback_text or claim["claim_text"], 220),
            "claim_type": raw_claim.get("claim_type", "event"),
            "source_type": raw_claim.get("source_type", "article"),
            "source_ref": raw_claim.get("source_ref", ""),
            "evidence_text": truncate(raw_claim.get("evidence_text") or raw_claim.get("summary") or fallback_text or "", 280),
            "calc_formula": raw_claim.get("calc_formula"),
            "support_level": raw_claim.get("support_level", "weak"),
            "primary_source_required": raw_claim.get("primary_source_required", True),
            "conflict_flag": raw_claim.get("conflict_flag", False),
            "rewrite_policy": raw_claim.get("rewrite_policy", "attribute"),
            "confidence": raw_claim.get("confidence"),
            "uncertainty_reason": raw_claim.get("uncertainty_reason"),
            "normalized_value": raw_claim.get("normalized_value"),
            "unit": raw_claim.get("unit"),
            "direction": raw_claim.get("direction"),
            "time_scope": raw_claim.get("time_scope"),
            "subject_entity_ids": raw_claim.get("subject_entity_ids", []),
            "evidence_spans": evidence_spans,
            "checked_at": utc_now_iso(),
            "notes": raw_claim.get("notes"),
        }
    )
    return claim


def llm_claims(article_bundle: list[dict[str, Any]], cluster_id: str) -> list[dict[str, Any]] | None:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or genai is None or types is None:
        return None

    prompt = (
        f"SYSTEM\n{CLAIM_EXTRACTION_SYSTEM}\n\nUSER\n"
        + CLAIM_EXTRACTION_USER_TEMPLATE.replace("{{articles_json}}", json.dumps(article_bundle, ensure_ascii=False))
        + "\n\n출력 형식: {\"claims\": [...]}"
    )
    client = genai.Client(api_key=api_key)
    config = types.GenerateContentConfig(response_mime_type="application/json")
    for model in ["gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-3.1-flash-lite-preview"]:
        try:
            res = client.models.generate_content(model=model, contents=prompt, config=config)
            data = json.loads(res.text)
            claims = data.get("claims") if isinstance(data, dict) else None
            if isinstance(claims, list) and claims:
                return [normalize_llm_claim(claim, cluster_id, idx) for idx, claim in enumerate(claims[:8], start=1)]
        except Exception:
            continue
    return None


def fallback_claims(article_bundle: list[dict[str, Any]], cluster_id: str) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    for idx, article in enumerate(article_bundle, start=1):
        claim = base_claim(cluster_id, idx, article.get("title", ""))
        evidence = evidence_item_from_article(article, confidence=0.55, notes="fallback_from_article_title")
        claim.update(
            {
                "source_type": "article",
                "source_ref": article.get("article_id") or article.get("canonical_url") or "",
                "evidence_text": truncate(article.get("summary", article.get("title", "")), 280),
                "confidence": 0.55,
                "evidence_items": [evidence],
            }
        )
        claims.append(claim)
    return claims


def attach_evidence_items(claims: list[dict[str, Any]], article_bundle: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not article_bundle:
        return claims

    article_by_id = {article.get("article_id"): article for article in article_bundle}
    for idx, claim in enumerate(claims, start=1):
        claim_ref = claim.get("source_ref")
        linked_article = article_by_id.get(claim_ref)
        if linked_article is None:
            linked_article = article_bundle[min(idx - 1, len(article_bundle) - 1)]

        evidence_items = claim.get("evidence_items") or []
        if not evidence_items:
            evidence_items = [
                evidence_item_from_article(
                    linked_article,
                    confidence=claim.get("confidence"),
                    notes="auto_linked_primary_evidence",
                )
            ]
        claim["evidence_items"] = evidence_items
        if not claim.get("source_ref"):
            claim["source_ref"] = linked_article.get("article_id") or linked_article.get("canonical_url") or ""
        if not claim.get("claim_text"):
            claim["claim_text"] = truncate(
                next((span for span in claim.get("evidence_spans", []) if str(span).strip()), "")
                or linked_article.get("title", ""),
                220,
            )
        if not claim.get("evidence_text"):
            claim["evidence_text"] = truncate(linked_article.get("summary", linked_article.get("title", "")), 280)
        if not claim.get("source_type"):
            claim["source_type"] = "article"
        claim["checked_at"] = utc_now_iso()
    return claims


def official_stat_claims(cluster_id: str, stat_items: list[dict[str, Any]], start_idx: int) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    for offset, item in enumerate(stat_items, start=0):
        idx = start_idx + offset
        claim = base_claim(cluster_id, idx, item.get("excerpt_or_value") or item.get("label") or "공식 통계")
        claim.update(
            {
                "claim_id": f"{cluster_id}_st_{offset + 1:02d}",
                "claim_type": "official_stat",
                "source_type": "official_stat",
                "source_ref": item.get("source_ref") or item.get("stat_id") or "",
                "evidence_text": item.get("excerpt_or_value") or "",
                "confidence": item.get("confidence", 0.97),
                "normalized_value": item.get("numeric_value"),
                "unit": item.get("unit"),
                "time_scope": item.get("time"),
                "support_level": "strong",
                "rewrite_policy": "state_with_source",
                "primary_source_required": False,
                "evidence_items": [item],
                "notes": item.get("notes"),
            }
        )
        claims.append(claim)
    return claims


def run() -> Path:
    clusters_path = NORMALIZED_DIR / "clusters_latest.json"
    articles_path = NORMALIZED_DIR / "entities_latest.json"
    if not clusters_path.exists() or not articles_path.exists():
        raise FileNotFoundError("cluster/article inputs missing")

    clusters = json.loads(clusters_path.read_text())
    articles = {a["article_id"]: a for a in json.loads(articles_path.read_text())}

    ledgers = []
    for cluster in clusters:
        article_bundle = [articles[article_id] for article_id in cluster.get("article_ids", [])[:5] if article_id in articles]
        claims = llm_claims(article_bundle, cluster["cluster_id"]) or fallback_claims(article_bundle, cluster["cluster_id"])
        claims = attach_evidence_items(claims, article_bundle)
        stat_items = fetch_official_stats_for_cluster(cluster)
        claims.extend(official_stat_claims(cluster["cluster_id"], stat_items, start_idx=len(claims) + 1))

        ledgers.append(
            {
                "ledger_id": f"led_{cluster['cluster_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "cluster_id": cluster["cluster_id"],
                "created_at": utc_now_iso(),
                "checked_at": utc_now_iso(),
                "source_article_ids": [article.get("article_id") for article in article_bundle if article.get("article_id")],
                "source_articles": [article_source_record(article) for article in article_bundle],
                "official_stats": stat_items,
                "claims": claims,
            }
        )

    LEDGERS_DIR.mkdir(parents=True, exist_ok=True)
    output = LEDGERS_DIR / "evidence_ledgers_latest.json"
    output.write_text(json.dumps(ledgers, ensure_ascii=False, indent=2))
    print(f"saved={output}")
    return output


if __name__ == "__main__":
    run()
