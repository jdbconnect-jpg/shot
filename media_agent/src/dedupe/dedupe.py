from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
NORMALIZED_DIR = ROOT / "data" / "normalized"


def exact_dedupe(articles: list[dict[str, Any]]) -> dict[str, Any]:
    seen: dict[str, dict[str, Any]] = {}
    groups = []
    unique = []

    for article in articles:
        key = article["canonical_url"]
        if key in seen:
            groups.append(
                {
                    "group_id": f"dup_{len(groups) + 1:04d}",
                    "canonical_article_id": seen[key]["article_id"],
                    "members": [seen[key]["article_id"], article["article_id"]],
                    "reason": ["url_hash"],
                }
            )
        else:
            seen[key] = article
            unique.append(article)

    return {
        "groups": groups,
        "unique_articles": [a["article_id"] for a in unique],
        "unique_count": len(unique),
        "input_count": len(articles),
    }


def load_latest_articles() -> list[dict[str, Any]]:
    files = sorted(NORMALIZED_DIR.glob("articles_*.json"))
    if not files:
        raise FileNotFoundError("normalized articles file not found")
    return json.loads(files[-1].read_text())


def run() -> Path:
    articles = load_latest_articles()
    result = exact_dedupe(articles)
    output = NORMALIZED_DIR / "dedupe_result_latest.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"saved={output}")
    print(f"unique={result['unique_count']}")
    return output


if __name__ == "__main__":
    run()
