from __future__ import annotations

import pytest

from rodou_chatbot.config import AIConfig
from rodou_chatbot.providers import (
    AnthropicProvider,
    GeminiProvider,
    IntentProviderError,
    JSONIntentProvider,
    OpenAIProvider,
    create_provider,
)


class StubJSONProvider(JSONIntentProvider):
    name = "stub"

    def __init__(self, raw: str) -> None:
        super().__init__(AIConfig(api_key="test-key"))
        self.raw = raw
        self.prompt = ""

    def _invoke(self, prompt: str) -> str:
        self.prompt = prompt
        return self.raw


def test_provider_parses_valid_structured_intent() -> None:
    provider = StubJSONProvider(
        '{"intent":"search_publications","terms":["dengue"],'
        '"organizations":["Ministério da Saúde"],"limit":5}'
    )

    intent = provider.parse_search_intent(
        "Mostre dengue no Ministério da Saúde",
        {"today": "2026-09-16", "user_name": None, "previous_intent": None},
    )

    assert intent.terms == ["dengue"]
    assert intent.organizations == ["Ministério da Saúde"]
    assert "postgres" not in provider.prompt.lower()
    assert "opensearch" not in provider.prompt.lower()


def test_provider_rejects_unstructured_or_extra_arguments() -> None:
    provider = StubJSONProvider('{"intent":"search_publications","sql":"SELECT 1"}')
    with pytest.raises(IntentProviderError):
        provider.parse_search_intent("teste", {"today": "2026-09-16"})


@pytest.mark.parametrize(
    ("name", "provider_type"),
    [
        ("openai", OpenAIProvider),
        ("anthropic", AnthropicProvider),
        ("gemini", GeminiProvider),
    ],
)
def test_provider_can_be_changed_without_chat_logic(name: str, provider_type: type) -> None:
    assert isinstance(create_provider(AIConfig(provider=name)), provider_type)

