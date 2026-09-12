"""Testes de app.api.routes_public — usada pela página /newsletter/ do
portfolio-website (ver docs/api-contract.md)."""

from __future__ import annotations

import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from app.api.dependencies import get_db, get_resend_client
from app.api.main import app
from app.delivery.pipeline import approve_and_send
from app.storage.db import SCHEMA, get_connection
from app.storage.editions import create_draft
from app.storage.subscribers import subscribe
from tests.fakes import FakeResendClient


class TestLatestEdition(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.conn = get_connection(self.db_path)
        self.conn.executescript(SCHEMA)

        def _override_get_db():
            conn = get_connection(self.db_path)
            try:
                yield conn
            finally:
                conn.close()

        app.dependency_overrides[get_db] = _override_get_db
        app.dependency_overrides[get_resend_client] = lambda: FakeResendClient()
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.conn.close()
        os.remove(self.db_path)

    def test_no_sent_edition_returns_404(self):
        response = self.client.get("/latest")
        self.assertEqual(response.status_code, 404)

    def test_pending_draft_is_not_exposed_as_latest(self):
        create_draft(self.conn, "2026-09-12", "Assunto", "Corpo")

        response = self.client.get("/latest")

        self.assertEqual(response.status_code, 404)

    def test_returns_the_most_recently_sent_edition(self):
        subscribe(self.conn, "leitor@example.com")
        edition = create_draft(self.conn, "2026-09-12", "Assunto real", "Curiosidade.\n\nManchete: resumo.")
        approve_and_send(self.conn, edition.id, FakeResendClient())

        response = self.client.get("/latest")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["subject"], "Assunto real")
        self.assertIn("Manchete: resumo.", data["body"])
        self.assertIsNotNone(data["sent_at"])


if __name__ == "__main__":
    unittest.main()
