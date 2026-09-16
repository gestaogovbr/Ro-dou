from __future__ import annotations

import pytest

from rodou_chatbot.config import load_config


def test_environment_overrides_yaml_and_supplies_secrets(tmp_path, monkeypatch) -> None:
    config_file = tmp_path / "chatbot.yaml"
    config_file.write_text(
        """
chat:
  ai:
    provider: openai
    model: yaml-model
search:
  source: postgres
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("RO_DOU_CHAT_AI_PROVIDER", "anthropic")
    monkeypatch.setenv("RO_DOU_CHAT_AI_MODEL", "environment-model")
    monkeypatch.setenv("RO_DOU_CHAT_AI_API_KEY", "secret-key")

    config = load_config(config_file)

    assert config.chat.ai.provider == "anthropic"
    assert config.chat.ai.model == "environment-model"
    assert config.chat.ai.api_key is not None
    assert config.chat.ai.api_key.get_secret_value() == "secret-key"


def test_yaml_secrets_are_rejected(tmp_path) -> None:
    config_file = tmp_path / "chatbot.yaml"
    config_file.write_text(
        """
chat:
  ai:
    api_key: do-not-store-here
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="environment"):
        load_config(config_file)

