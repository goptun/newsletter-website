"""Testes de app.api.routes_subscribe — usa app.dependency_overrides, mesmo
padrão de rag-knowledge-assistant/tests/test_api.py, sem subir o lifespan
real (TestClient sem 'with' não dispara startup/shutdown).

Usa um arquivo SQLite temporário (não ":memory:") com uma conexão nova por
chamada da dependência, espelhando exatamente o get_db de produção — o
TestClient do FastAPI despacha handlers síncronos numa threadpool, e uma
única conexão sqlite3 compartilhada entre threads levanta
"SQLite objects created in a thread can only be used in that same thread"."""

from __future__ import annotations

import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from app.api.dependencies import get_db
from app.api.main import app
from app.storage.db import SCHEMA, get_connection


class TestSubscribeEndpoint(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.conn = get_connection(self.db_path)
        self.conn.executescript(SCHEMA)
        self.conn.commit()

        def _override_get_db():
            conn = get_connection(self.db_path)
            try:
                yield conn
            finally:
                conn.close()

        app.dependency_overrides[get_db] = _override_get_db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.conn.close()
        os.remove(self.db_path)

    def test_subscribe_valid_email_returns_success(self):
        response = self.client.post("/subscribe", json={"email": "leitor@example.com"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "subscribed")

    def test_subscribe_malformed_email_returns_422(self):
        response = self.client.post("/subscribe", json={"email": "invalido"})
        self.assertEqual(response.status_code, 422)

    def test_subscribe_duplicate_email_is_still_a_success_noop(self):
        self.client.post("/subscribe", json={"email": "leitor@example.com"})
        response = self.client.post("/subscribe", json={"email": "leitor@example.com"})
        self.assertEqual(response.status_code, 200)
        rows = self.conn.execute("SELECT COUNT(*) AS n FROM subscribers").fetchone()
        self.assertEqual(rows["n"], 1)

    def test_unsubscribe_known_email_returns_success(self):
        self.client.post("/subscribe", json={"email": "leitor@example.com"})
        response = self.client.post("/unsubscribe", json={"email": "leitor@example.com"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "unsubscribed")


if __name__ == "__main__":
    unittest.main()
