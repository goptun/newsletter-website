"""Testes de app.delivery.pipeline — ver specs/newsletter/delivery/spec.md."""

from __future__ import annotations

import unittest

from app.delivery.pipeline import AlreadySentError, EditionNotFoundError, approve_and_send
from app.storage.db import SCHEMA, get_connection
from app.storage.editions import create_draft
from app.storage.subscribers import subscribe, unsubscribe
from tests.fakes import FakeResendClient


class TestApproveAndSend(unittest.TestCase):
    def setUp(self):
        self.conn = get_connection(":memory:")
        self.conn.executescript(SCHEMA)
        subscribe(self.conn, "a@example.com")
        subscribe(self.conn, "b@example.com")
        self.edition = create_draft(self.conn, "2026-09-12", "Assunto", "Corpo da edição")

    def tearDown(self):
        self.conn.close()

    def test_approve_sends_to_all_active_subscribers(self):
        resend = FakeResendClient()
        result = approve_and_send(self.conn, self.edition.id, resend)

        self.assertEqual(result.status, "sent")
        self.assertIsNotNone(result.sent_at)
        self.assertEqual(len(resend.sent), 1)
        _, _, recipients = resend.sent[0]
        self.assertCountEqual(recipients, ["a@example.com", "b@example.com"])

    def test_unsubscribed_emails_are_not_sent_to(self):
        unsubscribe(self.conn, "b@example.com")

        resend = FakeResendClient()
        approve_and_send(self.conn, self.edition.id, resend)

        _, _, recipients = resend.sent[0]
        self.assertEqual(recipients, ["a@example.com"])

    def test_resending_an_already_sent_edition_raises_instead_of_resending(self):
        resend = FakeResendClient()
        approve_and_send(self.conn, self.edition.id, resend)

        with self.assertRaises(AlreadySentError):
            approve_and_send(self.conn, self.edition.id, resend)

        self.assertEqual(len(resend.sent), 1)  # não enviou de novo

    def test_unknown_edition_raises(self):
        resend = FakeResendClient()
        with self.assertRaises(EditionNotFoundError):
            approve_and_send(self.conn, 9999, resend)

    def test_per_recipient_failures_are_recorded_without_crashing(self):
        resend = FakeResendClient(fail_for={"a@example.com"})
        result = approve_and_send(self.conn, self.edition.id, resend)

        self.assertEqual(result.status, "sent")
        self.assertEqual(result.send_failures, ["a@example.com"])


if __name__ == "__main__":
    unittest.main()
