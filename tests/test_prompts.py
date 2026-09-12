"""Testes de app.generation.prompts — regressão do bug de locale: o
container de produção só tem os locales C/C.utf8/POSIX (sem pt_BR), então
`date.strftime("%B")` sempre devolvia o nome do mês em inglês (ver
histórico: draft gerado com "12 de September de 2026")."""

from __future__ import annotations

import unittest
from datetime import date

from app.generation.prompts import curiosidade_prompt


class TestCuriosidadePrompt(unittest.TestCase):
    def test_month_name_is_in_portuguese_regardless_of_system_locale(self):
        _, user = curiosidade_prompt(date(2026, 9, 12))
        self.assertIn("12 de setembro de 2026", user)
        self.assertNotIn("September", user)

    def test_covers_all_twelve_months(self):
        expected = [
            "janeiro", "fevereiro", "março", "abril", "maio", "junho",
            "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
        ]
        for month_index, month_name in enumerate(expected, start=1):
            _, user = curiosidade_prompt(date(2026, month_index, 1))
            self.assertIn(month_name, user)


if __name__ == "__main__":
    unittest.main()
