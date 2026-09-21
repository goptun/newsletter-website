"""Testes de app.generation.pipeline — geração fim a fim usando um
FakeLLMClient (sem 9Router real) e feeds fakeados (sem rede) — ver
specs/newsletter/content-generation/spec.md."""

from __future__ import annotations

import unittest
from datetime import date, datetime, timezone
from unittest.mock import patch

from app.generation.pipeline import generate_daily_edition
from app.news.feeds import Article
from app.news.history import HistoricalEvent
from app.storage.db import SCHEMA, get_connection
from tests.fakes import FakeLLMClient


EVENTS = [
    HistoricalEvent(year=1995, text="Sun Microsystems releases the first public version of Java."),
    HistoricalEvent(year=1969, text="The first ARPANET message is sent."),
]


class TestGenerateDailyEdition(unittest.TestCase):
    def setUp(self):
        self.conn = get_connection(":memory:")
        self.conn.executescript(SCHEMA)
        # sem rede nos testes: a busca do texto completo da matéria vira no-op
        patcher = patch("app.generation.pipeline.enrich_with_full_text", side_effect=lambda a: a)
        self.enrich_mock = patcher.start()
        self.addCleanup(patcher.stop)
        # sem rede nos testes: eventos históricos da Wikipedia fixos
        events_patcher = patch("app.generation.pipeline.fetch_events", return_value=EVENTS)
        self.fetch_events_mock = events_patcher.start()
        self.addCleanup(events_patcher.stop)

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
                "1",  # escolha do evento
                "a Sun lançou a primeira versão pública do Java.",
                "Exemplo de manchete: resumo objetivo. As informações são do site TechCrunch.",
                "Exemplo de manchete",
            ]
        )

        with patch("app.generation.pipeline.fetch_candidates", return_value=candidates):
            edition = generate_daily_edition(self.conn, llm_client=fake_llm, today=date(2026, 9, 12))

        self.assertEqual(edition.status, "draft")
        self.assertTrue(
            edition.body.startswith(
                "Curiosidade do dia: Em 12 de setembro de 1995, a Sun lançou a primeira versão pública do Java."
            )
        )
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
                        "1",
                        "a Sun lançou a primeira versão pública do Java.",
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
        self.assertEqual(len(fake_llm.calls), 1 + 3 * 4)

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
                "1",  # escolha do evento
                "",  # 1ª tentativa da reescrita: vazia
                "a Sun lançou a primeira versão pública do Java.",  # retry
                "Exemplo de manchete: resumo objetivo. As informações são do site TechCrunch.",
                "Exemplo de manchete",
            ]
        )

        with patch("app.generation.pipeline.fetch_candidates", return_value=candidates):
            edition = generate_daily_edition(self.conn, llm_client=fake_llm, today=date(2026, 9, 12))

        self.assertEqual(edition.status, "draft")
        self.assertTrue(
            edition.body.startswith(
                "Curiosidade do dia: Em 12 de setembro de 1995, a Sun lançou a primeira versão pública do Java."
            )
        )

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
                # tentativa 1: reescrita da curiosidade vazia nas duas chamadas do
                # retry individual -> validate_draft falha, mas o loop externo
                # tenta de novo
                "1",  # escolha do evento
                "",
                "",
                "Exemplo de manchete: resumo objetivo. As informações são do site TechCrunch.",
                "Exemplo de manchete",
                # tentativa 2: tudo certo
                "1",  # escolha do evento
                "a Sun lançou a primeira versão pública do Java.",
                "Exemplo de manchete: resumo objetivo. As informações são do site TechCrunch.",
                "Exemplo de manchete",
            ]
        )

        with patch("app.generation.pipeline.fetch_candidates", return_value=candidates):
            edition = generate_daily_edition(self.conn, llm_client=fake_llm, today=date(2026, 9, 12))

        self.assertEqual(edition.status, "draft")
        self.assertTrue(
            edition.body.startswith(
                "Curiosidade do dia: Em 12 de setembro de 1995, a Sun lançou a primeira versão pública do Java."
            )
        )

    def _one_candidate(self):
        return [
            Article(
                title="Exemplo de manchete",
                url="https://example.com/1",
                source="TechCrunch",
                published=datetime.now(timezone.utc),
                summary="Resumo da notícia de exemplo.",
            )
        ]

    def test_curiosidade_date_and_year_come_from_the_wikipedia_event_not_the_llm(self):
        # O modelo não escreve data nem ano: mesmo que tente ("Em 2026, ..."),
        # o prefixo vem do código com o ano real do evento escolhido; artigo
        # inicial vira minúscula pra encaixar depois da vírgula.
        fake_llm = FakeLLMClient(
            [
                "[1]",
                "Evento 2",  # escolhe o 2º evento (ARPANET, 1969); só o 1º inteiro conta
                "A primeira mensagem da ARPANET foi enviada",
                "Exemplo de manchete: resumo objetivo. As informações são do site TechCrunch.",
                "Exemplo de manchete",
            ]
        )
        with patch("app.generation.pipeline.fetch_candidates", return_value=self._one_candidate()):
            edition = generate_daily_edition(self.conn, llm_client=fake_llm, today=date(2026, 9, 21))

        self.assertEqual(edition.status, "draft")
        self.assertTrue(
            edition.body.startswith(
                "Curiosidade do dia: Em 21 de setembro de 1969, a primeira mensagem da ARPANET foi enviada."
            )
        )

    def test_cleans_subject_and_replaces_special_hyphens_and_spaces(self):
        fake_llm = FakeLLMClient(
            [
                "[1]",
                "1",
                "a Sun lançou o Java.",
                "Falha 0\u2011day no Muse: custa US$\u00a0249. As informações são do site TechCrunch.",
                '"Falha 0\u2011day no Muse."',
            ]
        )
        with patch("app.generation.pipeline.fetch_candidates", return_value=self._one_candidate()):
            edition = generate_daily_edition(self.conn, llm_client=fake_llm, today=date(2026, 9, 12))

        self.assertEqual(edition.subject, "Falha 0-day no Muse")
        self.assertIn("Falha 0-day no Muse: custa US$ 249.", edition.body)
        self.assertNotIn("\u2011", edition.body)
        self.assertNotIn("\u00a0", edition.body)

    def test_invalid_event_choice_fails_validation_instead_of_guessing(self):
        fake_llm = FakeLLMClient(["[1]"] + ["99"] * 3)
        with patch("app.generation.pipeline.fetch_candidates", return_value=self._one_candidate()):
            edition = generate_daily_edition(self.conn, llm_client=fake_llm, today=date(2026, 9, 12))

        self.assertEqual(edition.status, "incomplete")
        self.assertIn("escolha de evento inválida", edition.body)

    def test_wikipedia_unavailable_marks_incomplete_without_inventing_a_fact(self):
        fake_llm = FakeLLMClient(["[1]"])
        self.fetch_events_mock.side_effect = RuntimeError("Wikipedia On This Day indisponível")
        with patch("app.generation.pipeline.fetch_candidates", return_value=self._one_candidate()):
            edition = generate_daily_edition(self.conn, llm_client=fake_llm, today=date(2026, 9, 12))

        self.assertEqual(edition.status, "incomplete")
        self.assertIn("Wikipedia", edition.body)
        self.assertEqual(len(fake_llm.calls), 1)  # só o filtro de relevância; nada de curiosidade inventada


if __name__ == "__main__":
    unittest.main()
