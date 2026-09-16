"""Backend-owned resolution of relative date expressions."""

from __future__ import annotations

import re
import unicodedata
from datetime import date, timedelta


def _normalize(value: str) -> str:
    return "".join(
        character
        for character in unicodedata.normalize("NFKD", value.lower())
        if not unicodedata.combining(character)
    )


def resolve_relative_dates(
    message: str,
    today: date,
) -> tuple[date, date] | None:
    """Resolve supported Portuguese relative periods without trusting the LLM."""
    normalized = _normalize(message)
    if re.search(r"\bhoje\b", normalized):
        return today, today
    if re.search(r"\bontem\b", normalized):
        yesterday = today - timedelta(days=1)
        return yesterday, yesterday
    if re.search(r"\b(?:esta|nesta|nessa|desta|dessa)\s+semana\b", normalized):
        return today - timedelta(days=today.weekday()), today
    match = re.search(r"\bultimos?\s+(\d{1,3})\s+dias?\b", normalized)
    if match:
        days = min(max(int(match.group(1)), 1), 366)
        return today - timedelta(days=days - 1), today
    if re.search(r"\b(?:este|neste|nesse|deste|desse)\s+mes\b", normalized):
        return today.replace(day=1), today
    return None
