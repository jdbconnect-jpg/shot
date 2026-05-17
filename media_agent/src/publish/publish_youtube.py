from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RENDERS_DIR = ROOT / "data" / "renders"
SCRIPTS_DIR = ROOT / "data" / "scripts"
LEDGERS_DIR = ROOT / "data" / "ledgers"


def latest_render_path() -> Path:
    files = sorted(RENDERS_DIR.glob("rnd_*.json"))
    if not files:
        raise FileNotFoundError("render job file not found")
    return files[-1]


def latest_script_path() -> Path:
    files = sorted(SCRIPTS_DIR.glob("scr_*.json"))
    if not files:
        raise FileNotFoundError("script file not found")
    return files[-1]


def load_ledger(ledger_id: str | None) -> dict[str, Any] | None:
    if not ledger_id:
        return None
    path = LEDGERS_DIR / "evidence_ledgers_latest.json"
    if not path.exists():
        return None
    ledgers = json.loads(path.read_text())
    return next((item for item in ledgers if item.get("ledger_id") == ledger_id), None)


def unique_official_stats(ledger: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not ledger:
        return []
    seen: set[str] = set()
    items: list[dict[str, Any]] = []
    for claim in ledger.get("claims", []):
        for evidence in claim.get("evidence_items", []):
            if evidence.get("source_type") != "official_stat":
                continue
            key = evidence.get("source_ref") or evidence.get("source_title") or ""
            if not key or key in seen:
                continue
            items.append(evidence)
            seen.add(key)
    return items


def unique_calculations(ledger: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not ledger:
        return []
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for claim in ledger.get("claims", []):
        if claim.get("source_type") != "calculation" and not claim.get("calc_formula"):
            continue
        key = claim.get("claim_id") or claim.get("calc_formula") or ""
        if not key or key in seen:
            continue
        items.append(claim)
        seen.add(key)
    return items


def build_source_block(script: dict[str, Any], ledger: dict[str, Any] | None) -> str:
    lines = ["[영상 출처]"]
    source_articles = script.get("source_articles") or (ledger or {}).get("source_articles") or []
    if source_articles:
        lines.append("- 기사")
        for article in source_articles:
            title = article.get("title") or article.get("article_id") or "제목 미상"
            publisher = article.get("source_name") or article.get("publisher") or "출처 미상"
            url = article.get("canonical_url") or article.get("source_ref") or ""
            lines.append(f"  • {publisher}: {title}")
            if url:
                lines.append(f"    {url}")
    else:
        lines.append("- 기사: 연결된 기사 정보 없음")

    official_stats = unique_official_stats(ledger)
    if official_stats:
        lines.append("- 공식 통계")
        for stat in official_stats:
            title = stat.get("source_title") or stat.get("source_ref") or "공식 통계"
            value = stat.get("excerpt_or_value") or ""
            lines.append(f"  • {title}: {value}".rstrip())
    else:
        lines.append("- 공식 통계: 현재 연결된 항목 없음")

    calculations = unique_calculations(ledger)
    lines.append("- 계산 가정")
    if calculations:
        for item in calculations:
            lines.append(f"  • {item.get('claim_text', '계산 근거')}")
            if item.get("calc_formula"):
                lines.append(f"    식: {item['calc_formula']}")
    else:
        lines.append("  • 영상 내 수치가 있다면 스크립트 ledger 기준으로 검수 필요")

    lines.extend(
        [
            "",
            "[고지]",
            "- 본 영상에는 합성 음성이 포함될 수 있습니다.",
            "- 본 영상은 정보 제공 목적이며 투자 권유가 아닙니다.",
            "- 숫자와 해석은 게시 전 최종 검수가 필요합니다.",
        ]
    )
    return "\n".join(lines)


def run() -> Path:
    render_job = json.loads(latest_render_path().read_text())
    script = json.loads(latest_script_path().read_text())
    ledger = load_ledger(script.get("ledger_id"))
    artifacts = render_job.get("artifact_urls", [])
    video_path = next((item for item in artifacts if item.endswith(".mp4")), None)
    captions_path = next((item for item in artifacts if item.endswith(".srt")), None)

    payload = {
        "publish_job_id": f"pub_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "render_job_id": render_job["render_job_id"],
        "ledger_id": script.get("ledger_id"),
        "video_path": video_path,
        "captions_file": captions_path,
        "privacy_status": "private",
        "contains_synthetic_media": True,
        "title": script.get("title", "[초안] 오늘 경제 뉴스 핵심 정리"),
        "description": build_source_block(script, ledger),
        "source_article_ids": script.get("source_article_ids", []),
        "scheduled_at": datetime.now(timezone.utc).isoformat(),
        "status": "draft",
    }
    output = RENDERS_DIR / "publish_payload_latest.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"saved={output}")
    return output


if __name__ == "__main__":
    run()
