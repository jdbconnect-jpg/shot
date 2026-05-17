from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NORMALIZED_DIR = ROOT / "data" / "normalized"
KEYWORDS = [
    "금리", "물가", "환율", "증시", "코스피", "코스닥", "수출", "실적", "반도체",
    "연준", "한국은행", "경제", "ETF", "채권", "달러", "인플레이션", "고용"
]


def score_article(article: dict) -> float:
    text = (article.get("title", "") + " " + article.get("summary", "")).lower()
    hits = sum(1 for keyword in KEYWORDS if keyword.lower() in text)
    return min(1.0, hits / 5)


def run() -> Path:
    files = sorted(NORMALIZED_DIR.glob("articles_*.json"))
    if not files:
        raise FileNotFoundError("normalized articles file not found")
    articles = json.loads(files[-1].read_text())
    scored = []
    for article in articles:
        score = score_article(article)
        article["relevance_score"] = score
        article["relevance_label"] = "relevant" if score >= 0.4 else "irrelevant"
        scored.append(article)

    output = NORMALIZED_DIR / "relevance_latest.json"
    output.write_text(json.dumps(scored, ensure_ascii=False, indent=2))
    print(f"saved={output}")
    return output


if __name__ == "__main__":
    run()
