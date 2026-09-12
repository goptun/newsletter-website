"""Validação determinística do draft antes de marcá-lo pronto para revisão —
ver specs/newsletter/content-generation/spec.md, Requirements "No sponsored
content" e "No editorial commentary per news item", e design.md Risks: "O
LLM pode ainda adicionar comentário editorial ou fugir da estrutura alvo
apesar do prompt"."""

from __future__ import annotations

import re

AD_TEASER_MARKERS = ("e após as notícias de hoje", "link patrocinado", "cupom")
ATTRIBUTION_RE = re.compile(r"as informações são do site .+\.\s*$", re.IGNORECASE)


class DraftValidationError(ValueError):
    def __init__(self, violations: list[str]):
        self.violations = violations
        super().__init__("; ".join(violations))


def validate_draft(subject: str, curiosidade: str, news_paragraphs: list[str]) -> None:
    violations: list[str] = []

    if not subject.strip():
        violations.append("Linha de assunto vazia")

    if not curiosidade.strip():
        violations.append("Seção 'Curiosidade do dia' vazia")

    lowered_curiosidade = curiosidade.lower()
    for marker in AD_TEASER_MARKERS:
        if marker in lowered_curiosidade:
            violations.append(f"Curiosidade contém trecho de propaganda: {marker!r}")

    if not news_paragraphs:
        violations.append("Nenhum parágrafo de notícia gerado")

    for index, paragraph in enumerate(news_paragraphs, start=1):
        if not ATTRIBUTION_RE.search(paragraph.strip()):
            violations.append(f"Notícia {index} não termina com atribuição de fonte")
        lowered = paragraph.lower()
        for marker in AD_TEASER_MARKERS:
            if marker in lowered:
                violations.append(f"Notícia {index} contém trecho de propaganda: {marker!r}")

    if violations:
        raise DraftValidationError(violations)
