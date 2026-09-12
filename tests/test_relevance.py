"""Testes de app.generation.relevance — ver specs/newsletter/content-generation/spec.md,
Requirement: News selection criteria (relevância além de atualidade/diversidade)."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from app.generation.relevance import select_relevant
from app.news.feeds import Article
from tests.fakes import FakeLLMClient


def _article(title: str, source: str = "TechCrunch") -> Article:
    return Article(
        title=title,
        url=f"https://example.com/{title}",
        source=source,
        published=datetime.now(timezone.utc),
        summary=f"Resumo de {title}.",
    )


class FakeFailingLLMClient:
    def complete(self, system: str, user: str) -> str:
        raise RuntimeError("9Router indisponível")


class TestSelectRelevant(unittest.TestCase):
    def test_empty_candidates_returns_empty_without_calling_llm(self):
        llm = FakeLLMClient([])
        result = select_relevant(llm, [], limit=6)
        self.assertEqual(result, [])
        self.assertEqual(llm.calls, [])

    def test_maps_returned_indices_back_to_articles(self):
        candidates = [_article("A"), _article("B"), _article("C")]
        llm = FakeLLMClient(["[2, 3]"])

        result = select_relevant(llm, candidates, limit=6)

        self.assertEqual([a.title for a in result], ["B", "C"])

    def test_excludes_items_not_selected_by_the_llm(self):
        candidates = [_article("Notícia real"), _article("Perfil de banda sobre iogurte")]
        llm = FakeLLMClient(["[1]"])

        result = select_relevant(llm, candidates, limit=6)

        self.assertEqual([a.title for a in result], ["Notícia real"])

    def test_respects_limit_even_if_llm_returns_more_indices(self):
        candidates = [_article("A"), _article("B"), _article("C")]
        llm = FakeLLMClient(["[1, 2, 3]"])

        result = select_relevant(llm, candidates, limit=2)

        self.assertEqual(len(result), 2)

    def test_handles_response_wrapped_in_markdown_code_fence(self):
        candidates = [_article("A"), _article("B")]
        llm = FakeLLMClient(["Aqui está minha seleção:\n```json\n[2]\n```"])

        result = select_relevant(llm, candidates, limit=6)

        self.assertEqual([a.title for a in result], ["B"])

    def test_falls_back_to_first_candidates_when_response_is_unparseable(self):
        candidates = [_article("A"), _article("B"), _article("C")]
        llm = FakeLLMClient(["desculpe, não consigo ajudar com isso"])

        result = select_relevant(llm, candidates, limit=2)

        self.assertEqual([a.title for a in result], ["A", "B"])

    def test_falls_back_when_llm_raises(self):
        candidates = [_article("A"), _article("B")]

        result = select_relevant(FakeFailingLLMClient(), candidates, limit=1)

        self.assertEqual([a.title for a in result], ["A"])

    def test_ignores_out_of_range_indices(self):
        candidates = [_article("A"), _article("B")]
        llm = FakeLLMClient(["[1, 99]"])

        result = select_relevant(llm, candidates, limit=6)

        self.assertEqual([a.title for a in result], ["A"])


if __name__ == "__main__":
    unittest.main()
