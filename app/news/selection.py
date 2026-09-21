"""Seleção das notícias do dia — ver specs/newsletter/content-generation/spec.md,
Requirement: News selection criteria (relevância, atualidade, qualidade da
fonte, diversidade de assuntos, utilidade pro leitor)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.news.feeds import Article

# A edição sai de manhã: 36h cobre "do dia/madrugada" com folga pra fusos e
# feeds que atrasam a publicação.
FRESH_WINDOW_HOURS = 36


def select(
    candidates: list[Article],
    limit: int = 6,
    fresh_window_hours: int = FRESH_WINDOW_HOURS,
) -> list[Article]:
    """Ordena por atualidade (mais recente primeiro) e escolhe de forma
    gulosa priorizando diversidade de fontes — no máximo `max_per_source`
    itens da mesma fonte antes de repetir — até atingir `limit`. Só entram
    itens das últimas `fresh_window_hours`; se isso deixar menos de `limit`
    itens, completa com os mais recentes fora da janela (melhor uma notícia
    de ontem do que uma edição curta).

    A "qualidade da fonte" já é garantida a montante: só se navega pelas
    fontes de app/news/feeds.DEFAULT_FEEDS, todos veículos de tecnologia
    estabelecidos."""
    if not candidates:
        return []

    def sort_key(article: Article):
        return article.published or datetime.min.replace(tzinfo=timezone.utc)

    ranked = sorted(candidates, key=sort_key, reverse=True)

    cutoff = datetime.now(timezone.utc) - timedelta(hours=fresh_window_hours)
    fresh = [a for a in ranked if a.published and a.published >= cutoff]
    pool = fresh if len(fresh) >= limit else ranked

    selected: list[Article] = []
    per_source_count: dict[str, int] = {}
    max_per_source = 2

    for article in pool:
        if len(selected) >= limit:
            break
        count = per_source_count.get(article.source, 0)
        if count >= max_per_source:
            continue
        selected.append(article)
        per_source_count[article.source] = count + 1

    if len(selected) < limit:
        remaining = [a for a in pool if a not in selected]
        selected.extend(remaining[: limit - len(selected)])

    return selected
