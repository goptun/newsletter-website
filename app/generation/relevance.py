"""Filtro de relevância via LLM — complementa a seleção determinística
(app/news/selection.py, que só cobre atualidade/diversidade/fonte) com o
critério que só um julgamento semântico resolve bem: "isso é realmente
notícia de tecnologia, útil pro leitor da newsletter?" (ver
specs/newsletter/content-generation/spec.md, Requirement: News selection
criteria). Fontes de tech às vezes publicam conteúdo de cultura/estilo de
vida que passa pelos filtros de atualidade/diversidade sem ser
efetivamente "notícia de tech" (ex.: perfil de banda que menciona
iogurte, encontrado na prática rodando este pipeline em produção)."""

from __future__ import annotations

import json
import logging
import re

from app.generation.llm_client import NineRouterClient
from app.news.feeds import Article

logger = logging.getLogger("newsletter.relevance")

RELEVANCE_SYSTEM = (
    "Você seleciona as notícias mais relevantes de tecnologia para uma "
    "newsletter diária, a partir de uma lista numerada de candidatos. "
    "Priorize: relevância direta com tecnologia (produtos, empresas de "
    "tech, IA, segurança, internet, ciência da computação), atualidade, "
    "diversidade de assuntos e utilidade prática pro leitor. EXCLUA itens "
    "que não sejam efetivamente sobre tecnologia — perfis/entrevistas de "
    "música, cultura, estilo de vida, humor, ou conteúdo patrocinado/"
    "publicitário, mesmo que publicados por um site de tecnologia. "
    "Responda apenas com um array JSON dos números dos itens "
    "selecionados, em ordem de prioridade, sem nenhum texto além do "
    "array — exemplo: [3, 1, 7]"
)

_JSON_ARRAY_RE = re.compile(r"\[[\d,\s]*\]")


def _format_candidate(index: int, article: Article) -> str:
    summary = (article.summary or "").strip()
    if len(summary) > 200:
        summary = summary[:200].rstrip() + "…"
    return f"{index}. [{article.source}] {article.title} — {summary}"


def _parse_selected_indices(raw: str, valid_range: range) -> list[int] | None:
    match = _JSON_ARRAY_RE.search(raw)
    if not match:
        return None
    try:
        indices = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(indices, list):
        return None

    result: list[int] = []
    for value in indices:
        if isinstance(value, int) and value in valid_range and value not in result:
            result.append(value)
    return result or None


def select_relevant(
    llm_client: NineRouterClient, candidates: list[Article], limit: int
) -> list[Article]:
    """Pede ao LLM pra escolher os itens realmente relevantes dentre os
    candidatos (já pré-filtrados por atualidade/diversidade em
    app.news.selection.select). Em caso de falha — erro de rede, resposta
    não parseável — cai de volta pros primeiros `limit` candidatos na
    ordem recebida: esse passo nunca deve, sozinho, derrubar a geração do
    dia."""
    if not candidates:
        return []

    numbered = "\n".join(_format_candidate(i, a) for i, a in enumerate(candidates, start=1))
    user = f"{numbered}\n\nSelecione até {limit} itens."

    indices: list[int] | None = None
    try:
        raw = llm_client.complete(RELEVANCE_SYSTEM, user)
        indices = _parse_selected_indices(raw, range(1, len(candidates) + 1))
    except Exception:
        logger.exception("Falha ao filtrar relevância via LLM — usando seleção determinística")

    if not indices:
        return candidates[:limit]

    return [candidates[i - 1] for i in indices[:limit]]
