"""Fluxo de aprovação -> envio — ver specs/newsletter/delivery/spec.md."""

from __future__ import annotations

import sqlite3
from typing import Protocol

from app.storage import editions as editions_store
from app.storage import subscribers as subscribers_store


class EmailSender(Protocol):
    def send_bulk(self, subject: str, html_body: str, recipients: list[str]) -> list[str]: ...


class AlreadySentError(Exception):
    pass


class EditionNotFoundError(Exception):
    pass


def approve_and_send(
    conn: sqlite3.Connection, edition_id: int, email_client: EmailSender
) -> editions_store.Edition:
    """Requirement: Approval triggers send / One send per approved draft.

    Aprova (se ainda em 'draft') e envia imediatamente a todos os
    assinantes ativos. Uma edição já 'sent' nunca é reenviada."""
    edition = editions_store.get_by_id(conn, edition_id)
    if edition is None:
        raise EditionNotFoundError(f"Edição {edition_id} não encontrada")

    if edition.status == "sent":
        raise AlreadySentError(f"Edição {edition_id} já foi enviada em {edition.sent_at}")

    if edition.status != "approved":
        edition = editions_store.approve(conn, edition_id)
        if edition is None:
            raise EditionNotFoundError(
                f"Edição {edition_id} não pôde ser aprovada (status inesperado)"
            )

    recipients = subscribers_store.list_active(conn)
    failures = email_client.send_bulk(
        subject=edition.subject or "",
        html_body=edition.body or "",
        recipients=recipients,
    )

    sent_edition = editions_store.mark_sent(conn, edition_id, failures)
    assert sent_edition is not None
    return sent_edition
