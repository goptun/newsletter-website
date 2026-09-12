"""Cliente de envio via Resend (API transacional) — ver design.md Decisions:
"Delivery: Resend API, sender newsletter@matheusramos.dev". Import do SDK é
lazy pelo mesmo motivo do cliente de LLM: não acoplar o resto do projeto a
uma lib que pode não estar instalada em contextos que não enviam e-mail
(ex.: testes)."""

from __future__ import annotations


class ResendNotConfiguredError(RuntimeError):
    pass


class ResendClient:
    def __init__(self, api_key: str, from_address: str):
        if not api_key:
            raise ResendNotConfiguredError(
                "RESEND_API_KEY não configurada. Defina no .env antes de enviar edições."
            )
        if not from_address:
            raise ResendNotConfiguredError("NEWSLETTER_FROM_ADDRESS não configurado.")

        import resend

        resend.api_key = api_key
        self._resend = resend
        self.from_address = from_address

    def send_bulk(self, subject: str, html_body: str, recipients: list[str]) -> list[str]:
        """Requirement: Delivery via transactional provider / Send status
        visibility. Envia a edição a cada destinatário e devolve a lista
        de e-mails que falharam, sem derrubar o envio aos demais."""
        failures: list[str] = []
        for recipient in recipients:
            try:
                self._resend.Emails.send(
                    {
                        "from": self.from_address,
                        "to": recipient,
                        "subject": subject,
                        "html": html_body,
                    }
                )
            except Exception:
                failures.append(recipient)
        return failures

    def send_draft_ready_notification(self, owner_email: str, review_url: str, edition_date: str) -> None:
        """Requirement (design.md, Risks): notifica o dono quando um novo
        draft está pronto pra revisão, pra que a aprovação manual não seja
        esquecida — ver tasks.md 5.6."""
        self._resend.Emails.send(
            {
                "from": self.from_address,
                "to": owner_email,
                "subject": f"Newsletter de {edition_date} pronta para revisão",
                "html": (
                    f"<p>O draft da edição de {edition_date} está pronto.</p>"
                    f'<p><a href="{review_url}">Revisar e aprovar</a></p>'
                ),
            }
        )
