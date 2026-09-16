"""Notificação ao dono quando um novo draft está pronto para revisão — ver
design.md Risks: "o passo de aprovação manual poderia ser esquecido
silenciosamente" e Open Questions: canal de notificação (ver tasks.md 5.6)."""

from __future__ import annotations

from app.api import dependencies
from app.config.settings import settings
from app.storage.editions import Edition


def notify_draft_ready(edition: Edition, owner_email: str | None = None) -> None:
    owner_email = owner_email or settings.newsletter_owner_email
    if not owner_email:
        return  # sem destinatário configurado, não há o que notificar

    # /review/page (não /review/pending): a versão HTML com botões de
    # Aprovar/Rejeitar, clicável direto no e-mail — ver app/api/review_html.py.
    review_url = f"{settings.review_base_url}/review/page?token={settings.review_secret_token}"
    resend_client = dependencies.build_resend_client()
    resend_client.send_draft_ready_notification(owner_email, review_url, edition.edition_date)


def notify_generation_failed(edition: Edition, owner_email: str | None = None) -> None:
    """Requirement (design.md, Risks): sem isso, uma edição 'incomplete'
    (sem notícia real disponível, ou draft gerado que falhou na validação)
    ficava só num log que ninguém lê — o dono nunca sabia que aquele dia
    ficou sem draft nenhum pra revisar."""
    owner_email = owner_email or settings.newsletter_owner_email
    if not owner_email:
        return  # sem destinatário configurado, não há o que notificar

    resend_client = dependencies.build_resend_client()
    resend_client.send_generation_failed_notification(
        owner_email, edition.edition_date, edition.body or ""
    )
