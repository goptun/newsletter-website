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


class InvalidEditionStateError(Exception):
    """Ação pedida (aprovar/enviar, rejeitar) não se aplica ao status atual
    da edição — ex.: tentar aprovar uma edição 'incomplete' ou 'rejected'."""

    pass


def approve_and_send(
    conn: sqlite3.Connection, edition_id: int, email_client: EmailSender
) -> editions_store.Edition:
    """Requirement: Approval triggers send / One send per approved draft.

    Aprova (se ainda em 'draft') e envia imediatamente a todos os
    assinantes ativos. Uma edição já 'sent' nunca é reenviada, e uma
    edição que não está em 'draft'/'approved' (ex.: 'incomplete',
    'rejected') nunca é enviada — sem essa checagem explícita,
    editions_store.approve() vira um no-op silencioso (só atualiza linhas
    com status='draft') e o código seguia adiante pro envio mesmo assim."""
    edition = editions_store.get_by_id(conn, edition_id)
    if edition is None:
        raise EditionNotFoundError(f"Edição {edition_id} não encontrada")

    if edition.status == "sent":
        raise AlreadySentError(f"Edição {edition_id} já foi enviada em {edition.sent_at}")

    if edition.status == "draft":
        edition = editions_store.approve(conn, edition_id)
        assert edition is not None
    elif edition.status != "approved":
        raise InvalidEditionStateError(
            f"Edição {edition_id} está com status '{edition.status}' e não pode ser enviada"
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


def reject_draft(conn: sqlite3.Connection, edition_id: int) -> editions_store.Edition:
    """O dono descarta um draft pendente em vez de aprovar — a edição some
    da fila de revisão e nunca é enviada."""
    edition = editions_store.get_by_id(conn, edition_id)
    if edition is None:
        raise EditionNotFoundError(f"Edição {edition_id} não encontrada")

    if edition.status == "sent":
        raise AlreadySentError(f"Edição {edition_id} já foi enviada em {edition.sent_at}")

    if edition.status != "draft":
        raise InvalidEditionStateError(
            f"Edição {edition_id} está com status '{edition.status}' e não pode ser rejeitada"
        )

    rejected = editions_store.reject(conn, edition_id)
    assert rejected is not None
    return rejected
