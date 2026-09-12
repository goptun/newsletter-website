"""Testes de app.api.routes_review — ver design.md Decisions: revisão
protegida por secret-link, não um sistema de auth completo, e
specs/newsletter/delivery/spec.md.

Usa um arquivo SQLite temporário com uma conexão nova por chamada da
dependência — ver o comentário equivalente em tests/test_api_subscribe.py."""

from __future__ import annotations

import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from app.api.dependencies import get_db, get_resend_client
from app.api.main import app
from app.config.settings import settings
from app.storage.db import SCHEMA, get_connection
from app.storage.editions import create_draft
from app.storage.subscribers import subscribe
from tests.fakes import FakeResendClient


class TestReviewEndpointAuth(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.conn = get_connection(self.db_path)
        self.conn.executescript(SCHEMA)
        self.edition = create_draft(self.conn, "2026-09-12", "Assunto", "Corpo")
        subscribe(self.conn, "leitor@example.com")

        self._original_token = settings.review_secret_token
        settings.review_secret_token = "segredo-de-teste"

        self.fake_resend = FakeResendClient()

        def _override_get_db():
            conn = get_connection(self.db_path)
            try:
                yield conn
            finally:
                conn.close()

        app.dependency_overrides[get_db] = _override_get_db
        app.dependency_overrides[get_resend_client] = lambda: self.fake_resend
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        settings.review_secret_token = self._original_token
        self.conn.close()
        os.remove(self.db_path)

    def test_missing_token_is_rejected(self):
        response = self.client.get("/review/pending")
        self.assertEqual(response.status_code, 422)  # token é query param obrigatório

    def test_wrong_token_is_rejected(self):
        response = self.client.get("/review/pending", params={"token": "errado"})
        self.assertEqual(response.status_code, 401)

    def test_correct_token_returns_pending_draft(self):
        response = self.client.get("/review/pending", params={"token": "segredo-de-teste"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["subject"], "Assunto")

    def test_approve_with_correct_token_sends_and_marks_sent(self):
        response = self.client.post(
            f"/review/{self.edition.id}/approve", params={"token": "segredo-de-teste"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "sent")
        self.assertEqual(len(self.fake_resend.sent), 1)

    def test_approve_with_wrong_token_does_not_send(self):
        response = self.client.post(f"/review/{self.edition.id}/approve", params={"token": "errado"})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(len(self.fake_resend.sent), 0)

    def test_reject_with_correct_token_marks_rejected_and_does_not_send(self):
        response = self.client.post(
            f"/review/{self.edition.id}/reject", params={"token": "segredo-de-teste"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "rejected")
        self.assertEqual(len(self.fake_resend.sent), 0)

    def test_reject_with_wrong_token_does_not_reject(self):
        response = self.client.post(f"/review/{self.edition.id}/reject", params={"token": "errado"})
        self.assertEqual(response.status_code, 401)

    def test_approving_an_already_rejected_edition_is_rejected_with_409(self):
        self.client.post(f"/review/{self.edition.id}/reject", params={"token": "segredo-de-teste"})

        response = self.client.post(
            f"/review/{self.edition.id}/approve", params={"token": "segredo-de-teste"}
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(len(self.fake_resend.sent), 0)

    def test_review_page_html_shows_pending_draft_with_both_actions(self):
        response = self.client.get(
            "/review/page",
            params={"token": "segredo-de-teste"},
            headers={"Accept": "text/html"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["content-type"])
        self.assertIn("Assunto", response.text)
        self.assertIn(f'action="{self.edition.id}/approve?token=segredo-de-teste"', response.text)
        self.assertIn(f'action="{self.edition.id}/reject?token=segredo-de-teste"', response.text)

    def test_review_page_html_reports_no_pending_draft(self):
        self.client.post(f"/review/{self.edition.id}/reject", params={"token": "segredo-de-teste"})

        response = self.client.get(
            "/review/page",
            params={"token": "segredo-de-teste"},
            headers={"Accept": "text/html"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Nenhum draft", response.text)

    def test_review_page_requires_correct_token(self):
        response = self.client.get("/review/page", params={"token": "errado"})
        self.assertEqual(response.status_code, 401)

    def test_approve_via_html_form_returns_confirmation_page_not_json(self):
        response = self.client.post(
            f"/review/{self.edition.id}/approve",
            params={"token": "segredo-de-teste"},
            headers={"Accept": "text/html"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["content-type"])
        self.assertIn("enviada", response.text)

    def test_reject_via_html_form_returns_confirmation_page_not_json(self):
        response = self.client.post(
            f"/review/{self.edition.id}/reject",
            params={"token": "segredo-de-teste"},
            headers={"Accept": "text/html"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["content-type"])
        self.assertIn("rejeitada", response.text)


if __name__ == "__main__":
    unittest.main()
