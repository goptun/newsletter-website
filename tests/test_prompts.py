"""Testes de app.generation.prompts — regressão do bug de locale: o
container de produção só tem os locales C/C.utf8/POSIX (sem pt_BR), então
`date.strftime("%B")` sempre devolvia o nome do mês em inglês (ver
histórico: draft gerado com "12 de September de 2026")."""

from __future__ import annotations

import unittest
from datetime import date

from app.generation.prompts import (
    curiosidade_pick_prompt,
    curiosidade_write_prompt,
    format_day_month,
    news_item_prompt,
    subject_prompt,
)
from app.news.feeds import Article
from app.news.history import HistoricalEvent


class TestCuriosidadePrompts(unittest.TestCase):
    def test_month_name_is_in_portuguese_regardless_of_system_locale(self):
        self.assertEqual(format_day_month(date(2026, 9, 12)), "12 de setembro")
        self.assertNotIn("September", format_day_month(date(2026, 9, 12)))

    def test_covers_all_twelve_months(self):
        expected = [
            "janeiro", "fevereiro", "março", "abril", "maio", "junho",
            "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
        ]
        for month_index, month_name in enumerate(expected, start=1):
            self.assertIn(month_name, format_day_month(date(2026, month_index, 1)))

    def test_pick_prompt_lists_numbered_events_with_their_years(self):
        events = [HistoricalEvent(1995, "Java released."), HistoricalEvent(1969, "ARPANET starts.")]
        system, user = curiosidade_pick_prompt(events)
        self.assertIn("1. (1995) Java released.", user)
        self.assertIn("2. (1969) ARPANET starts.", user)
        self.assertIn("tecnologia", system)
        self.assertIn("exploração espacial", system)
        self.assertIn("militares", system)

    def test_write_prompt_forbids_date_and_extra_details(self):
        system, user = curiosidade_write_prompt(HistoricalEvent(1995, "Java released."))
        self.assertIn("NÃO escreva data, ano", system)
        self.assertIn("não acrescente detalhes", system)
        self.assertIn("Java released.", user)


class TestNewsAndSubjectPrompts(unittest.TestCase):
    def test_news_prompt_asks_short_headline_and_detailed_body(self):
        article = Article(
            title="Some headline",
            url="https://example.com/1",
            source="BleepingComputer",
            published=None,
            summary="Texto da fonte.",
        )
        system, user = news_item_prompt(article)
        self.assertIn("As informações são do site BleepingComputer.", system)
        self.assertIn("no máximo 8 palavras", system)
        self.assertIn("2 a 4 frases", system)
        self.assertIn("passo a passo", system)
        self.assertIn("Texto da fonte.", user)

    def test_subject_prompt_asks_short_professional_subject(self):
        system, user = subject_prompt(["A", "B"])
        self.assertIn("60 caracteres", system)
        self.assertIn("- A", user)


if __name__ == "__main__":
    unittest.main()
