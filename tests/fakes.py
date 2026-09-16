"""Fakes usados nos testes — sem chamadas reais ao 9Router nem ao Resend
(mesmo padrão de rag-knowledge-assistant/tests/fakes.py)."""

from __future__ import annotations


class FakeLLMClient:
    """Devolve respostas pré-definidas, na ordem em que `complete()` é
    chamado, sem depender do 9Router nem de rede."""

    def __init__(self, responses: list[str]):
        self._responses = list(responses)
        self.calls: list[tuple[str, str]] = []

    def complete(self, system: str, user: str) -> str:
        self.calls.append((system, user))
        if not self._responses:
            raise AssertionError("FakeLLMClient esgotou as respostas configuradas")
        return self._responses.pop(0)


class FakeResendClient:
    """Substitui ResendClient nos testes de app.delivery — grava quem
    seria enviado, sem nenhuma chamada de rede. `fail_for` simula
    destinatários que o provedor rejeita."""

    def __init__(self, from_address: str = "newsletter@matheusramos.dev", fail_for: set[str] | None = None):
        self.from_address = from_address
        self.fail_for = fail_for or set()
        self.sent: list[tuple[str, str, list[str]]] = []
        self.notifications: list[tuple[str, str, str]] = []
        self.failure_notifications: list[tuple[str, str, str]] = []

    def send_bulk(self, subject: str, body: str, recipients: list[str]) -> list[str]:
        self.sent.append((subject, body, list(recipients)))
        return [r for r in recipients if r in self.fail_for]

    def send_draft_ready_notification(self, owner_email: str, review_url: str, edition_date: str) -> None:
        self.notifications.append((owner_email, review_url, edition_date))

    def send_generation_failed_notification(self, owner_email: str, edition_date: str, reason: str) -> None:
        self.failure_notifications.append((owner_email, edition_date, reason))
