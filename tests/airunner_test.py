from unittest.mock import patch

import pytest
from ai.provider import AIProvider
from ai.runner import AIRunner

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


def test_ai_provider_invalid_raises():
    with pytest.raises(ValueError):
        AIProvider("not_a_real_provider_name_xyz")


def test_run_raises_when_api_key_empty():
    with pytest.raises(RuntimeError, match="API_KEY"):
        AIRunner.run(
            provider=AIProvider.openai,
            api_key="",
            model="gpt-4o-mini",
            input_text="hello",
        )


@patch.object(AIRunner, "_run_openai", return_value="openai-out")
def test_run_dispatches_to_openai(mock_openai):
    out = AIRunner.run(
        provider=AIProvider.openai,
        api_key="sk-test",
        model="gpt-4o-mini",
        input_text="user text",
        system_prompt="system",
        max_tokens=500,
        temperature=0.3,
    )
    assert out == "openai-out"
    mock_openai.assert_called_once_with(
        "sk-test",
        "gpt-4o-mini",
        "user text",
        "system",
        500,
        0.3,
        60,
    )


@patch.object(AIRunner, "_run_gemini", return_value="gemini-out")
def test_run_dispatches_to_gemini(mock_gemini):
    out = AIRunner.run(
        provider=AIProvider.gemini,
        api_key="g-key",
        model="gemini-1.5-flash",
        input_text="prompt",
        system_prompt="sys",
        max_tokens=100,
        temperature=0.1,
    )
    assert out == "gemini-out"
    mock_gemini.assert_called_once_with(
        "g-key", "gemini-1.5-flash", "prompt", "sys", 100, 0.1
    )


@patch.object(AIRunner, "_run_claude", return_value="claude-out")
def test_run_dispatches_to_claude(mock_claude):
    out = AIRunner.run(
        provider=AIProvider.claude,
        api_key="c-key",
        model="claude-3-5-sonnet-20241022",
        input_text="hi",
        system_prompt="s",
        max_tokens=200,
        temperature=0.5,
    )
    assert out == "claude-out"
    mock_claude.assert_called_once_with(
        "c-key", "claude-3-5-sonnet-20241022", "hi", "s", 200, 0.5, 60
    )


@patch.object(AIRunner, "_run_azure", return_value="azure-out")
@patch.object(
    AIProvider,
    "get_azure_config",
    return_value={
        "endpoint": "https://example.openai.azure.com",
        "api_version": "2024-02-01",
        "deployment": "gpt-4",
    },
)
def test_run_dispatches_to_azure(mock_azure_config, mock_azure_run):
    out = AIRunner.run(
        provider=AIProvider.azure,
        api_key="azure-key",
        model="ignored-by-runner",
        input_text="input",
        system_prompt="sys",
        max_tokens=50,
        temperature=0.2,
    )
    assert out == "azure-out"
    mock_azure_run.assert_called_once_with(
        "azure-key",
        "https://example.openai.azure.com",
        "2024-02-01",
        "gpt-4",
        "input",
        "sys",
        50,
        0.2,
        60,
    )
