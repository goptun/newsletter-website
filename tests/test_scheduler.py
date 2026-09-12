"""Testes de app.scheduler.run_daily_generation — verifica que a
notificação de "draft pronto" dispara após uma geração bem-sucedida (ver
tasks.md 5.6) e não dispara quando a edição fica 'incomplete'."""

from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch

from app.config.settings import settings
from app.storage.db import SCHEMA, get_connection
from app.storage.editions import Edition


class TestRunDailyGeneration(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        conn = get_connection(self.db_path)
        conn.executescript(SCHEMA)
        conn.close()

        self._original_db_path = settings.db_path
        settings.db_path = self.db_path

    def tearDown(self):
        settings.db_path = self._original_db_path
        os.remove(self.db_path)

    def test_notifies_when_generation_produces_a_draft(self):
        draft_edition = Edition(
            id=1,
            edition_date="2026-09-12",
            subject="Assunto",
            body="Corpo",
            status="draft",
            sent_at=None,
            send_failures=None,
        )

        with (
            patch("app.scheduler.dependencies.build_llm_client"),
            patch("app.scheduler.generate_daily_edition", return_value=draft_edition),
            patch("app.scheduler.notify_draft_ready") as notify_mock,
        ):
            from app.scheduler import run_daily_generation

            run_daily_generation()

        notify_mock.assert_called_once_with(draft_edition)

    def test_does_not_notify_when_edition_is_incomplete(self):
        incomplete_edition = Edition(
            id=1,
            edition_date="2026-09-12",
            subject=None,
            body="sem notícia",
            status="incomplete",
            sent_at=None,
            send_failures=None,
        )

        with (
            patch("app.scheduler.dependencies.build_llm_client"),
            patch("app.scheduler.generate_daily_edition", return_value=incomplete_edition),
            patch("app.scheduler.notify_draft_ready") as notify_mock,
        ):
            from app.scheduler import run_daily_generation

            run_daily_generation()

        notify_mock.assert_not_called()


class TestStartScheduler(unittest.TestCase):
    """Requirement: Daily draft generation — a geração dispara sozinha,
    sem gatilho manual (ver tasks.md 6.1: 'job registrado no startup')."""

    def test_job_is_registered_and_schedulable(self):
        from app.scheduler import start_scheduler

        scheduler = start_scheduler(hour=6, minute=0)
        try:
            job = scheduler.get_job("daily_newsletter_generation")
            self.assertIsNotNone(job)
            self.assertTrue(scheduler.running)
        finally:
            scheduler.shutdown(wait=False)


if __name__ == "__main__":
    unittest.main()
