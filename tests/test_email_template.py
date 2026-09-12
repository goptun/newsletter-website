"""Testes de app.delivery.email_template — corrige o bug relatado: o corpo
puro (parágrafos separados por linha em branco) ia direto como HTML pro
Resend, e HTML ignora quebras de linha soltas, então tudo saía junto no
e-mail. Ver também specs/newsletter/subscription/spec.md, Requirement:
Unsubscribe (link no rodapé)."""

from __future__ import annotations

import unittest

from app.delivery.email_template import render_edition_html, unsubscribe_url_for


class TestRenderEditionHtml(unittest.TestCase):
    def test_paragraphs_are_wrapped_in_separate_p_tags(self):
        body = "Curiosidade do dia: fato.\n\nManchete um: resumo um.\n\nManchete dois: resumo dois."
        html = render_edition_html(body, "leitor@example.com")

        self.assertEqual(html.count("<p"), 4)  # curiosidade + 2 notícias + rodapé

    def test_news_lead_sentence_is_bolded(self):
        body = "Curiosidade: fato.\n\nManchete importante: resumo da notícia."
        html = render_edition_html(body, "leitor@example.com")

        self.assertIn("<strong>Manchete importante:</strong> resumo da notícia.", html)

    def test_escapes_html_special_characters_from_generated_content(self):
        body = "Curiosidade: fato.\n\nEmpresa <X>: usa \"aspas\" & outras coisas."
        html = render_edition_html(body, "leitor@example.com")

        self.assertNotIn("<X>", html)
        self.assertIn("&lt;X&gt;", html)

    def test_includes_personalized_unsubscribe_link(self):
        body = "Curiosidade: fato.\n\nManchete: resumo."
        html = render_edition_html(body, "leitor@example.com")

        self.assertIn(unsubscribe_url_for("leitor@example.com"), html)

    def test_different_recipients_get_different_unsubscribe_links(self):
        body = "Curiosidade: fato.\n\nManchete: resumo."
        html_a = render_edition_html(body, "a@example.com")
        html_b = render_edition_html(body, "b@example.com")

        self.assertIn("a%40example.com", html_a)
        self.assertIn("b%40example.com", html_b)
        self.assertNotIn("a%40example.com", html_b)

    def test_empty_body_returns_empty_string(self):
        self.assertEqual(render_edition_html("", "leitor@example.com"), "")


if __name__ == "__main__":
    unittest.main()
