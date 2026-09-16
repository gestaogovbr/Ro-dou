"""Validated contracts shared by chat, providers and publication search."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


StrictText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
SearchField = Literal[
    "artcategory",
    "ementa",
    "texto",
    "titulo",
    "subtitulo",
    "identifica",
    "name",
    "arttype",
    "assina",
]
ClearableFilter = Literal[
    "terms",
    "excluded_terms",
    "organizations",
    "sections",
    "field",
    "dates",
]


class SearchIntent(BaseModel):
    """The only contract accepted from an LLM provider."""

    model_config = ConfigDict(extra="forbid")

    intent: Literal["search_publications"] = "search_publications"
    terms: list[StrictText] = Field(default_factory=list, max_length=10)
    excluded_terms: list[StrictText] = Field(default_factory=list, max_length=10)
    organizations: list[StrictText] = Field(default_factory=list, max_length=10)
    sections: list[StrictText] = Field(default_factory=list, max_length=10)
    field: SearchField | None = None
    exact_search: bool = False
    context_action: Literal["replace", "refine"] = "replace"
    clear_filters: list[ClearableFilter] = Field(default_factory=list, max_length=6)
    date_from: date | None = None
    date_to: date | None = None
    limit: int = Field(default=20, ge=1, le=100)

    @model_validator(mode="after")
    def validate_date_range(self) -> "SearchIntent":
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from must not be after date_to")
        return self


class PublicationSearchRequest(BaseModel):
    """Reusable REST input for structured publication searches."""

    model_config = ConfigDict(extra="forbid")

    terms: list[StrictText] = Field(default_factory=list, max_length=10)
    excluded_terms: list[StrictText] = Field(default_factory=list, max_length=10)
    organizations: list[StrictText] = Field(default_factory=list, max_length=10)
    sections: list[StrictText] = Field(default_factory=list, max_length=10)
    field: SearchField | None = None
    exact_search: bool = False
    date_from: date | None = None
    date_to: date | None = None
    limit: int = Field(default=20, ge=1, le=100)

    @model_validator(mode="after")
    def validate_date_range(self) -> "PublicationSearchRequest":
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from must not be after date_to")
        return self

    def to_intent(self) -> SearchIntent:
        return SearchIntent.model_validate(
            {"intent": "search_publications", **self.model_dump()}
        )


class PublicationResult(BaseModel):
    id: str
    title: str | None = None
    organization: str | None = None
    section: str | None = None
    publication_date: date | None = None
    content: str = ""
    content_type: Literal["ementa", "excerpt"] = "excerpt"
    url: str | None = None


class SearchResult(BaseModel):
    total: int = 0
    results: list[PublicationResult] = Field(default_factory=list)
    effective_date: date | None = None
    message: str | None = None


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=4000)
    conversation_id: UUID | None = None
    client_id: UUID | None = None


class ChatResponse(BaseModel):
    conversation_id: UUID
    client_id: UUID
    answer: str
    intent: SearchIntent | None = None
    search_result: SearchResult | None = None
    needs_clarification: bool = False


class AuthenticatedUser(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
