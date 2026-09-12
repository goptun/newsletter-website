"""Conexão e schema do SQLite.

Sem ORM — poucas tabelas, queries simples (ver design.md Decisions:
"Storage: SQLite" — escolhido por simplicidade a esta escala)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS subscribers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'unsubscribed')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    unsubscribed_at TEXT
);

CREATE TABLE IF NOT EXISTS editions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    edition_date TEXT NOT NULL UNIQUE,
    subject TEXT,
    body TEXT,
    status TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'incomplete', 'approved', 'sent', 'rejected')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    sent_at TEXT,
    send_failures TEXT
);
"""


def get_connection(db_path: str) -> sqlite3.Connection:
    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _migrate_editions_status_check(conn: sqlite3.Connection) -> None:
    """SQLite não permite alterar um CHECK já existente — se `editions` foi
    criada antes do status 'rejected' existir (caso da produção, que já tem
    uma edição real enviada), recria a tabela com a constraint atualizada
    preservando os dados. Idempotente: não faz nada se já está em dia."""
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='editions'"
    ).fetchone()
    if row is None or "'rejected'" in row["sql"]:
        return

    conn.executescript(
        """
        CREATE TABLE editions_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            edition_date TEXT NOT NULL UNIQUE,
            subject TEXT,
            body TEXT,
            status TEXT NOT NULL DEFAULT 'draft'
                CHECK (status IN ('draft', 'incomplete', 'approved', 'sent', 'rejected')),
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            sent_at TEXT,
            send_failures TEXT
        );
        INSERT INTO editions_new SELECT * FROM editions;
        DROP TABLE editions;
        ALTER TABLE editions_new RENAME TO editions;
        """
    )


def init_db(db_path: str) -> None:
    conn = get_connection(db_path)
    try:
        conn.executescript(SCHEMA)
        _migrate_editions_status_check(conn)
        conn.commit()
    finally:
        conn.close()
