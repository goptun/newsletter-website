"""Eventos históricos reais do dia, via API "On this day" da Wikipedia — base
factual da "Curiosidade do dia". Antes o LLM escolhia o fato de memória e
errava datas com confiança (ex.: Apple II em 21/09/1977, TCP/IP em
21/09/1978); agora o evento e o ano vêm da Wikipedia e o LLM só escolhe e
reescreve (ver specs/newsletter/content-generation/spec.md, Requirement:
Real, sourced news only)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import date

import httpx

ONTHISDAY_URL = "https://api.wikimedia.org/feed/v1/wikipedia/en/onthisday/all/{month:02d}/{day:02d}"
# A política da Wikimedia exige um User-Agent identificável.
_USER_AGENT = "newsletter-website/1.0 (https://matheusramos.dev)"
_ATTEMPTS = 3


@dataclass(frozen=True)
class HistoricalEvent:
    year: int
    text: str


def fetch_events(day: date, timeout: float = 15.0) -> list[HistoricalEvent]:
    """Eventos do dia/mês em qualquer ano ("events" + os "selected", curados
    pela Wikipedia), sem repetição. Levanta a última exceção se a API falhar
    nas tentativas — quem chama decide o que fazer (ver pipeline)."""
    url = ONTHISDAY_URL.format(month=day.month, day=day.day)
    last_exc: Exception | None = None
    for attempt in range(_ATTEMPTS):
        try:
            response = httpx.get(
                url, headers={"User-Agent": _USER_AGENT}, timeout=timeout, follow_redirects=True
            )
            response.raise_for_status()
            payload = response.json()
            break
        except Exception as exc:
            last_exc = exc
            if attempt < _ATTEMPTS - 1:
                time.sleep(1.5 * (attempt + 1))
    else:
        raise RuntimeError(f"Wikipedia On This Day indisponível: {last_exc}") from last_exc

    events: list[HistoricalEvent] = []
    seen: set[tuple[int, str]] = set()
    for raw in [*payload.get("events", []), *payload.get("selected", [])]:
        year, text = raw.get("year"), (raw.get("text") or "").strip()
        if not isinstance(year, int) or not text:
            continue
        key = (year, text[:60])
        if key in seen:
            continue
        seen.add(key)
        events.append(HistoricalEvent(year=year, text=text))
    return events
