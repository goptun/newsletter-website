"""Testes de app.delivery.pipeline — ver specs/newsletter/delivery/spec.md."""

from __future__ import annotations

import unittest

from app.delivery.pipeline import (
    AlreadySentError,
    EditionNotFoundError,
    InvalidEditionStateError,
    approve_and_send,
    reject_draft,
)
from app.storage.db import SCHEMA, get_connection
from app.storage.editions import create_draft, create_incomplete
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

    def test_incomplete_edition_cannot_be_approved_and_sent(self):
        # Regressão: antes desse guard, approve_and_send() chamava
        # editions_store.approve() (que só atualiza linhas com
        # status='draft', virando um no-op silencioso em qualquer outro
        # status) e seguia pro envio mesmo assim — uma edição 'incomplete'
        # (sem notícia real/validação falhou) seria enviada de qualquer jeito.
        incomplete = create_incomplete(self.conn, "2026-09-13", reason="sem notícia real")
        resend = FakeResendClient()

        with self.assertRaises(InvalidEditionStateError):
            approve_and_send(self.conn, incomplete.id, resend)

        self.assertEqual(len(resend.sent), 0)


class TestRejectDraft(unittest.TestCase):
    def setUp(self):
        self.conn = get_connection(":memory:")
        self.conn.executescript(SCHEMA)
        self.edition = create_draft(self.conn, "2026-09-12", "Assunto", "Corpo da edição")

    def tearDown(self):
        self.conn.close()

    def test_rejecting_a_draft_marks_it_rejected(self):
        result = reject_draft(self.conn, self.edition.id)
        self.assertEqual(result.status, "rejected")

    def test_rejected_draft_no_longer_shows_as_pending(self):
        from app.storage.editions import get_latest_pending

        reject_draft(self.conn, self.edition.id)
        self.assertIsNone(get_latest_pending(self.conn))

    def test_rejected_draft_can_never_be_sent(self):
        reject_draft(self.conn, self.edition.id)
        resend = FakeResendClient()

        with self.assertRaises(InvalidEditionStateError):
            approve_and_send(self.conn, self.edition.id, resend)

        self.assertEqual(len(resend.sent), 0)

    def test_cannot_reject_an_already_sent_edition(self):
        approve_and_send(self.conn, self.edition.id, FakeResendClient())

        with self.assertRaises(AlreadySentError):
            reject_draft(self.conn, self.edition.id)

    def test_unknown_edition_raises(self):
        with self.assertRaises(EditionNotFoundError):
            reject_draft(self.conn, 9999)


if __name__ == "__main__":
    unittest.main()
