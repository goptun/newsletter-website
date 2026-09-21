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
import logging
import re
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from html.parser import HTMLParser

import feedparser
import httpx

logger = logging.getLogger("newsletter.feeds")

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

# Abaixo disso o RSS não dá material pra um desenvolvimento de 2-4 frases
# (ex.: BleepingComputer e 9to5Google mandam só 1-2 frases), e o LLM acaba
# completando com generalidades — então busca-se o texto da matéria na URL.
MIN_RSS_TEXT_CHARS = 800
ARTICLE_FETCH_TIMEOUT = 10.0
_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

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


class _ArticleTextParser(HTMLParser):
    """Extrai os parágrafos do corpo da matéria: usa só <p> dentro de
    <article> quando existir (senão todos os <p>), ignorando menus,
    rodapés, scripts e parágrafos curtos de interface."""

    _SKIP = {"script", "style", "nav", "footer", "aside", "header", "form", "noscript"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._article_depth = 0
        self._in_p = False
        self._buf: list[str] = []
        self.article_paragraphs: list[str] = []
        self.all_paragraphs: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP:
            self._skip_depth += 1
        elif tag == "article":
            self._article_depth += 1
        elif tag == "p" and not self._skip_depth:
            self._in_p, self._buf = True, []

    def handle_endtag(self, tag):
        if tag in self._SKIP and self._skip_depth:
            self._skip_depth -= 1
        elif tag == "article" and self._article_depth:
            self._article_depth -= 1
        elif tag == "p" and self._in_p:
            self._in_p = False
            text = _WS_RE.sub(" ", "".join(self._buf)).strip()
            if len(text) >= 40:
                self.all_paragraphs.append(text)
                if self._article_depth:
                    self.article_paragraphs.append(text)

    def handle_data(self, data):
        if self._in_p and not self._skip_depth:
            self._buf.append(data)


def _extract_article_text(page_html: str) -> str:
    parser = _ArticleTextParser()
    parser.feed(page_html)
    paragraphs = parser.article_paragraphs or parser.all_paragraphs
    text = " ".join(paragraphs)
    if len(text) > MAX_SUMMARY_CHARS:
        text = text[:MAX_SUMMARY_CHARS].rsplit(" ", 1)[0] + "…"
    return text


def fetch_article_text(url: str, timeout: float = ARTICLE_FETCH_TIMEOUT) -> str:
    """Baixa a página da matéria e devolve o texto dos parágrafos, ou "" em
    qualquer falha (bloqueio, timeout, HTML sem parágrafos) — o chamador
    segue com o texto do RSS."""
    try:
        response = httpx.get(
            url,
            headers={"User-Agent": _BROWSER_UA, "Accept-Language": "en,pt;q=0.8"},
            timeout=timeout,
            follow_redirects=True,
        )
        response.raise_for_status()
        return _extract_article_text(response.text)
    except Exception as exc:
        logger.info("Sem texto completo de %s (%s) — usando o resumo do RSS", url, exc)
        return ""


def enrich_with_full_text(articles: list[Article]) -> list[Article]:
    """Para cada notícia cujo texto do RSS é curto (< MIN_RSS_TEXT_CHARS),
    tenta trocá-lo pelo texto da matéria — só se o da página for de fato
    maior. Chamado só nas notícias já selecionadas (poucas requisições)."""
    enriched: list[Article] = []
    for article in articles:
        if len(article.summary) < MIN_RSS_TEXT_CHARS:
            full_text = fetch_article_text(article.url)
            if len(full_text) > len(article.summary):
                article = replace(article, summary=full_text)
        enriched.append(article)
    return enriched


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
