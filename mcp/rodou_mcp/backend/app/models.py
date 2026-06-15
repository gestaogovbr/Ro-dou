"""Typed FastAPI request and response models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """A user message submitted by the chatbot page."""

    message: str = Field(min_length=1, max_length=4000)
    date_from: str | None = None
    date_to: str | None = None
    pubname: list[str] | None = None
    size: int = Field(default=5, ge=1, le=20)


class ChatResponse(BaseModel):
    """Chatbot answer plus source publications."""

    answer: str
    sources: list[dict[str, Any]] = Field(default_factory=list)
    context_source: str | None = None
    context_id: str | None = None
    fresh_context: bool | None = None
    context_date: str | None = None
    total_publications: int | None = None
    loaded_publications: int | None = None
