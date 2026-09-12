"""Testes de app.news.selection — ver specs/newsletter/content-generation/spec.md,
Requirement: News selection criteria."""

from __future__ import annotations

import unittest
from collections import Counter
from datetime import datetime, timedelta, timezone

from app.news.feeds import Article
from app.news.selection import select


def _article(source: str, hours_ago: int, title: str | None = None) -> Article:
    published = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    return Article(
        title=title or f"{source} story {hours_ago}h ago",
        url=f"https://example.com/{source}/{hours_ago}",
        source=source,
        published=published,
        summary="resumo",
    )


class TestSelect(unittest.TestCase):
    def test_empty_candidates_returns_empty(self):
        self.assertEqual(select([], limit=6), [])

    def test_prefers_more_recent_articles(self):
        old = _article("A", hours_ago=48)
        new = _article("A", hours_ago=1)
        selected = select([old, new], limit=1)
        self.assertEqual(selected, [new])

    def test_limits_items_per_source_for_diversity(self):
        candidates = [_article("A", h) for h in (1, 2, 3, 4)] + [_article("B", h) for h in (5, 6)]
        selected = select(candidates, limit=4)
        counts = Counter(a.source for a in selected)
        self.assertIn("B", counts)
        self.assertLessEqual(counts["A"], 2)

    def test_respects_limit(self):
        candidates = [_article("A", h) for h in range(10)]
        selected = select(candidates, limit=3)
        self.assertEqual(len(selected), 3)

    def test_fills_remaining_slots_even_if_diversity_cap_would_undershoot(self):
        # só uma fonte disponível: a diversidade não pode impedir de
        # preencher o limite quando não há outra opção.
        candidates = [_article("A", h) for h in range(5)]
        selected = select(candidates, limit=4)
        self.assertEqual(len(selected), 4)


if __name__ == "__main__":
    unittest.main()
