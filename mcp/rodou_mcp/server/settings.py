"""Configuration for the Ro-DOU MCP server."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven settings kept inside the MCP server boundary."""

    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    host: str = Field(default="0.0.0.0", alias="RO_DOU_MCP_HOST")
    port: int = Field(default=8100, alias="RO_DOU_MCP_PORT")
    transport: Literal["stdio", "sse"] = Field(default="sse", alias="RO_DOU_MCP_TRANSPORT")

    enable_opensearch: bool = Field(default=False, alias="ENABLE_OPENSEARCH")
    opensearch_host: str = Field(default="http://localhost:9200", alias="OPENSEARCH_HOST")
    opensearch_user: str | None = Field(default=None, alias="OPENSEARCH_USER")
    opensearch_pass: str | None = Field(default=None, alias="OPENSEARCH_PASS")
    opensearch_index: str = Field(default="dou", alias="OPENSEARCH_INDEX")
    opensearch_use_ssl: bool = Field(default=False, alias="OPENSEARCH_SSL")
    opensearch_verify_certs: bool = Field(default=False, alias="OPENSEARCH_VERIFY_CERTS")

    inlabs_postgres_dsn: str = Field(
        default="postgresql://airflow:airflow@localhost:5432/inlabs",
        alias="INLABS_POSTGRES_DSN",
    )
    inlabs_table: str = Field(default="dou_inlabs.article_raw", alias="INLABS_TABLE")
    day_context_publication_limit: int = Field(
        default=1000,
        alias="RO_DOU_DAY_CONTEXT_PUBLICATION_LIMIT",
    )
    ai_context_body_chars: int = Field(default=300, alias="RO_DOU_AI_CONTEXT_BODY_CHARS")

    ai_provider: Literal["openai", "gemini", "claude", "azure"] | None = Field(
        default=None,
        alias="RO_DOU_AI_PROVIDER",
    )
    ai_model: str | None = Field(default=None, alias="RO_DOU_AI_MODEL")
    ai_api_key: str | None = Field(default=None, alias="RO_DOU_AI_API_KEY")
    ai_temperature: float = Field(default=0.2, alias="RO_DOU_AI_TEMPERATURE")
    ai_max_tokens: int = Field(default=700, alias="RO_DOU_AI_MAX_TOKENS")
    azure_openai_endpoint: str | None = Field(default=None, alias="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_version: str | None = Field(default=None, alias="AZURE_OPENAI_API_VERSION")

    @field_validator("ai_provider", mode="before")
    @classmethod
    def empty_ai_provider_is_none(cls, value: str | None) -> str | None:
        """Treat empty Compose substitutions as an unconfigured AI provider."""
        if value == "":
            return None
        return value

    @field_validator("inlabs_table")
    @classmethod
    def validate_inlabs_table(cls, value: str) -> str:
        """Accept only simple SQL identifiers such as schema.table."""
        parts = value.split(".")
        if not parts or any(not part.isidentifier() for part in parts):
            raise ValueError("INLABS_TABLE must be a dot-separated SQL identifier")
        return value
