"""Testes de app.generation.pipeline — geração fim a fim usando um
FakeLLMClient (sem 9Router real) e feeds fakeados (sem rede) — ver
specs/newsletter/content-generation/spec.md."""

from __future__ import annotations

import unittest
from datetime import date, datetime, timezone
from unittest.mock import patch

from app.generation.pipeline import generate_daily_edition
from app.news.feeds import Article
from app.storage.db import SCHEMA, get_connection
from tests.fakes import FakeLLMClient


class TestGenerateDailyEdition(unittest.TestCase):
    def setUp(self):
        self.conn = get_connection(":memory:")
        self.conn.executescript(SCHEMA)
        # sem rede nos testes: a busca do texto completo da matéria vira no-op
        patcher = patch("app.generation.pipeline.enrich_with_full_text", side_effect=lambda a: a)
        self.enrich_mock = patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        self.conn.close()

    def test_no_candidates_marks_edition_incomplete_without_fabricating(self):
        with patch("app.generation.pipeline.fetch_candidates", return_value=[]):
            edition = generate_daily_edition(
                self.conn, llm_client=FakeLLMClient([]), today=date(2026, 9, 12)
            )

        self.assertEqual(edition.status, "incomplete")
        self.assertIsNone(edition.subject)

    def test_generates_draft_following_reference_structure(self):
        candidates = [
            Article(
                title="Exemplo de manchete",
                url="https://example.com/1",
                source="TechCrunch",
                published=datetime.now(timezone.utc),
                summary="Resumo da notícia de exemplo.",
            )
        ]
        fake_llm = FakeLLMClient(
            [
                "[1]",  # filtro de relevância (app.generation.relevance) seleciona o único candidato
                "Curiosidade do dia: Em 12 de setembro de 1995, fato real de tecnologia.",
                "Exemplo de manchete: resumo objetivo. As informações são do site TechCrunch.",
                "Exemplo de manchete",
            ]
        )

        with patch("app.generation.pipeline.fetch_candidates", return_value=candidates):
            edition = generate_daily_edition(self.conn, llm_client=fake_llm, today=date(2026, 9, 12))

        self.assertEqual(edition.status, "draft")
        self.assertTrue(edition.body.startswith("Curiosidade do dia: Em 12 de setembro de 1995"))
        self.assertIn("As informações são do site TechCrunch.", edition.body)
        self.assertEqual(edition.subject, "Exemplo de manchete")

    def test_invalid_generated_content_is_marked_incomplete_not_sent_as_is(self):
        candidates = [
            Article(
                title="Exemplo de manchete",
                url="https://example.com/1",
                source="TechCrunch",
                published=datetime.now(timezone.utc),
                summary="Resumo da notícia de exemplo.",
            )
        ]
        # a resposta do parágrafo de notícia nunca termina com atribuição de
        # fonte, nas 3 tentativas -> deve esgotar o loop de reprocessamento
        # (max_attempts) e só então falhar a validação determinística.
        fake_llm = FakeLLMClient(
            [
                "[1]",  # filtro de relevância seleciona o único candidato
                *(
                    [
                        "Curiosidade do dia: Em 12 de setembro de 1995, fato real.",
                        "Exemplo de manchete: resumo sem atribuição.",
                        "Exemplo de manchete",
                    ]
                    * 3
                ),
            ]
        )

        with patch("app.generation.pipeline.fetch_candidates", return_value=candidates):
            edition = generate_daily_edition(self.conn, llm_client=fake_llm, today=date(2026, 9, 12))

        self.assertEqual(edition.status, "incomplete")
        self.assertEqual(len(fake_llm.calls), 1 + 3 * 3)

    def test_retries_once_when_curiosidade_comes_back_empty(self):
        # Regressão: em produção o LLM às vezes devolve a "Curiosidade do
        # dia" vazia (estoura o orçamento de tokens de raciocínio antes do
        # conteúdo final) e a edição inteira falhava a validação mesmo
        # havendo notícia real disponível — ver app.generation.pipeline.
        # _complete_nonempty. Uma segunda tentativa deve recuperar o draft.
        candidates = [
            Article(
                title="Exemplo de manchete",
                url="https://example.com/1",
                source="TechCrunch",
                published=datetime.now(timezone.utc),
                summary="Resumo da notícia de exemplo.",
            )
        ]
        fake_llm = FakeLLMClient(
            [
                "[1]",  # filtro de relevância seleciona o único candidato
                "",  # 1ª tentativa da curiosidade: vazia
                "Curiosidade do dia: Em 12 de setembro de 1995, fato real de tecnologia.",  # retry
                "Exemplo de manchete: resumo objetivo. As informações são do site TechCrunch.",
                "Exemplo de manchete",
            ]
        )

        with patch("app.generation.pipeline.fetch_candidates", return_value=candidates):
            edition = generate_daily_edition(self.conn, llm_client=fake_llm, today=date(2026, 9, 12))

        self.assertEqual(edition.status, "draft")
        self.assertTrue(edition.body.startswith("Curiosidade do dia: Em 12 de setembro de 1995"))

    def test_reprocesses_whole_generation_after_a_failed_attempt(self):
        # Regressão: em produção (2026-09-18) a "Curiosidade do dia" veio
        # vazia mesmo após o retry individual de _complete_nonempty (o
        # modelo de raciocínio estourou o orçamento de tokens nas duas
        # chamadas), e a edição inteira foi descartada como 'incomplete'
        # mesmo com notícia real disponível. generate_daily_edition agora
        # reprocessa a geração completa (não só a chamada individual) antes
        # de desistir — ver max_attempts.
        candidates = [
            Article(
                title="Exemplo de manchete",
                url="https://example.com/1",
                source="TechCrunch",
                published=datetime.now(timezone.utc),
                summary="Resumo da notícia de exemplo.",
            )
        ]
        fake_llm = FakeLLMClient(
            [
                "[1]",  # filtro de relevância seleciona o único candidato
                # tentativa 1: curiosidade vazia nas duas chamadas do retry
                # individual -> validate_draft falha, mas o loop externo tenta de novo
                "",
                "",
                "Exemplo de manchete: resumo objetivo. As informações são do site TechCrunch.",
                "Exemplo de manchete",
                # tentativa 2: tudo certo
                "Curiosidade do dia: Em 12 de setembro de 1995, fato real de tecnologia.",
                "Exemplo de manchete: resumo objetivo. As informações são do site TechCrunch.",
                "Exemplo de manchete",
            ]
        )

        with patch("app.generation.pipeline.fetch_candidates", return_value=candidates):
            edition = generate_daily_edition(self.conn, llm_client=fake_llm, today=date(2026, 9, 12))

        self.assertEqual(edition.status, "draft")
        self.assertTrue(edition.body.startswith("Curiosidade do dia: Em 12 de setembro de 1995"))

    def test_normalizes_curiosidade_label_and_cleans_subject(self):
        # O LLM às vezes ignora o formato curto e escreve "Curiosidade para o
        # dia <data>: ..."; o assunto pode vir com aspas/ponto final.
        candidates = [
            Article(
                title="Exemplo de manchete",
                url="https://example.com/1",
                source="TechCrunch",
                published=datetime.now(timezone.utc),
                summary="Resumo da notícia de exemplo.",
            )
        ]
        fake_llm = FakeLLMClient(
            [
                "[1]",
                "Curiosidade para o dia 12 de setembro de 2026: Em 12 de setembro de 1995, fato real.",
                "Exemplo de manchete: resumo objetivo. As informações são do site TechCrunch.",
                '"Exemplo de manchete."',
            ]
        )

        with patch("app.generation.pipeline.fetch_candidates", return_value=candidates):
            edition = generate_daily_edition(self.conn, llm_client=fake_llm, today=date(2026, 9, 12))

        self.assertEqual(edition.status, "draft")
        self.assertTrue(
            edition.body.startswith("Curiosidade do dia: Em 12 de setembro de 1995, fato real.")
        )
        self.assertNotIn("para o dia", edition.body)
        self.assertEqual(edition.subject, "Exemplo de manchete")


if __name__ == "__main__":
    unittest.main()
