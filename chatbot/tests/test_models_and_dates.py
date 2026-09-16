from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from rodou_chatbot.dates import resolve_relative_dates
from rodou_chatbot.models import PublicationSearchRequest, SearchIntent


def test_search_intent_rejects_unknown_fields_and_unsafe_column() -> None:
    with pytest.raises(ValidationError):
        SearchIntent.model_validate(
            {"terms": ["dengue"], "sql": "DROP TABLE article_raw"}
        )
    with pytest.raises(ValidationError):
        SearchIntent.model_validate({"terms": ["dengue"], "field": "password"})


def test_search_intent_rejects_inverted_dates_and_excessive_limit() -> None:
    with pytest.raises(ValidationError):
        SearchIntent(
            terms=["dengue"],
            date_from=date(2026, 9, 17),
            date_to=date(2026, 9, 16),
        )
    with pytest.raises(ValidationError):
        PublicationSearchRequest(terms=["dengue"], limit=101)


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("publicações de hoje", (date(2026, 9, 16), date(2026, 9, 16))),
        ("publicações de ontem", (date(2026, 9, 15), date(2026, 9, 15))),
        ("nesta semana", (date(2026, 9, 14), date(2026, 9, 16))),
        ("publicações desta semana", (date(2026, 9, 14), date(2026, 9, 16))),
        ("últimos 7 dias", (date(2026, 9, 10), date(2026, 9, 16))),
        ("neste mês", (date(2026, 9, 1), date(2026, 9, 16))),
        ("atos deste mês", (date(2026, 9, 1), date(2026, 9, 16))),
    ],
)
def test_relative_dates_are_resolved_by_backend(message: str, expected: tuple) -> None:
    assert resolve_relative_dates(message, date(2026, 9, 16)) == expected
