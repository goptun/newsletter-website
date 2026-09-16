"""Orquestra a geração diária: busca -> seleção -> geração -> validação ->
persistência — ver specs/newsletter/content-generation/spec.md."""

from __future__ import annotations

import sqlite3
from datetime import date

from app.generation.llm_client import NineRouterClient
from app.generation.prompts import curiosidade_prompt, news_item_prompt, subject_prompt
from app.generation.relevance import select_relevant
from app.generation.validation import DraftValidationError, validate_draft
from app.news.feeds import fetch_candidates
from app.news.selection import select
from app.storage import editions as editions_store


def _complete_nonempty(llm_client: NineRouterClient, system: str, user: str, retries: int = 1) -> str:
    """Reexecuta a chamada ao LLM quando a resposta vem vazia — sintoma
    observado em produção quando o modelo de raciocínio estoura o
    orçamento de tokens "pensando" antes do conteúdo final (ver
    settings.generation_max_tokens), o que derrubava a edição inteira pra
    'incomplete' mesmo havendo notícia real disponível."""
    result = llm_client.complete(system, user).strip()
    attempts = 0
    while not result and attempts < retries:
        attempts += 1
        result = llm_client.complete(system, user).strip()
    return result


def generate_daily_edition(
    conn: sqlite3.Connection,
    llm_client: NineRouterClient,
    today: date | None = None,
    max_items: int = 6,
) -> editions_store.Edition:
    """Requirement: Daily draft generation. Chamável diretamente (scripts/
    generate_now.py) ou pelo scheduler (app/scheduler.py) — ver tasks.md 2.7."""
    today = today or date.today()

    candidates = fetch_candidates()
    # Duas etapas: (1) narrows determinístico por atualidade/diversidade/
    # fonte (app.news.selection.select — nunca falha, serve de base segura);
    # (2) filtro semântico de relevância via LLM sobre esse pool maior (ver
    # app/generation/relevance.py) — pega o critério "isso é mesmo notícia
    # de tech?" que o passo 1 não cobre, com fallback pro resultado do
    # passo 1 se o LLM falhar.
    narrowed = select(candidates, limit=max_items * 3)
    selected = select_relevant(llm_client, narrowed, limit=max_items)

    if not selected:
        # Requirement: Real, sourced news only — sem notícia real, a edição
        # do dia fica marcada 'incomplete' em vez de inventar conteúdo.
        return editions_store.create_incomplete(
            conn,
            today.isoformat(),
            reason="Nenhuma notícia real disponível nas fontes configuradas hoje.",
        )

    curiosidade_system, curiosidade_user = curiosidade_prompt(today)
    curiosidade = _complete_nonempty(llm_client, curiosidade_system, curiosidade_user)

    news_paragraphs = []
    for article in selected:
        system, user = news_item_prompt(article)
        news_paragraphs.append(_complete_nonempty(llm_client, system, user))

    subj_system, subj_user = subject_prompt([a.title for a in selected[:3]])
    subject = _complete_nonempty(llm_client, subj_system, subj_user)

    try:
        validate_draft(subject, curiosidade, news_paragraphs)
    except DraftValidationError as exc:
        # Notícia real existia, mas o texto gerado violou a estrutura
        # exigida (propaganda residual, sem atribuição de fonte etc.) —
        # melhor marcar como incompleta pra revisão manual do que arriscar
        # aprovar/enviar conteúdo fora do padrão.
        return editions_store.create_incomplete(
            conn,
            today.isoformat(),
            reason="Draft gerado não passou na validação: " + "; ".join(exc.violations),
        )

    body = curiosidade + "\n\n" + "\n\n".join(news_paragraphs)

    return editions_store.create_draft(conn, today.isoformat(), subject, body)
