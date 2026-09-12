#!/usr/bin/env python3
"""Dispara a geração da edição do dia manualmente, independente do
scheduler — ver tasks.md 2.7.

Uso:
    python scripts/generate_now.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.api import dependencies  # noqa: E402
from app.generation.pipeline import generate_daily_edition  # noqa: E402


def main() -> None:
    conn = dependencies.build_db_connection()
    llm_client = dependencies.build_llm_client()
    edition = generate_daily_edition(conn, llm_client)
    print(f"Edição {edition.edition_date}: status={edition.status}")
    if edition.subject:
        print(f"Assunto: {edition.subject}")
    if edition.status == "incomplete":
        print(f"Motivo: {edition.body}")


if __name__ == "__main__":
    main()
