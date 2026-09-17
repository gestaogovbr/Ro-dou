"""YAML configuration with environment overrides and environment-only secrets."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


class AIConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: Literal["openai", "anthropic", "gemini"] = "openai"
    model: str = "gpt-4.1-mini"
    temperature: float = Field(default=0, ge=0, le=2)
    timeout: float = Field(default=30, gt=0, le=120)
    max_prompt_chars: int = Field(default=12000, ge=1000, le=50000)
    api_key: SecretStr | None = None


class ChatConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    ai: AIConfig = Field(default_factory=AIConfig)
    max_results: int = Field(default=20, ge=1, le=100)
    max_concurrent_ai_calls: int = Field(default=8, ge=1, le=100)
    conversation_ttl_seconds: int = Field(default=1800, ge=60, le=86400)
    max_conversations: int = Field(default=1000, ge=1, le=10000)


class SearchConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: Literal["postgres", "opensearch"] = "postgres"
    postgres_dsn: str = "postgresql://airflow:airflow@localhost:5432/inlabs"
    postgres_table: str = "dou_inlabs.article_raw"
    opensearch_host: str = "http://localhost:9200"
    opensearch_index: str = "dou"
    opensearch_user: str | None = None
    opensearch_password: SecretStr | None = None
    timeout: float = Field(default=15, gt=0, le=120)

    @field_validator("postgres_table")
    @classmethod
    def validate_table(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)?", value):
            raise ValueError("postgres_table must be a simple schema.table identifier")
        return value


class AuthConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    api_token: SecretStr | None = None


class AuditLogConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    directory: str | None = None
    max_bytes: int = Field(default=10_000_000, ge=10_000)
    backup_count: int = Field(default=5, ge=1, le=100)


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chat: ChatConfig = Field(default_factory=ChatConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    audit_log: AuditLogConfig = Field(default_factory=AuditLogConfig)
    timezone: str = "America/Sao_Paulo"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5174"])


ENV_OVERRIDES: dict[str, tuple[str, ...]] = {
    "RO_DOU_CHAT_ENABLED": ("chat", "enabled"),
    "RO_DOU_CHAT_AI_PROVIDER": ("chat", "ai", "provider"),
    "RO_DOU_CHAT_AI_MODEL": ("chat", "ai", "model"),
    "RO_DOU_CHAT_AI_TEMPERATURE": ("chat", "ai", "temperature"),
    "RO_DOU_CHAT_AI_TIMEOUT": ("chat", "ai", "timeout"),
    "RO_DOU_CHAT_MAX_RESULTS": ("chat", "max_results"),
    "RO_DOU_CHAT_MAX_CONCURRENT_AI_CALLS": ("chat", "max_concurrent_ai_calls"),
    "RO_DOU_CHAT_SEARCH_SOURCE": ("search", "source"),
    "INLABS_POSTGRES_DSN": ("search", "postgres_dsn"),
    "INLABS_TABLE": ("search", "postgres_table"),
    "OPENSEARCH_HOST": ("search", "opensearch_host"),
    "OPENSEARCH_INDEX": ("search", "opensearch_index"),
    "OPENSEARCH_USER": ("search", "opensearch_user"),
    "RO_DOU_CHAT_SEARCH_TIMEOUT": ("search", "timeout"),
    "RO_DOU_CHAT_LOG_ENABLED": ("audit_log", "enabled"),
    "RO_DOU_CHAT_LOG_DIR": ("audit_log", "directory"),
    "RO_DOU_CHAT_LOG_MAX_BYTES": ("audit_log", "max_bytes"),
    "RO_DOU_CHAT_LOG_BACKUP_COUNT": ("audit_log", "backup_count"),
    "RO_DOU_TIMEZONE": ("timezone",),
}


def _set_nested(target: dict[str, Any], path: tuple[str, ...], value: Any) -> None:
    current = target
    for part in path[:-1]:
        current = current.setdefault(part, {})
    current[path[-1]] = value


def load_config(path: str | Path | None = None) -> AppConfig:
    """Load non-secret YAML settings, then apply environment overrides."""
    config_path = Path(path or os.getenv("RO_DOU_CHAT_CONFIG", "chatbot/config.yaml"))
    raw: dict[str, Any] = {}
    if config_path.exists():
        loaded = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        if not isinstance(loaded, dict):
            raise ValueError("chatbot configuration must be a YAML object")
        raw = loaded
    if raw.get("chat", {}).get("ai", {}).get("api_key"):
        raise ValueError("AI API keys must be provided through the environment")
    if raw.get("auth", {}).get("api_token"):
        raise ValueError("API tokens must be provided through the environment")
    if raw.get("search", {}).get("opensearch_password"):
        raise ValueError("OpenSearch passwords must be provided through the environment")

    for environment_name, config_path_parts in ENV_OVERRIDES.items():
        value = os.getenv(environment_name)
        if value not in (None, ""):
            _set_nested(raw, config_path_parts, value)

    _set_nested(raw, ("chat", "ai", "api_key"), os.getenv("RO_DOU_CHAT_AI_API_KEY"))
    _set_nested(raw, ("auth", "api_token"), os.getenv("RO_DOU_CHAT_API_TOKEN"))
    _set_nested(
        raw,
        ("search", "opensearch_password"),
        os.getenv("OPENSEARCH_PASS"),
    )
    return AppConfig.model_validate(raw)
