"""Typed response models for Ro-DOU MCP tools."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Publication(BaseModel):
    """A processed DOU publication returned from search."""

    id: str
    id_materia: str | None = None
    title: str | None = None
    subtitle: str | None = None
    pubname: str | None = None
    pubdate: str | None = None
    category: str | None = None
    article_type: str | None = None
    body: str | None = None
    url: str | None = None
    score: float | None = None


class SearchResult(BaseModel):
    """Search result returned by the MCP server."""

    query: str
    total: int = 0
    items: list[Publication] = Field(default_factory=list)


class PublicationContext(BaseModel):
    """Database-loaded context passed to the AI provider."""

    context_id: str
    source: str = "postgres"
    question: str
    context_date: str | None = None
    total_publications: int = 0
    publications: list[Publication] = Field(default_factory=list)
