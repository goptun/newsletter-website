"""Testes de app.generation.validation — ver specs/newsletter/content-generation/spec.md,
Requirements "No sponsored content" e "No editorial commentary per news item"."""

from __future__ import annotations

import unittest

from app.generation.validation import DraftValidationError, validate_draft


class TestValidateDraft(unittest.TestCase):
    def test_accepts_well_formed_draft(self):
        validate_draft(
            subject="Tema 1 / Tema 2",
            curiosidade="Curiosidade para o dia 12 de setembro: fato real.",
            news_paragraphs=[
                "Manchete: resumo objetivo da notícia. As informações são do site TechCrunch."
            ],
        )  # não deve levantar

    def test_rejects_draft_with_sponsored_teaser_in_curiosidade(self):
        with self.assertRaises(DraftValidationError) as ctx:
            validate_draft(
                subject="Tema 1",
                curiosidade=(
                    "Curiosidade para o dia X: fato. E após as notícias de hoje: propaganda."
                ),
                news_paragraphs=["Manchete: resumo. As informações são do site TechCrunch."],
            )
        self.assertTrue(any("propaganda" in v for v in ctx.exception.violations))

    def test_rejects_news_paragraph_missing_source_attribution(self):
        with self.assertRaises(DraftValidationError) as ctx:
            validate_draft(
                subject="Tema 1",
                curiosidade="Curiosidade para o dia X: fato real.",
                news_paragraphs=["Manchete: resumo sem atribuição de fonte."],
            )
        self.assertTrue(any("atribuição" in v for v in ctx.exception.violations))

    def test_rejects_empty_subject(self):
        with self.assertRaises(DraftValidationError):
            validate_draft(
                subject="",
                curiosidade="Curiosidade para o dia X: fato.",
                news_paragraphs=["Manchete: resumo. As informações são do site X."],
            )

    def test_rejects_news_paragraph_with_ad_marker(self):
        with self.assertRaises(DraftValidationError) as ctx:
            validate_draft(
                subject="Tema 1",
                curiosidade="Curiosidade para o dia X: fato real.",
                news_paragraphs=[
                    "Manchete: resumo. Use o cupom hoje. As informações são do site X."
                ],
            )
        self.assertTrue(any("propaganda" in v for v in ctx.exception.violations))


if __name__ == "__main__":
    unittest.main()
