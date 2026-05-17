from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NORMALIZED_DIR = ROOT / "data" / "normalized"
ENTITY_RULES = {
    "한국은행": ["한국은행", "한은"],
    "연준": ["연준", "fed", "미 fed"],
    "환율": ["환율", "원달러", "달러"],
    "금리": ["금리", "기준금리"],
    "물가": ["물가", "cpi", "인플레이션"],
    "수출": ["수출"],
    "반도체": ["반도체"],
    "코스피": ["코스피"],
    "코스닥": ["코스닥"],
    "ETF": ["etf"],
}


def extract_entities(text: str) -> list[str]:
    lowered = text.lower()
    found = []
    for canonical, aliases in ENTITY_RULES.items():
        if any(alias.lower() in lowered for alias in aliases):
            found.append(canonical)
    return found


def run() -> Path:
    path = NORMALIZED_DIR / "relevance_latest.json"
    if not path.exists():
        raise FileNotFoundError("relevance_latest.json not found")
    articles = json.loads(path.read_text())
    for article in articles:
        text = f"{article.get('title', '')} {article.get('summary', '')}"
        article["entities"] = extract_entities(text)
    output = NORMALIZED_DIR / "entities_latest.json"
    output.write_text(json.dumps(articles, ensure_ascii=False, indent=2))
    print(f"saved={output}")
    return output


if __name__ == "__main__":
    run()
