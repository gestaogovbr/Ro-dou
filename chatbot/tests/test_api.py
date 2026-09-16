from __future__ import annotations

from datetime import date, datetime

from fastapi.testclient import TestClient

import rodou_chatbot.search as search_module
from rodou_chatbot.app import create_app
from rodou_chatbot.config import (
    AIConfig,
    AppConfig,
    AuthConfig,
    ChatConfig,
    SearchConfig,
)
from rodou_chatbot.models import PublicationResult, SearchIntent, SearchResult
from rodou_chatbot.search import PublicationSearchService


class FakeProvider:
    name = "fake"
    model = "fake"

    def parse_search_intent(self, message: str, context: dict) -> SearchIntent:
        return SearchIntent(terms=[context.get("user_name") or "dengue"])


class FakeSearch:
    def __init__(self) -> None:
        self.intents: list[SearchIntent] = []

    def search(self, intent: SearchIntent) -> SearchResult:
        self.intents.append(intent)
        return SearchResult(
            total=1,
            results=[PublicationResult(id="1", title="Resultado")],
        )


def test_chat_and_search_api_share_search_service() -> None:
    search = FakeSearch()
    app = create_app(
        config=AppConfig(chat=ChatConfig(ai=AIConfig())),
        provider=FakeProvider(),
        search_service=search,  # type: ignore[arg-type]
    )
    client = TestClient(app)

    chat_response = client.post(
        "/api/v1/chat",
        json={"message": "publicações de Eduardo"},
        headers={"X-User-Name": "Eduardo Lauer"},
    )
    search_response = client.post(
        "/api/v1/publications/search",
        json={"terms": ["dengue"], "organizations": ["Ministério da Saúde"]},
    )

    assert chat_response.status_code == 200
    assert chat_response.json()["intent"]["terms"] == ["dengue"]
    assert search_response.status_code == 200
    assert len(search.intents) == 2
    assert search.intents[1].organizations == ["Ministério da Saúde"]


def test_api_authentication_when_token_is_configured() -> None:
    app = create_app(
        config=AppConfig(auth=AuthConfig(api_token="expected-token")),
        provider=FakeProvider(),
        search_service=FakeSearch(),  # type: ignore[arg-type]
    )
    client = TestClient(app)

    unauthorized = client.post(
        "/api/v1/publications/search",
        json={"terms": ["dengue"]},
    )
    authorized = client.post(
        "/api/v1/publications/search",
        json={"terms": ["dengue"]},
        headers={"Authorization": "Bearer expected-token"},
    )

    assert unauthorized.status_code == 401
    assert authorized.status_code == 200


def test_authenticated_identity_is_forwarded_to_chat_context() -> None:
    app = create_app(
        config=AppConfig(auth=AuthConfig(api_token="expected-token")),
        provider=FakeProvider(),
        search_service=FakeSearch(),  # type: ignore[arg-type]
    )
    client = TestClient(app)

    response = client.post(
        "/api/v1/chat",
        json={"message": "publicações do meu nome"},
        headers={
            "Authorization": "Bearer expected-token",
            "X-User-Name": "Eduardo Lauer",
        },
    )

    assert response.status_code == 200
    assert response.json()["intent"]["terms"] == ["Eduardo Lauer"]


def test_structured_api_reports_effective_current_date_when_empty(monkeypatch) -> None:
    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 9, 16, tzinfo=tz)

    monkeypatch.setattr(search_module, "datetime", FrozenDatetime)
    search = PublicationSearchService(SearchConfig(), max_results=20)
    captured: list[SearchIntent] = []

    def fake_search(intent: SearchIntent) -> SearchResult:
        captured.append(intent)
        return SearchResult()

    search._search_postgres = fake_search  # type: ignore[method-assign]
    app = create_app(
        config=AppConfig(chat=ChatConfig(ai=AIConfig())),
        provider=FakeProvider(),
        search_service=search,
    )

    response = TestClient(app).post(
        "/api/v1/publications/search",
        json={
            "terms": ["dengue"],
            "date_from": "2020-01-01",
            "date_to": "2020-01-31",
        },
    )

    assert response.status_code == 200
    assert captured[0].date_from == date(2026, 9, 16)
    assert captured[0].date_to == date(2026, 9, 16)
    assert response.json()["effective_date"] == "2026-09-16"
    assert response.json()["message"] == (
        "Não há publicações no dia de hoje para os filtros informados."
    )
