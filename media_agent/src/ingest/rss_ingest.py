from __future__ import annotations

import hashlib
import json
import re
import urllib.parse
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config" / "feeds.yaml"
RAW_DIR = ROOT / "data" / "raw"
NORMALIZED_DIR = ROOT / "data" / "normalized"


@dataclass
class FeedSpec:
    feed_id: str
    name: str
    url: str
    lang: str
    trust_tier: str


def load_config() -> dict[str, Any]:
    return yaml.safe_load(CONFIG_PATH.read_text())


def load_feeds() -> list[FeedSpec]:
    config = load_config()
    return [FeedSpec(**feed) for feed in config.get("feeds", [])]


def canonicalize_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=False)
    filtered = [(k, v) for k, v in query if not k.lower().startswith("utm_")]
    clean_query = urllib.parse.urlencode(filtered)
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, clean_query, ""))


def content_hash(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text.strip())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def parse_pubdate(value: str | None) -> str:
    if not value:
        return datetime.now(timezone.utc).isoformat()
    try:
        return datetime.strptime(value, "%a, %d %b %Y %H:%M:%S %z").isoformat()
    except Exception:
        return datetime.now(timezone.utc).isoformat()


def article_id(source_id: str, url: str) -> str:
    digest = hashlib.sha256(f"{source_id}:{url}".encode("utf-8")).hexdigest()[:16]
    return f"art_{digest}"


def fetch_feed(feed: FeedSpec, timeout_sec: int) -> list[dict[str, Any]]:
    response = requests.get(feed.url, timeout=timeout_sec, headers={"User-Agent": "longform-economic-agent/0.1"})
    response.raise_for_status()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = RAW_DIR / f"{feed.feed_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml"
    raw_path.write_bytes(response.content)

    root = ET.fromstring(response.content)
    items = []
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        summary = (item.findtext("description") or "").strip()
        published = parse_pubdate(item.findtext("pubDate"))
        if not title or not link:
            continue
        canonical_url = canonicalize_url(link)
        items.append(
            {
                "article_id": article_id(feed.feed_id, canonical_url),
                "source_id": feed.feed_id,
                "source_name": feed.name,
                "canonical_url": canonical_url,
                "published_at": published,
                "title": title,
                "summary": summary,
                "lang": feed.lang,
                "content_hash": content_hash(title + "\n" + summary),
                "trust_tier": feed.trust_tier,
            }
        )
    return items


def save_articles(articles: list[dict[str, Any]]) -> Path:
    NORMALIZED_DIR.mkdir(parents=True, exist_ok=True)
    output_path = NORMALIZED_DIR / f"articles_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_path.write_text(json.dumps(articles, ensure_ascii=False, indent=2))
    return output_path


def run() -> Path:
    config = load_config()
    timeout_sec = config.get("policy", {}).get("fetch_timeout_sec", 15)
    all_articles: list[dict[str, Any]] = []
    for feed in load_feeds():
        all_articles.extend(fetch_feed(feed, timeout_sec=timeout_sec))
    output = save_articles(all_articles)
    print(f"saved={output}")
    print(f"articles={len(all_articles)}")
    return output


if __name__ == "__main__":
    run()
