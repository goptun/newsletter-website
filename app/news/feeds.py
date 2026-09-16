"""Coleta de notícias reais via RSS — ver design.md Decisions: "News
collection: RSS/official feeds from a curated set of reputable outlets".

Lista inicial de fontes de tecnologia confiáveis: TechCrunch, The Verge,
Ars Technica, The Register, BleepingComputer, 9to5Google e 404 Media (ver
design.md Open Questions — extensível conforme necessário)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import feedparser

DEFAULT_FEEDS: dict[str, str] = {
    "BleepingComputer": "https://www.bleepingcomputer.com/feed/",
    "TechCrunch": "https://techcrunch.com/feed/",
    "The Verge": "https://www.theverge.com/rss/index.xml",
    "Ars Technica": "https://feeds.arstechnica.com/arstechnica/index",
    "The Register": "https://www.theregister.com/headlines.atom",
    "9to5Google": "https://9to5google.com/feed/",
    "404 Media": "https://www.404media.co/rss/",
}


@dataclass
class Article:
    title: str
    url: str
    source: str
    published: datetime | None
    summary: str


def _parse_published(entry) -> datetime | None:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if not parsed:
        return None
    return datetime(*parsed[:6], tzinfo=timezone.utc)


def fetch_candidates(feeds: dict[str, str] | None = None, per_feed_limit: int = 10) -> list[Article]:
    """Requirement: Real, sourced news only — cada Article vem de um item
    de feed real, nunca inventado. Uma fonte fora do ar é simplesmente
    ignorada (não interrompe a coleta das demais); é o chamador (ver
    app/news/selection.py e app/generation/pipeline.py) quem decide o que
    fazer se a lista final vier vazia."""
    feeds = feeds or DEFAULT_FEEDS
    articles: list[Article] = []
    for source, feed_url in feeds.items():
        try:
            parsed_feed = feedparser.parse(feed_url)
        except Exception:
            continue
        for entry in parsed_feed.entries[:per_feed_limit]:
            title = entry.get("title")
            link = entry.get("link")
            if not title or not link:
                continue
            articles.append(
                Article(
                    title=title,
                    url=link,
                    source=source,
                    published=_parse_published(entry),
                    summary=entry.get("summary", ""),
                )
            )
    return articles
