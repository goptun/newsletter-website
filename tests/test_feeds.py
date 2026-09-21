"""Testes de app.news.feeds — limpeza do texto que vira base factual da
notícia (resumo do RSS ou corpo completo, sem HTML)."""

from __future__ import annotations

import unittest

from app.news.feeds import DEFAULT_FEEDS, MAX_SUMMARY_CHARS, _clean_text, _entry_text


class TestFeedText(unittest.TestCase):
    def test_clean_text_strips_tags_and_entities(self):
        raw = "<p>Empresa &amp; parceiros</p><p>Segundo <b>par\u00e1grafo</b>.</p>"
        self.assertEqual(_clean_text(raw), "Empresa & parceiros Segundo par\u00e1grafo.")

    def test_entry_text_prefers_full_content_over_short_summary(self):
        entry = {
            "summary": "<p>Resumo curto.</p>",
            "content": [{"value": "<p>Corpo completo da matéria, bem mais longo que o resumo.</p>"}],
        }
        self.assertEqual(
            _entry_text(entry), "Corpo completo da matéria, bem mais longo que o resumo."
        )

    def test_entry_text_is_capped(self):
        entry = {"summary": "palavra " * 2000}
        self.assertLessEqual(len(_entry_text(entry)), MAX_SUMMARY_CHARS + 1)

    def test_default_feeds_include_requested_sources(self):
        for source in ("BleepingComputer", "Ars Technica", "The Verge", "TechCrunch",
                       "The Register", "TechRadar", "Convergência Digital", "Micron Technology"):
            self.assertIn(source, DEFAULT_FEEDS)


if __name__ == "__main__":
    unittest.main()
