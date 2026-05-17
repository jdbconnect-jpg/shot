from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config" / "stats.json"
DATA_DIR = ROOT / "data"
CACHE_PATH = DATA_DIR / "official_stats_latest.json"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {}
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def normalize_text_set(values: list[str] | None) -> set[str]:
    return {str(value).strip().lower() for value in (values or []) if str(value).strip()}


def cluster_terms(cluster: dict[str, Any]) -> set[str]:
    terms = []
    for key in ("title", "topic"):
        if cluster.get(key):
            terms.append(str(cluster[key]))
    terms.extend(cluster.get("dominant_entities", []) or [])
    return normalize_text_set(terms)


def indicator_matches_cluster(indicator: dict[str, Any], cluster: dict[str, Any]) -> bool:
    terms = cluster_terms(cluster)
    keywords = normalize_text_set(indicator.get("topic_keywords"))
    entities = normalize_text_set(indicator.get("match_entities"))
    if not terms:
        return False
    haystack = " ".join(terms)
    return any(keyword in haystack for keyword in keywords) or any(entity in terms for entity in entities)


def latest_cache() -> dict[str, Any]:
    if not CACHE_PATH.exists():
        return {"fetched_at": None, "items": []}
    try:
        return json.loads(CACHE_PATH.read_text())
    except Exception:
        return {"fetched_at": None, "items": []}


def save_cache(items: list[dict[str, Any]]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps({"fetched_at": utc_now_iso(), "items": items}, ensure_ascii=False, indent=2))


def safe_float(value: Any) -> float | None:
    try:
        return float(str(value).replace(",", ""))
    except Exception:
        return None


def extract_latest_ecos_row(response_json: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(response_json, dict):
        return None
    for value in response_json.values():
        if isinstance(value, dict):
            rows = value.get("row")
            if isinstance(rows, list) and rows:
                return rows[-1]
    return None


def fetch_ecos(indicator: dict[str, Any], source_cfg: dict[str, Any], timeout_sec: int) -> dict[str, Any] | None:
    api_key = os.getenv(source_cfg.get("api_key_env", ""), "").strip()
    if not api_key:
        return {
            "stat_id": indicator["stat_id"],
            "provider": "ecos",
            "label": indicator.get("label", indicator["stat_id"]),
            "source_type": "official_stat",
            "source_ref": indicator.get("stat_code") or indicator["stat_id"],
            "source_title": indicator.get("label", indicator["stat_id"]),
            "canonical_url": None,
            "time": None,
            "value": None,
            "numeric_value": None,
            "unit": indicator.get("unit", ""),
            "excerpt_or_value": f"{indicator.get('label', indicator['stat_id'])} 연동 대기: {source_cfg.get('api_key_env', 'ECOS_API_KEY')} 설정 필요",
            "checked_at": utc_now_iso(),
            "confidence": 0.0,
            "notes": "missing_api_key",
        }
    path_segments = [
        api_key,
        source_cfg.get("format", "json"),
        source_cfg.get("language", "kr"),
        str(source_cfg.get("start_row", 1)),
        str(source_cfg.get("end_row", 20)),
        indicator["stat_code"],
        indicator["cycle"],
        indicator["start_time"],
        indicator["end_time"],
        indicator.get("item_code_1", "?"),
        indicator.get("item_code_2", "?"),
        indicator.get("item_code_3", "?"),
        indicator.get("item_code_4", "?"),
    ]
    path = "/".join(segment if segment not in {"", None} else "?" for segment in path_segments)
    url = f"{source_cfg['base_url'].rstrip('/')}/StatisticSearch/{path}"
    response = requests.get(url, timeout=timeout_sec)
    response.raise_for_status()
    row = extract_latest_ecos_row(response.json())
    if not row:
        return None
    time_value = row.get(indicator.get("time_field", "TIME"), "")
    value = row.get(indicator.get("value_field", "DATA_VALUE"), "")
    unit = indicator.get("unit", row.get("UNIT_NAME", ""))
    summary = indicator.get("summary_template", "{value}{unit} ({time})").format(value=value, unit=unit, time=time_value)
    return {
        "stat_id": indicator["stat_id"],
        "provider": "ecos",
        "label": indicator.get("label", indicator["stat_id"]),
        "source_type": "official_stat",
        "source_ref": indicator.get("stat_code"),
        "source_title": indicator.get("label", indicator["stat_id"]),
        "canonical_url": url,
        "time": time_value,
        "value": value,
        "numeric_value": safe_float(value),
        "unit": unit,
        "excerpt_or_value": summary,
        "checked_at": utc_now_iso(),
        "confidence": 0.98,
        "notes": "fetched_from_ecos",
    }


def extract_latest_kosis_row(data: Any) -> dict[str, Any] | None:
    if isinstance(data, list) and data:
        return data[-1]
    if isinstance(data, dict):
        for value in data.values():
            if isinstance(value, list) and value:
                return value[-1]
    return None


def fetch_kosis(indicator: dict[str, Any], source_cfg: dict[str, Any], timeout_sec: int) -> dict[str, Any] | None:
    api_key = os.getenv(source_cfg.get("api_key_env", ""), "").strip()
    if not api_key:
        return {
            "stat_id": indicator["stat_id"],
            "provider": "kosis",
            "label": indicator.get("label", indicator["stat_id"]),
            "source_type": "official_stat",
            "source_ref": indicator.get("tbl_id") or indicator["stat_id"],
            "source_title": indicator.get("label", indicator["stat_id"]),
            "canonical_url": None,
            "time": None,
            "value": None,
            "numeric_value": None,
            "unit": indicator.get("unit", ""),
            "excerpt_or_value": f"{indicator.get('label', indicator['stat_id'])} 연동 대기: {source_cfg.get('api_key_env', 'KOSIS_API_KEY')} 설정 필요",
            "checked_at": utc_now_iso(),
            "confidence": 0.0,
            "notes": "missing_api_key",
        }
    params = {
        "method": "getList",
        "apiKey": api_key,
        "format": source_cfg.get("format", "json"),
        "jsonVD": "Y",
        "userStatsId": "longform_agent",
        "prdSe": indicator.get("period_type", "M"),
        "startPrdDe": indicator.get("start_prd_de"),
        "endPrdDe": indicator.get("end_prd_de"),
        "orgId": indicator.get("org_id"),
        "tblId": indicator.get("tbl_id"),
    }
    params.update(indicator.get("items", {}))
    response = requests.get(source_cfg["base_url"], params=params, timeout=timeout_sec)
    response.raise_for_status()
    row = extract_latest_kosis_row(response.json())
    if not row:
        return None
    time_value = row.get(indicator.get("time_field", "PRD_DE"), "")
    value = row.get(indicator.get("value_field", "DT"), "")
    unit = indicator.get("unit", row.get("UNIT_NM", ""))
    summary = indicator.get("summary_template", "{value}{unit} ({time})").format(value=value, unit=unit, time=time_value)
    return {
        "stat_id": indicator["stat_id"],
        "provider": "kosis",
        "label": indicator.get("label", indicator["stat_id"]),
        "source_type": "official_stat",
        "source_ref": indicator.get("tbl_id"),
        "source_title": indicator.get("label", indicator["stat_id"]),
        "canonical_url": response.url,
        "time": time_value,
        "value": value,
        "numeric_value": safe_float(value),
        "unit": unit,
        "excerpt_or_value": summary,
        "checked_at": utc_now_iso(),
        "confidence": 0.97,
        "notes": "fetched_from_kosis",
    }


def fetch_indicator(indicator: dict[str, Any], source_cfg: dict[str, Any], timeout_sec: int) -> dict[str, Any] | None:
    provider = indicator.get("provider")
    try:
        if provider == "ecos":
            return fetch_ecos(indicator, source_cfg, timeout_sec)
        if provider == "kosis":
            return fetch_kosis(indicator, source_cfg, timeout_sec)
    except Exception as exc:
        return {
            "stat_id": indicator["stat_id"],
            "provider": provider,
            "label": indicator.get("label", indicator["stat_id"]),
            "source_type": "official_stat",
            "source_ref": indicator.get("stat_code") or indicator.get("tbl_id") or indicator["stat_id"],
            "source_title": indicator.get("label", indicator["stat_id"]),
            "canonical_url": None,
            "time": None,
            "value": None,
            "numeric_value": None,
            "unit": indicator.get("unit", ""),
            "excerpt_or_value": f"{indicator.get('label', indicator['stat_id'])} 조회 실패: {str(exc)[:120]}",
            "checked_at": utc_now_iso(),
            "confidence": 0.0,
            "notes": "fetch_error",
        }
    return None


def fetch_official_stats_for_cluster(cluster: dict[str, Any]) -> list[dict[str, Any]]:
    config = load_config()
    indicators = config.get("indicators", [])
    sources = config.get("sources", {})
    timeout_sec = int(config.get("policy", {}).get("request_timeout_sec", 12))
    max_series = int(config.get("policy", {}).get("max_series_per_cluster", 3))

    matched = [indicator for indicator in indicators if indicator_matches_cluster(indicator, cluster)]
    matched = matched[:max_series]
    items: list[dict[str, Any]] = []

    for indicator in matched:
        source_cfg = sources.get(indicator.get("provider"), {})
        if not source_cfg or not source_cfg.get("enabled", True):
            continue
        item = fetch_indicator(indicator, source_cfg, timeout_sec)
        if item:
            items.append(item)

    cache = latest_cache()
    cached_items = cache.get("items", []) if isinstance(cache, dict) else []
    # merge cached items for matched stats when live fetch unavailable
    existing_ids = {item.get("stat_id") for item in items}
    for cached in cached_items:
        if cached.get("stat_id") in existing_ids:
            continue
        if any(cached.get("stat_id") == indicator.get("stat_id") for indicator in matched):
            items.append(cached)

    if items:
        combined = {item.get("stat_id"): item for item in cached_items if item.get("stat_id")}
        for item in items:
            combined[item.get("stat_id")] = item
        save_cache(list(combined.values()))
    return items
