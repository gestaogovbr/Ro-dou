from __future__ import annotations

import time
from datetime import date, datetime
from uuid import uuid4

import rodou_chatbot.chat as chat_module
from rodou_chatbot.chat import ChatService
from rodou_chatbot.config import AIConfig, ChatConfig
from rodou_chatbot.conversation import ConversationStore
from rodou_chatbot.models import (
    AuthenticatedUser,
    ChatRequest,
    PublicationResult,
    SearchIntent,
    SearchResult,
)
from rodou_chatbot.providers import IntentProviderError


class FakeProvider:
    name = "fake"
    model = "fake-model"

    def __init__(self, intents: list[SearchIntent] | None = None, error=None) -> None:
        self.intents = list(intents or [])
        self.error = error
        self.contexts: list[dict] = []
        self.calls = 0

    def parse_search_intent(self, message: str, context: dict) -> SearchIntent:
        self.calls += 1
        self.contexts.append(context)
        if self.error:
            raise self.error
        return self.intents.pop(0)


class FakeSearchService:
    def __init__(self, results: list[SearchResult]) -> None:
        self.results = list(results)
        self.intents: list[SearchIntent] = []

    def search(self, intent: SearchIntent) -> SearchResult:
        self.intents.append(intent)
        return self.results.pop(0)


def build_service(provider, search, timeout: float = 1) -> ChatService:
    return ChatService(
        config=ChatConfig(ai=AIConfig(timeout=timeout), max_results=20),
        timezone="America/Sao_Paulo",
        provider=provider,
        search_service=search,
        conversation_store=ConversationStore(1800, 100),
    )


def test_my_name_and_today_are_completed_by_backend(monkeypatch) -> None:
    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 9, 16, tzinfo=tz)

    monkeypatch.setattr(chat_module, "datetime", FrozenDatetime)
    provider = FakeProvider([SearchIntent(terms=["nome informado pela LLM"])])
    search = FakeSearchService([SearchResult()])
    service = build_service(provider, search)

    response = service.answer(
        ChatRequest(message="Quais publicações referentes ao meu nome constam hoje?"),
        AuthenticatedUser(name="Eduardo Lauer"),
    )

    assert response.intent is not None
    assert response.intent.terms == ["Eduardo Lauer"]
    assert response.intent.date_from == date(2026, 9, 16)
    assert response.intent.date_to == date(2026, 9, 16)


def test_organization_filter_does_not_limit_topic_to_article_category() -> None:
    provider = FakeProvider(
        [
            SearchIntent(
                terms=["dengue"],
                organizations=["Ministério da Saúde"],
                field="artcategory",
            )
        ]
    )
    search = FakeSearchService([SearchResult()])
    service = build_service(provider, search)

    response = service.answer(
        ChatRequest(message="Ministério da Saúde sobre dengue"),
        AuthenticatedUser(),
    )

    assert response.intent is not None
    assert response.intent.organizations == ["Ministério da Saúde"]
    assert response.intent.terms == ["dengue"]
    assert response.intent.field is None


def test_my_name_without_authenticated_context_requests_clarification() -> None:
    provider = FakeProvider([SearchIntent(terms=["unused"])])
    service = build_service(provider, FakeSearchService([]))

    response = service.answer(
        ChatRequest(message="Há publicação no meu nome hoje?"),
        AuthenticatedUser(),
    )

    assert response.needs_clarification is True
    assert provider.calls == 0


def test_absence_and_multiple_results_have_deterministic_answers() -> None:
    intent = SearchIntent(terms=["dengue"])
    provider = FakeProvider([intent, intent])
    search = FakeSearchService(
        [
            SearchResult(),
            SearchResult(
                total=2,
                results=[
                    PublicationResult(
                        id="1",
                        title="Portaria A",
                        organization="Ministério da Saúde",
                        section="DO1",
                        publication_date=date(2026, 9, 16),
                        content="Resumo oficial.",
                        content_type="ementa",
                    ),
                    PublicationResult(
                        id="2",
                        title="Portaria B",
                        content="Trecho com dengue.",
                    ),
                ],
            ),
        ]
    )
    service = build_service(provider, search)

    empty = service.answer(ChatRequest(message="dengue"), AuthenticatedUser())
    multiple = service.answer(ChatRequest(message="dengue"), AuthenticatedUser())

    assert "Não há publicações no dia de hoje" in empty.answer
    assert "Encontrei 2" in multiple.answer
    assert "Portaria A" in multiple.answer
    assert (
        "1. Portaria A\n"
        "   Órgão: Ministério da Saúde • Seção: DO1 • Data: 16/09/2026"
    ) in multiple.answer
    assert "Ementa: Resumo oficial." in multiple.answer
    assert "Recorte: Trecho com dengue." in multiple.answer


def test_provider_error_returns_safe_clarification() -> None:
    provider = FakeProvider(error=IntentProviderError("secret provider detail"))
    service = build_service(provider, FakeSearchService([]))

    response = service.answer(ChatRequest(message="algo"), AuthenticatedUser())

    assert response.needs_clarification is True
    assert "secret provider detail" not in response.answer


def test_limit_notice_is_displayed_before_publications() -> None:
    result = SearchResult(
        total=25,
        results=[PublicationResult(id="1", title="Portaria A")],
        message=(
            "Os resultados ultrapassam o limite de 20 publicações definido na "
            "configuração. Exibindo as primeiras 20 publicações."
        ),
    )

    answer = ChatService._format_answer(result)

    assert "Aviso: Os resultados ultrapassam o limite" in answer
    assert answer.index("Aviso:") < answer.index("1. Portaria A")


def test_provider_timeout_returns_safe_clarification() -> None:
    class SlowProvider(FakeProvider):
        def parse_search_intent(self, message: str, context: dict) -> SearchIntent:
            time.sleep(0.1)
            return SearchIntent(terms=["late"])

    service = build_service(SlowProvider(), FakeSearchService([]), timeout=0.01)

    response = service.answer(ChatRequest(message="algo"), AuthenticatedUser())

    assert response.needs_clarification is True


def test_conversation_continuity_merges_previous_filters(monkeypatch) -> None:
    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 9, 16, tzinfo=tz)

    monkeypatch.setattr(chat_module, "datetime", FrozenDatetime)
    provider = FakeProvider(
        [
            SearchIntent(terms=["transformação digital"]),
            SearchIntent(organizations=["MGI"], context_action="refine"),
        ]
    )
    search = FakeSearchService([SearchResult(), SearchResult()])
    service = build_service(provider, search)

    first = service.answer(
        ChatRequest(message="Transformação digital desta semana"),
        AuthenticatedUser(),
    )
    second = service.answer(
        ChatRequest(
            message="Só do MGI",
            conversation_id=first.conversation_id,
            client_id=first.client_id,
        ),
        AuthenticatedUser(),
    )

    assert second.intent is not None
    assert second.intent.terms == ["transformação digital"]
    assert second.intent.organizations == ["MGI"]
    assert second.intent.date_from == date(2026, 9, 16)
    assert second.intent.date_to == date(2026, 9, 16)
    assert provider.contexts[1]["previous_intent"]["terms"] == [
        "transformação digital"
    ]


def test_short_replacement_query_does_not_inherit_previous_terms() -> None:
    provider = FakeProvider(
        [
            SearchIntent(terms=["dengue"]),
            SearchIntent(organizations=["ANVISA"]),
        ]
    )
    search = FakeSearchService([SearchResult(), SearchResult()])
    service = build_service(provider, search)

    first = service.answer(ChatRequest(message="dengue esta semana"), AuthenticatedUser())
    second = service.answer(
        ChatRequest(
            message="ANVISA ontem",
            conversation_id=first.conversation_id,
            client_id=first.client_id,
        ),
        AuthenticatedUser(),
    )

    assert second.intent is not None
    assert second.intent.terms == []
    assert second.intent.organizations == ["ANVISA"]


def test_request_for_yesterday_is_restricted_to_today(monkeypatch) -> None:
    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 9, 16, tzinfo=tz)

    monkeypatch.setattr(chat_module, "datetime", FrozenDatetime)
    provider = FakeProvider(
        [
            SearchIntent(
                terms=["dengue"],
                date_from=date(2026, 9, 15),
                date_to=date(2026, 9, 15),
            )
        ]
    )
    search = FakeSearchService([SearchResult()])
    service = build_service(provider, search)

    response = service.answer(
        ChatRequest(message="publicações sobre dengue ontem"),
        AuthenticatedUser(),
    )

    assert response.intent is not None
    assert response.intent.date_from == date(2026, 9, 16)
    assert response.intent.date_to == date(2026, 9, 16)
    assert search.intents[0].date_from == date(2026, 9, 16)


def test_refinement_can_explicitly_clear_organization_filter() -> None:
    provider = FakeProvider(
        [
            SearchIntent(terms=["dengue"], organizations=["ANVISA"]),
            SearchIntent(
                context_action="refine",
                clear_filters=["organizations"],
            ),
        ]
    )
    search = FakeSearchService([SearchResult(), SearchResult()])
    service = build_service(provider, search)

    first = service.answer(ChatRequest(message="dengue da ANVISA"), AuthenticatedUser())
    second = service.answer(
        ChatRequest(
            message="agora sem órgão",
            conversation_id=first.conversation_id,
            client_id=first.client_id,
        ),
        AuthenticatedUser(),
    )

    assert second.intent is not None
    assert second.intent.terms == ["dengue"]
    assert second.intent.organizations == []


def test_conversation_cannot_be_reused_by_another_client() -> None:
    provider = FakeProvider([SearchIntent(terms=["dengue"])])
    search = FakeSearchService([SearchResult()])
    service = build_service(provider, search)
    first = service.answer(ChatRequest(message="dengue"), AuthenticatedUser())

    response = service.answer(
        ChatRequest(
            message="Só da ANVISA",
            conversation_id=first.conversation_id,
        ),
        AuthenticatedUser(),
    )

    assert response.needs_clarification is True
    assert response.conversation_id != first.conversation_id
    assert provider.calls == 1


def test_authenticated_name_still_requires_original_client_capability() -> None:
    provider = FakeProvider([SearchIntent(terms=["Eduardo Lauer"])])
    search = FakeSearchService([SearchResult()])
    service = build_service(provider, search)
    first = service.answer(
        ChatRequest(message="Eduardo Lauer", client_id=uuid4()),
        AuthenticatedUser(name="Eduardo Lauer"),
    )

    response = service.answer(
        ChatRequest(
            message="Só de ontem",
            conversation_id=first.conversation_id,
            client_id=uuid4(),
        ),
        AuthenticatedUser(name="Eduardo Lauer"),
    )

    assert response.needs_clarification is True
    assert response.conversation_id != first.conversation_id


def test_search_failure_returns_controlled_response() -> None:
    class FailingSearch(FakeSearchService):
        def search(self, intent: SearchIntent) -> SearchResult:
            raise TimeoutError("database detail")

    service = build_service(
        FakeProvider([SearchIntent(terms=["dengue"])]),
        FailingSearch([]),
    )

    response = service.answer(ChatRequest(message="dengue"), AuthenticatedUser())

    assert response.needs_clarification is True
    assert "database detail" not in response.answer
