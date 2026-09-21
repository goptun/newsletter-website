"""Testes de app.generation.prompts — regressão do bug de locale: o
container de produção só tem os locales C/C.utf8/POSIX (sem pt_BR), então
`date.strftime("%B")` sempre devolvia o nome do mês em inglês (ver
histórico: draft gerado com "12 de September de 2026")."""

from __future__ import annotations

import unittest
from datetime import date

from app.generation.prompts import curiosidade_prompt, news_item_prompt, subject_prompt
from app.news.feeds import Article


class TestCuriosidadePrompt(unittest.TestCase):
    def test_month_name_is_in_portuguese_regardless_of_system_locale(self):
        _, user = curiosidade_prompt(date(2026, 9, 12))
        self.assertIn("12 de setembro", user)
        self.assertNotIn("September", user)

    def test_prompt_does_not_leak_current_year(self):
        # O ano do fato é o histórico ("Em 21 de setembro de 1995, ..."); o
        # ano atual no prompt fazia o LLM escrever "Curiosidade para o dia
        # 21 de setembro de 2026: ...".
        system, user = curiosidade_prompt(date(2026, 9, 21))
        self.assertNotIn("2026", system)
        self.assertNotIn("2026", user)
        self.assertIn("Curiosidade do dia: Em 21 de setembro de <ano>", system)

    def test_covers_all_twelve_months(self):
        expected = [
            "janeiro", "fevereiro", "março", "abril", "maio", "junho",
            "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
        ]
        for month_index, month_name in enumerate(expected, start=1):
            _, user = curiosidade_prompt(date(2026, month_index, 1))
            self.assertIn(month_name, user)


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
        self.assertIn("Texto da fonte.", user)

    def test_subject_prompt_asks_short_professional_subject(self):
        system, user = subject_prompt(["A", "B"])
        self.assertIn("60 caracteres", system)
        self.assertIn("- A", user)


if __name__ == "__main__":
    unittest.main()
