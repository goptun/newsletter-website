"""A documentação automática da API (Swagger UI / OpenAPI) fica desligada por
padrão: em produção só revelaria a superfície da API, inclusive as rotas de
revisão. As rotas reais e o /health não podem ser afetados por isso."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.api.main import app


class TestDocsDisabledByDefault(unittest.TestCase):
    def setUp(self):
        # sem lifespan (não sobe o scheduler nem toca no banco real)
        self.client = TestClient(app)

    def test_docs_and_schema_are_not_exposed(self):
        for path in ("/docs", "/redoc", "/openapi.json"):
            self.assertEqual(self.client.get(path).status_code, 404, path)

    def test_real_routes_are_still_registered(self):
        self.assertEqual(self.client.get("/health").status_code, 200)
        registered = {route.path for route in app.routes}
        for path in ("/latest", "/subscribe", "/unsubscribe", "/review/pending", "/review/page"):
            self.assertIn(path, registered)


if __name__ == "__main__":
    unittest.main()
