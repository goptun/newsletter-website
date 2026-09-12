"""Testes de app.storage.subscribers — ver specs/newsletter/subscription/spec.md."""

from __future__ import annotations

import unittest

from app.storage.db import SCHEMA, get_connection
from app.storage.subscribers import InvalidEmailError, list_active, subscribe, unsubscribe


class TestSubscribe(unittest.TestCase):
    def setUp(self):
        self.conn = get_connection(":memory:")
        self.conn.executescript(SCHEMA)

    def tearDown(self):
        self.conn.close()

    def test_new_email_is_persisted_as_active(self):
        result = subscribe(self.conn, "leitor@example.com")
        self.assertEqual(result.status, "active")
        self.assertEqual(list_active(self.conn), ["leitor@example.com"])

    def test_resubmitting_active_email_is_a_noop(self):
        subscribe(self.conn, "leitor@example.com")
        subscribe(self.conn, "leitor@example.com")
        self.assertEqual(list_active(self.conn), ["leitor@example.com"])

    def test_malformed_email_is_rejected_and_not_persisted(self):
        with self.assertRaises(InvalidEmailError):
            subscribe(self.conn, "nao-e-um-email")
        self.assertEqual(list_active(self.conn), [])

    def test_unsubscribe_excludes_from_active_list(self):
        subscribe(self.conn, "leitor@example.com")
        changed = unsubscribe(self.conn, "leitor@example.com")
        self.assertTrue(changed)
        self.assertEqual(list_active(self.conn), [])

    def test_unsubscribe_unknown_email_is_a_noop(self):
        changed = unsubscribe(self.conn, "ninguem@example.com")
        self.assertFalse(changed)

    def test_resubscribing_after_unsubscribe_reactivates_without_duplicating(self):
        subscribe(self.conn, "leitor@example.com")
        unsubscribe(self.conn, "leitor@example.com")
        subscribe(self.conn, "leitor@example.com")

        rows = self.conn.execute("SELECT COUNT(*) AS n FROM subscribers").fetchone()
        self.assertEqual(rows["n"], 1)
        self.assertEqual(list_active(self.conn), ["leitor@example.com"])


if __name__ == "__main__":
    unittest.main()
