"""Testes de app.delivery.notify — ver tasks.md 5.6 e design.md Risks: "o
passo de aprovação manual poderia ser esquecido silenciosamente"."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from app.config.settings import settings
from app.delivery.notify import notify_draft_ready
from app.storage.editions import Edition
from tests.fakes import FakeResendClient


class TestNotifyDraftReady(unittest.TestCase):
    def setUp(self):
        self._original_owner = settings.newsletter_owner_email
        self._original_token = settings.review_secret_token
        self._original_base_url = settings.review_base_url

    def tearDown(self):
        settings.newsletter_owner_email = self._original_owner
        settings.review_secret_token = self._original_token
        settings.review_base_url = self._original_base_url

    def test_sends_notification_when_owner_email_configured(self):
        settings.newsletter_owner_email = "dono@example.com"
        settings.review_secret_token = "segredo"
        settings.review_base_url = "http://127.0.0.1:8001"

        fake_resend = FakeResendClient()
        edition = Edition(
            id=1,
            edition_date="2026-09-12",
            subject="Assunto",
            body="Corpo",
            status="draft",
            sent_at=None,
            send_failures=None,
        )

        with patch("app.delivery.notify.dependencies.build_resend_client", return_value=fake_resend):
            notify_draft_ready(edition)

        self.assertEqual(len(fake_resend.notifications), 1)
        owner_email, review_url, edition_date = fake_resend.notifications[0]
        self.assertEqual(owner_email, "dono@example.com")
        self.assertIn("segredo", review_url)
        # /review/page (não /review/pending): a versão HTML com botões de
        # Aprovar/Rejeitar, clicável direto no e-mail.
        self.assertIn("/review/page", review_url)
        self.assertEqual(edition_date, "2026-09-12")

    def test_no_notification_when_owner_email_not_configured(self):
        settings.newsletter_owner_email = ""
        edition = Edition(
            id=1,
            edition_date="2026-09-12",
            subject="Assunto",
            body="Corpo",
            status="draft",
            sent_at=None,
            send_failures=None,
        )

        with patch("app.delivery.notify.dependencies.build_resend_client") as build_mock:
            notify_draft_ready(edition)

        build_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
