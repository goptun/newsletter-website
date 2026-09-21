"""Testes de app.news.feeds — limpeza do texto que vira base factual da
notícia (resumo do RSS ou corpo completo, sem HTML)."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from app.news.feeds import (
    DEFAULT_FEEDS,
    MAX_SUMMARY_CHARS,
    MIN_RSS_TEXT_CHARS,
    Article,
    _clean_text,
    _entry_text,
    _extract_article_text,
    enrich_with_full_text,
)


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


PAGE = """
<html><body>
<nav><p>Menu de navegação bem comprido que não faz parte da matéria em si</p></nav>
<article>
  <p>Primeiro parágrafo da matéria, com informação suficiente para contar.</p>
  <p>curto</p>
  <p>Segundo parágrafo com <a href="#">link</a> e mais detalhes importantes do caso.</p>
  <script>var x = "<p>não deve entrar no texto extraído da página</p>";</script>
</article>
<footer><p>Rodapé com texto longo o bastante para passar do filtro de tamanho mínimo</p></footer>
<p>Parágrafo solto fora do article que não deve entrar quando há article na página.</p>
</body></html>
"""


class TestArticleTextExtraction(unittest.TestCase):
    def test_extracts_only_article_paragraphs_without_boilerplate(self):
        text = _extract_article_text(PAGE)
        self.assertIn("Primeiro parágrafo da matéria", text)
        self.assertIn("Segundo parágrafo com link e mais detalhes", text)
        self.assertNotIn("Menu de navegação", text)
        self.assertNotIn("Rodapé", text)
        self.assertNotIn("solto", text)
        self.assertNotIn("curto", text.split("Primeiro")[0])

    def test_falls_back_to_all_paragraphs_when_no_article_tag(self):
        html_no_article = "<body><p>Um parágrafo longo o suficiente para ser considerado texto da matéria.</p></body>"
        self.assertIn("Um parágrafo longo", _extract_article_text(html_no_article))


def _article(summary: str) -> Article:
    return Article(title="T", url="https://example.com/a", source="S", published=None, summary=summary)


class TestEnrichWithFullText(unittest.TestCase):
    def test_replaces_short_rss_text_with_longer_page_text(self):
        with patch("app.news.feeds.fetch_article_text", return_value="texto completo " * 30):
            [result] = enrich_with_full_text([_article("curto")])
        self.assertTrue(result.summary.startswith("texto completo"))

    def test_keeps_rss_text_when_fetch_fails(self):
        with patch("app.news.feeds.fetch_article_text", return_value=""):
            [result] = enrich_with_full_text([_article("resumo do rss")])
        self.assertEqual(result.summary, "resumo do rss")

    def test_does_not_fetch_when_rss_text_is_already_long(self):
        with patch("app.news.feeds.fetch_article_text") as fetch:
            enrich_with_full_text([_article("x" * MIN_RSS_TEXT_CHARS)])
        fetch.assert_not_called()

    def test_fetch_article_text_returns_empty_string_on_network_error(self):
        from app.news.feeds import fetch_article_text

        with patch("app.news.feeds.httpx.get", side_effect=RuntimeError("boom")):
            self.assertEqual(fetch_article_text("https://example.com/a"), "")


if __name__ == "__main__":
    unittest.main()
