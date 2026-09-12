"""Persistência de edições (drafts/incompletas/aprovadas/enviadas) — ver
specs/newsletter/content-generation/spec.md e specs/newsletter/delivery/spec.md."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass


@dataclass
class Edition:
    id: int
    edition_date: str
    subject: str | None
    body: str | None
    status: str
    sent_at: str | None
    send_failures: list[str] | None


def _row_to_edition(row: sqlite3.Row) -> Edition:
    failures = json.loads(row["send_failures"]) if row["send_failures"] else None
    return Edition(
        id=row["id"],
        edition_date=row["edition_date"],
        subject=row["subject"],
        body=row["body"],
        status=row["status"],
        sent_at=row["sent_at"],
        send_failures=failures,
    )


def create_draft(conn: sqlite3.Connection, edition_date: str, subject: str, body: str) -> Edition:
    """Requirement: Draft requires approval before send — toda edição
    nasce em status 'draft', nunca 'sent'."""
    conn.execute(
        "INSERT INTO editions (edition_date, subject, body, status) VALUES (?, ?, ?, 'draft') "
        "ON CONFLICT(edition_date) DO UPDATE SET subject=excluded.subject, body=excluded.body, "
        "status='draft', sent_at=NULL, send_failures=NULL",
        (edition_date, subject, body),
    )
    conn.commit()
    return get_by_date(conn, edition_date)  # type: ignore[return-value]


def create_incomplete(conn: sqlite3.Connection, edition_date: str, reason: str) -> Edition:
    """Requirement: Real, sourced news only — quando não há notícia real
    disponível (ou o texto gerado não passa na validação), a edição do dia
    fica marcada 'incomplete' em vez de conter conteúdo inventado."""
    conn.execute(
        "INSERT INTO editions (edition_date, subject, body, status) VALUES (?, NULL, ?, 'incomplete') "
        "ON CONFLICT(edition_date) DO UPDATE SET status='incomplete', body=excluded.body",
        (edition_date, reason),
    )
    conn.commit()
    return get_by_date(conn, edition_date)  # type: ignore[return-value]


def get_by_date(conn: sqlite3.Connection, edition_date: str) -> Edition | None:
    row = conn.execute("SELECT * FROM editions WHERE edition_date = ?", (edition_date,)).fetchone()
    return _row_to_edition(row) if row else None


def get_by_id(conn: sqlite3.Connection, edition_id: int) -> Edition | None:
    row = conn.execute("SELECT * FROM editions WHERE id = ?", (edition_id,)).fetchone()
    return _row_to_edition(row) if row else None


def get_latest_pending(conn: sqlite3.Connection) -> Edition | None:
    row = conn.execute(
        "SELECT * FROM editions WHERE status = 'draft' ORDER BY edition_date DESC LIMIT 1"
    ).fetchone()
    return _row_to_edition(row) if row else None


def approve(conn: sqlite3.Connection, edition_id: int) -> Edition | None:
    conn.execute(
        "UPDATE editions SET status = 'approved' WHERE id = ? AND status = 'draft'", (edition_id,)
    )
    conn.commit()
    return get_by_id(conn, edition_id)


def reject(conn: sqlite3.Connection, edition_id: int) -> Edition | None:
    """O dono descarta um draft pendente na revisão diária — a edição some
    da fila (get_latest_pending não a lista mais) e nunca é enviada. Só
    transiciona a partir de 'draft'; ver app/api/routes_review.py pra como
    isso é reportado quando já não se aplica (já enviada/já decidida)."""
    conn.execute(
        "UPDATE editions SET status = 'rejected' WHERE id = ? AND status = 'draft'", (edition_id,)
    )
    conn.commit()
    return get_by_id(conn, edition_id)


def mark_sent(conn: sqlite3.Connection, edition_id: int, failures: list[str]) -> Edition | None:
    """Requirement: Send status visibility — grava o resultado do envio,
    incluindo falhas por destinatário reportadas pelo provedor."""
    conn.execute(
        "UPDATE editions SET status = 'sent', sent_at = datetime('now'), send_failures = ? "
        "WHERE id = ?",
        (json.dumps(failures) if failures else None, edition_id),
    )
    conn.commit()
    return get_by_id(conn, edition_id)
