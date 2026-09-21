"""Coleta de notícias reais via RSS — ver design.md Decisions: "News
collection: RSS/official feeds from a curated set of reputable outlets".

Lista de fontes de tecnologia confiáveis: TechCrunch, The Verge, Ars
Technica, The Register, BleepingComputer, TechRadar, Convergência Digital,
Micron (comunicados), 9to5Google e 404 Media (ver design.md Open Questions —
extensível conforme necessário). PCMag, Citadel Securities e The Chosun Daily
não entram: os dois primeiros bloqueiam leitores de RSS (Cloudflare 403) e o
feed do Chosun é geral e em coreano, não de tecnologia."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from datetime import datetime, timezone

import feedparser

DEFAULT_FEEDS: dict[str, str] = {
    "BleepingComputer": "https://www.bleepingcomputer.com/feed/",
    "TechCrunch": "https://techcrunch.com/feed/",
    "The Verge": "https://www.theverge.com/rss/index.xml",
    "Ars Technica": "https://feeds.arstechnica.com/arstechnica/index",
    "The Register": "https://www.theregister.com/headlines.atom",
    "TechRadar": "https://www.techradar.com/feeds/articletype/news",
    "Convergência Digital": "https://convergenciadigital.com.br/feed/",
    "Micron Technology": "https://investors.micron.com/rss/pressrelease.aspx",
    "9to5Google": "https://9to5google.com/feed/",
    "404 Media": "https://www.404media.co/rss/",
}

# Texto que vai pro LLM como base factual da notícia. O resumo do RSS costuma
# ter 1-2 frases; quando o feed traz o corpo completo (content:encoded),
# usar ele dá material pra um desenvolvimento detalhado sem inventar fatos.
MAX_SUMMARY_CHARS = 3000

_TAG_RE = re.compile(r"<[^>]+>")
_BLOCK_END_RE = re.compile(r"</(p|div|li|h[1-6])>|<br\s*/?>", re.IGNORECASE)
_WS_RE = re.compile(r"\s+")


@dataclass
class Article:
    title: str
    url: str
    source: str
    published: datetime | None
    summary: str


def _clean_text(raw: str) -> str:
    """Remove tags HTML e entidades do texto do feed (vinha cru pro
    prompt e pro filtro de relevância)."""
    text = _BLOCK_END_RE.sub(" ", raw or "")
    text = html.unescape(_TAG_RE.sub("", text))
    return _WS_RE.sub(" ", text).strip()


def _entry_text(entry) -> str:
    """Prefere o maior entre o resumo e o corpo completo do feed."""
    candidates = [entry.get("summary", "")]
    candidates.extend(c.get("value", "") for c in entry.get("content", []) or [])
    cleaned = (_clean_text(c) for c in candidates)
    best = max(cleaned, key=len, default="")
    if len(best) > MAX_SUMMARY_CHARS:
        best = best[:MAX_SUMMARY_CHARS].rsplit(" ", 1)[0] + "…"
    return best


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
                    summary=_entry_text(entry),
                )
            )
    return articles
