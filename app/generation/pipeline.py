"""Orquestra a geração diária: busca -> seleção -> geração -> validação ->
persistência — ver specs/newsletter/content-generation/spec.md."""

from __future__ import annotations

import logging
import re
import sqlite3
from datetime import date

from app.generation.llm_client import NineRouterClient
from app.generation.prompts import curiosidade_prompt, news_item_prompt, subject_prompt
from app.generation.relevance import select_relevant
from app.generation.validation import DraftValidationError, validate_draft
from app.news.feeds import fetch_candidates
from app.news.selection import select
from app.storage import editions as editions_store

logger = logging.getLogger("newsletter.generation")


CURIOSIDADE_PREFIX = "Curiosidade do dia:"
_CURIOSIDADE_LEAD_RE = re.compile(r"^\s*curiosidade[^:\n]{0,60}:\s*", re.IGNORECASE)


def _normalize_curiosidade(text: str) -> str:
    """Garante o rótulo fixo 'Curiosidade do dia: ' no início — o LLM às
    vezes escreve 'Curiosidade para o dia <data>: ...' mesmo com o prompt
    pedindo o formato curto. Corrigir aqui (em vez de reprovar na
    validação) evita descartar a edição inteira por um detalhe de rótulo.
    Texto vazio passa direto pra validate_draft reportar."""
    text = text.strip()
    if not text:
        return text
    return f"{CURIOSIDADE_PREFIX} {_CURIOSIDADE_LEAD_RE.sub('', text, count=1)}"


def _clean_subject(text: str) -> str:
    return text.strip().strip("\"'“”").rstrip(".").strip()


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


def _generate_once(
    llm_client: NineRouterClient, today: date, selected: list
) -> tuple[str, str, list[str]]:
    """Uma passada de geração (assunto, curiosidade, parágrafos de notícia).
    Levanta DraftValidationError se o resultado não passar em validate_draft,
    ou a exceção original do LLM em caso de falha de chamada — quem chama
    decide se tenta de novo (ver generate_daily_edition)."""
    curiosidade_system, curiosidade_user = curiosidade_prompt(today)
    curiosidade = _normalize_curiosidade(
        _complete_nonempty(llm_client, curiosidade_system, curiosidade_user)
    )

    news_paragraphs = []
    for article in selected:
        system, user = news_item_prompt(article)
        news_paragraphs.append(_complete_nonempty(llm_client, system, user))

    subj_system, subj_user = subject_prompt([a.title for a in selected[:3]])
    subject = _clean_subject(_complete_nonempty(llm_client, subj_system, subj_user))

    validate_draft(subject, curiosidade, news_paragraphs)
    return subject, curiosidade, news_paragraphs


def generate_daily_edition(
    conn: sqlite3.Connection,
    llm_client: NineRouterClient,
    today: date | None = None,
    max_items: int = 6,
    max_attempts: int = 3,
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

    # Reprocessa a geração completa (não só a chamada individual que veio
    # vazia — ver _complete_nonempty) até max_attempts vezes: a notícia real
    # já está selecionada e não muda entre tentativas, só o texto gerado
    # pelo LLM. Sem isso, uma falha de chamada (rede/timeout) ou uma
    # violação de validate_draft (ex.: raciocínio do modelo estourando o
    # orçamento de tokens numa das chamadas, mesmo após o retry individual)
    # descartava a edição do dia como 'incomplete' — e o dono só via um
    # e-mail de "geração falhou" — mesmo havendo notícia real disponível e
    # uma boa chance de a próxima tentativa dar certo.
    last_error: str | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            subject, curiosidade, news_paragraphs = _generate_once(llm_client, today, selected)
            body = curiosidade + "\n\n" + "\n\n".join(news_paragraphs)
            return editions_store.create_draft(conn, today.isoformat(), subject, body)
        except DraftValidationError as exc:
            last_error = "Draft gerado não passou na validação: " + "; ".join(exc.violations)
        except Exception as exc:
            # Diferente de select_relevant (que tem fallback pra falha de
            # LLM), essas chamadas não têm como seguir sem resposta do
            # modelo — mas vale tentar de novo antes de desistir (ver
            # comentário do loop acima).
            last_error = f"Falha ao chamar o LLM durante a geração do conteúdo: {exc}"
        logger.warning(
            "Tentativa %d/%d de gerar a edição de %s falhou: %s",
            attempt,
            max_attempts,
            today.isoformat(),
            last_error,
        )

    return editions_store.create_incomplete(
        conn,
        today.isoformat(),
        reason=f"{last_error} (após {max_attempts} tentativas)",
    )
