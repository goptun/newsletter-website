"""Monta os componentes reais (DB, cliente LLM, cliente Resend) — mesmo
padrão de rag-knowledge-assistant/app/api/dependencies.py.

O cliente do 9Router e o do Resend são construídos sob demanda (na
primeira vez que a dependência é usada), não no startup: assim a API sobe
e responde /health mesmo antes de LLM_MODEL/RESEND_API_KEY estarem
configurados (ver tasks.md 1.1/1.3), e falha rápido só quando a rota que
realmente precisa deles é chamada.

get_db abre uma conexão SQLite nova por request em vez de reusar uma
única conexão global: sqlite3.Connection não pode atravessar threads, e o
FastAPI roda handlers síncronos (como os deste projeto) numa threadpool —
uma conexão compartilhada quebra com
"SQLite objects created in a thread can only be used in that same thread"
assim que duas requisições caem em threads diferentes."""

from __future__ import annotations

import sqlite3
from typing import Iterator

from fastapi import Request

from app.config.settings import settings
from app.delivery.resend_client import ResendClient
from app.generation.llm_client import NineRouterClient
from app.storage.db import get_connection, init_db


def build_llm_client() -> NineRouterClient:
    return NineRouterClient(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        max_tokens=settings.generation_max_tokens,
        temperature=settings.generation_temperature,
    )


def build_resend_client() -> ResendClient:
    return ResendClient(
        api_key=settings.resend_api_key, from_address=settings.newsletter_from_address
    )


def build_db_connection() -> sqlite3.Connection:
    """Usado por scripts de processo único (scripts/generate_now.py) onde
    não há troca de thread — uma única conexão de vida curta é suficiente."""
    init_db(settings.db_path)
    return get_connection(settings.db_path)


def ensure_schema() -> None:
    init_db(settings.db_path)


def get_db() -> Iterator[sqlite3.Connection]:
    conn = get_connection(settings.db_path)
    try:
        yield conn
    finally:
        conn.close()


def get_resend_client(request: Request) -> ResendClient:
    if not hasattr(request.app.state, "resend_client"):
        request.app.state.resend_client = build_resend_client()
    return request.app.state.resend_client
