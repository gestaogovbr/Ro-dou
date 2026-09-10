from types import SimpleNamespace
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


@patch.object(AIRunner, "_run_openai", return_value=("openai-out", "stop"))
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
    assert out == ("openai-out", "stop")
    mock_openai.assert_called_once_with(
        "sk-test",
        "gpt-4o-mini",
        "user text",
        "system",
        500,
        0.3,
        60,
    )


@patch.object(AIRunner, "_run_gemini", return_value=("gemini-out", "stop"))
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
    assert out == ("gemini-out", "stop")
    mock_gemini.assert_called_once_with(
        "g-key", "gemini-1.5-flash", "prompt", "sys", 100, 0.1
    )


@patch.object(AIRunner, "_run_claude", return_value=("claude-out", "stop"))
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
    assert out == ("claude-out", "stop")
    mock_claude.assert_called_once_with(
        "c-key", "claude-3-5-sonnet-20241022", "hi", "s", 200, 0.5, 60
    )


@patch.object(AIRunner, "_run_azure", return_value=("azure-out", "stop"))
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
    assert out == ("azure-out", "stop")
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


@pytest.mark.parametrize(
    "reason,expected",
    [
        ("length", "length"),
        ("max_tokens", "length"),
        ("stop", "stop"),
        (SimpleNamespace(name="MAX_TOKENS"), "length"),
        (None, None),
    ],
)
def test_normalize_finish_reason(reason, expected):
    assert AIRunner._normalize_finish_reason(reason) == expected


@patch("google.genai.Client")
def test_run_gemini_returns_normalized_finish_reason(mock_client):
    response = SimpleNamespace(
        text="Resumo parcial",
        candidates=[
            SimpleNamespace(finish_reason=SimpleNamespace(name="MAX_TOKENS"))
        ],
    )
    mock_client.return_value.models.generate_content.return_value = response

    result = AIRunner._run_gemini(
        "api-key", "gemini-2.5-flash", "input", "system", 600, 0.2
    )

    assert result == ("Resumo parcial", "length")


@patch("anthropic.Anthropic")
def test_run_claude_returns_normalized_finish_reason(mock_anthropic):
    response = SimpleNamespace(
        content=[SimpleNamespace(text="Resumo parcial")],
        stop_reason="max_tokens",
    )
    mock_anthropic.return_value.messages.create.return_value = response

    result = AIRunner._run_claude(
        "api-key", "claude-model", "input", "system", 600, 0.2, 60
    )

    assert result == ("Resumo parcial", "length")


@patch("openai.AzureOpenAI")
def test_run_azure_returns_finish_reason(mock_azure_openai):
    choice = SimpleNamespace(
        message=SimpleNamespace(content="Resumo completo"),
        finish_reason="stop",
    )
    response = SimpleNamespace(choices=[choice])
    mock_azure_openai.return_value.chat.completions.create.return_value = response

    result = AIRunner._run_azure(
        "api-key",
        "https://example.openai.azure.com",
        "api-version",
        "deployment",
        "input",
        "system",
        600,
        0.2,
        60,
    )

    assert result == ("Resumo completo", "stop")
