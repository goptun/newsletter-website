"""Seleção das notícias do dia — ver specs/newsletter/content-generation/spec.md,
Requirement: News selection criteria (relevância, atualidade, qualidade da
fonte, diversidade de assuntos, utilidade pro leitor)."""

from __future__ import annotations

from datetime import datetime, timezone

from app.news.feeds import Article


def select(candidates: list[Article], limit: int = 6) -> list[Article]:
    """Ordena por atualidade (mais recente primeiro) e escolhe de forma
    gulosa priorizando diversidade de fontes — no máximo `max_per_source`
    itens da mesma fonte antes de repetir — até atingir `limit`.

    A "qualidade da fonte" já é garantida a montante: só se navega pelas
    fontes de app/news/feeds.DEFAULT_FEEDS, todos veículos de tecnologia
    estabelecidos."""
    if not candidates:
        return []

    def sort_key(article: Article):
        return article.published or datetime.min.replace(tzinfo=timezone.utc)

    ranked = sorted(candidates, key=sort_key, reverse=True)

    selected: list[Article] = []
    per_source_count: dict[str, int] = {}
    max_per_source = 2

    for article in ranked:
        if len(selected) >= limit:
            break
        count = per_source_count.get(article.source, 0)
        if count >= max_per_source:
            continue
        selected.append(article)
        per_source_count[article.source] = count + 1

    if len(selected) < limit:
        remaining = [a for a in ranked if a not in selected]
        selected.extend(remaining[: limit - len(selected)])

    return selected
