"""Scheduler in-process do job diário de geração — ver design.md Decisions:
"Scheduling: in-process scheduler (e.g., APScheduler) inside the FastAPI
service, not a separate cron container"."""

from __future__ import annotations

import logging
from datetime import date

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.api import dependencies
from app.config.settings import settings
from app.delivery.notify import notify_draft_ready, notify_generation_failed
from app.generation.pipeline import generate_daily_edition
from app.storage.db import get_connection

logger = logging.getLogger("newsletter.scheduler")


def run_daily_generation() -> None:
    """Requirement: Daily draft generation. Também acionável manualmente
    via scripts/generate_now.py (ver tasks.md 2.7), independente deste
    scheduler.

    Abre sua própria conexão SQLite: o APScheduler roda jobs em threads
    do seu próprio pool, e sqlite3.Connection não atravessa threads (ver
    app/api/dependencies.py::get_db)."""
    conn = get_connection(settings.db_path)
    try:
        llm_client = dependencies.build_llm_client()
        edition = generate_daily_edition(conn, llm_client, today=date.today())
    finally:
        conn.close()

    if edition.status == "draft":
        try:
            notify_draft_ready(edition)
        except Exception:
            logger.exception(
                "Falha ao notificar draft pronto para revisão (edição %s)", edition.edition_date
            )
    else:
        logger.warning(
            "Edição de %s ficou com status '%s' — sem notícia real utilizável ou "
            "conteúdo gerado inválido; ver app.storage.editions.Edition.body pro motivo.",
            edition.edition_date,
            edition.status,
        )
        try:
            notify_generation_failed(edition)
        except Exception:
            logger.exception(
                "Falha ao notificar o dono sobre falha na geração (edição %s)", edition.edition_date
            )


def start_scheduler(hour: int = 6, minute: int = 0) -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        run_daily_generation,
        trigger=CronTrigger(hour=hour, minute=minute),
        id="daily_newsletter_generation",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler iniciado: geração diária às %02d:%02d", hour, minute)
    return scheduler
