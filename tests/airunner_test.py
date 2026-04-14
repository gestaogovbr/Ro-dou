from ai.runner import AIRunner
from ai.provider import AIProvider

import pytest

@pytest.mark.parametrize("value,expected", [
    ("openai", AIProvider.openai),
    ("OpenAI", AIProvider.openai),
    ("OPENAI", AIProvider.openai),
    ("gemini", AIProvider.gemini),
    ("GEMINI", AIProvider.gemini),
    ("Claude", AIProvider.claude),
    ("AZURE", AIProvider.azure),
])
def test_ai_provider_case_insensitive(value, expected):
    assert AIProvider(value) == expected