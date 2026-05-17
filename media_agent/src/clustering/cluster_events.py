from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NORMALIZED_DIR = ROOT / "data" / "normalized"


def dominant_topic(article: dict) -> str:
    entities = article.get("entities") or []
    if entities:
        return entities[0]
    title = article.get("title", "")
    if "ETF" in title or "etf" in title.lower():
        return "ETF"
    return "misc"


def run() -> Path:
    path = NORMALIZED_DIR / "entities_latest.json"
    if not path.exists():
        raise FileNotFoundError("entities_latest.json not found")
    articles = json.loads(path.read_text())
    relevant = [a for a in articles if a.get("relevance_label") == "relevant"]

    grouped = defaultdict(list)
    for article in relevant:
        grouped[dominant_topic(article)].append(article)

    clusters = []
    for idx, (topic, members) in enumerate(grouped.items(), start=1):
        members.sort(key=lambda a: a.get("published_at", ""), reverse=True)
        clusters.append(
            {
                "cluster_id": f"evt_{idx:03d}",
                "title": f"{topic} 관련 뉴스 묶음",
                "topic": topic,
                "article_ids": [m["article_id"] for m in members],
                "dominant_entities": sorted({e for m in members for e in m.get("entities", [])}),
                "coherence": round(min(0.99, 0.6 + len(members) * 0.03), 2),
                "impact_score": min(95, 50 + len(members) * 4),
            }
        )

    output = NORMALIZED_DIR / "clusters_latest.json"
    output.write_text(json.dumps(clusters, ensure_ascii=False, indent=2))
    print(f"saved={output}")
    print(f"clusters={len(clusters)}")
    return output


if __name__ == "__main__":
    run()
