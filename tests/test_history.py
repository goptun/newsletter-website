"""Testes de app.news.history — eventos reais do dia via Wikipedia (sem rede)."""

from __future__ import annotations

import unittest
from datetime import date
from unittest.mock import MagicMock, patch

from app.news.history import fetch_events

PAYLOAD = {
    "events": [
        {"year": 1995, "text": "Java is released."},
        {"year": 1969, "text": "First ARPANET message."},
        {"text": "sem ano"},
        {"year": 2001, "text": ""},
    ],
    "selected": [{"year": 1995, "text": "Java is released."}, {"year": 1984, "text": "Another event."}],
}


def _response(payload):
    response = MagicMock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


class TestFetchEvents(unittest.TestCase):
    def test_merges_events_and_selected_without_duplicates_or_incomplete_items(self):
        with patch("app.news.history.httpx.get", return_value=_response(PAYLOAD)) as get:
            events = fetch_events(date(2026, 9, 21))

        self.assertEqual([(e.year, e.text) for e in events],
                         [(1995, "Java is released."), (1969, "First ARPANET message."), (1984, "Another event.")])
        self.assertTrue(get.call_args.args[0].endswith("/onthisday/all/09/21"))
        self.assertIn("User-Agent", get.call_args.kwargs["headers"])

    def test_retries_then_succeeds(self):
        with patch("app.news.history.time.sleep"), patch(
            "app.news.history.httpx.get", side_effect=[RuntimeError("boom"), _response(PAYLOAD)]
        ):
            self.assertEqual(len(fetch_events(date(2026, 9, 21))), 3)

    def test_raises_after_all_attempts_fail(self):
        with patch("app.news.history.time.sleep"), patch(
            "app.news.history.httpx.get", side_effect=RuntimeError("boom")
        ) as get:
            with self.assertRaises(RuntimeError):
                fetch_events(date(2026, 9, 21))
        self.assertEqual(get.call_count, 3)


if __name__ == "__main__":
    unittest.main()
