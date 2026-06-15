"""FastAPI backend settings."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BackendSettings(BaseSettings):
    """Environment-driven settings for the chatbot API."""

    model_config = SettingsConfigDict(env_prefix="RO_DOU_", extra="ignore")

    mcp_server_url: str = Field(default="http://localhost:8100/sse")
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])
