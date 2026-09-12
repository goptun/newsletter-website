"""Persistência de assinantes — ver specs/newsletter/subscription/spec.md."""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class InvalidEmailError(ValueError):
    pass


@dataclass
class Subscriber:
    id: int
    email: str
    status: str


def is_valid_email(email: str) -> bool:
    return bool(EMAIL_RE.match(email.strip()))


def subscribe(conn: sqlite3.Connection, email: str) -> Subscriber:
    """Requirement: Subscribe endpoint / Duplicate subscription handling.

    E-mail já ativo -> no-op (devolve o registro existente). E-mail que
    já existiu e foi cancelado -> reativa em vez de duplicar (mesma coluna
    UNIQUE de e-mail)."""
    email = email.strip().lower()
    if not is_valid_email(email):
        raise InvalidEmailError(f"E-mail inválido: {email!r}")

    existing = conn.execute(
        "SELECT id, email, status FROM subscribers WHERE email = ?", (email,)
    ).fetchone()

    if existing and existing["status"] == "active":
        return Subscriber(id=existing["id"], email=existing["email"], status="active")

    if existing:
        conn.execute(
            "UPDATE subscribers SET status = 'active', unsubscribed_at = NULL WHERE id = ?",
            (existing["id"],),
        )
        conn.commit()
        return Subscriber(id=existing["id"], email=email, status="active")

    cursor = conn.execute(
        "INSERT INTO subscribers (email, status) VALUES (?, 'active')", (email,)
    )
    conn.commit()
    return Subscriber(id=cursor.lastrowid, email=email, status="active")


def unsubscribe(conn: sqlite3.Connection, email: str) -> bool:
    """Requirement: Unsubscribe. Devolve True se um assinante ativo foi
    desativado, False se o e-mail não era um assinante ativo (no-op)."""
    email = email.strip().lower()
    cursor = conn.execute(
        "UPDATE subscribers SET status = 'unsubscribed', unsubscribed_at = datetime('now') "
        "WHERE email = ? AND status = 'active'",
        (email,),
    )
    conn.commit()
    return cursor.rowcount > 0


def list_active(conn: sqlite3.Connection) -> list[str]:
    """Requirement: Subscriber data scope — única forma de obter
    destinatários; usada pelo módulo de delivery."""
    rows = conn.execute("SELECT email FROM subscribers WHERE status = 'active'").fetchall()
    return [row["email"] for row in rows]
