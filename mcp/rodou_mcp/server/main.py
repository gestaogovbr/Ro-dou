"""Ro-DOU MCP server entrypoint."""

from __future__ import annotations

from uuid import uuid4
from typing import Any

from mcp.server.fastmcp import FastMCP

from .models import PublicationContext, SearchResult
from .services.ai import AIService
from .services.search import DouSearchService
from .settings import Settings

settings = Settings()
search_service = DouSearchService(settings=settings)
ai_service = AIService(settings=settings)

mcp = FastMCP("ro-dou", host=settings.host, port=settings.port)


@mcp.tool()
def search_publications(
    query: str,
    date_from: str | None = None,
    date_to: str | None = None,
    pubname: list[str] | None = None,
    size: int = 10,
) -> dict[str, Any]:
    """Busca publicações do Diário Oficial na base PostgreSQL do INLABS."""
    return search_service.search_postgres(
        query=query,
        date_from=date_from,
        date_to=date_to,
        pubname=pubname,
        size=size,
    ).model_dump()


@mcp.tool()
def list_publications_by_day(
    pubdate: str | None = None,
    pubname: list[str] | None = None,
    size: int | None = None,
) -> dict[str, Any]:
    """Lista publicações do Diário Oficial de um dia na base PostgreSQL."""
    context_date = search_service.resolve_postgres_context_date(
        date_from=pubdate,
        date_to=None,
        pubname=pubname,
    )
    if not context_date:
        return {"query": "", "total": 0, "items": []}
    return search_service.list_publications_by_day_postgres(
        pubdate=context_date,
        pubname=pubname,
        size=size,
    ).model_dump()


@mcp.tool()
def get_publication(article_id: str) -> dict[str, Any]:
    """Busca uma publicação do Diário Oficial por id na base PostgreSQL."""
    return search_service.get_publication_postgres(article_id=article_id).model_dump()


@mcp.tool()
def answer_question(
    question: str,
    date_from: str | None = None,
    date_to: str | None = None,
    pubname: list[str] | None = None,
    size: int = 5,
) -> dict[str, Any]:
    """Responde usando todas as publicações do dia recuperadas do PostgreSQL."""
    context = _load_postgres_context(
        question=question,
        date_from=date_from,
        date_to=date_to,
        pubname=pubname,
        size=size,
    )
    answer = ai_service.answer(context=context)
    return {
        "answer": answer,
        "sources": [_source_payload(item) for item in context.publications],
        "context_source": context.source,
        "context_id": context.context_id,
        "fresh_context": True,
        "context_date": context.context_date,
        "total_publications": context.total_publications,
        "loaded_publications": len(context.publications),
    }


def _load_postgres_context(
    question: str,
    date_from: str | None,
    date_to: str | None,
    pubname: list[str] | None,
    size: int,
) -> PublicationContext:
    """Load all AI context from PostgreSQL before any provider call."""
    context_date = search_service.resolve_postgres_context_date(
        date_from=date_from,
        date_to=date_to,
        pubname=pubname,
    )
    if context_date:
        search_result = search_service.list_publications_by_day_postgres(
            pubdate=context_date,
            pubname=pubname,
            size=None,
        )
    else:
        search_result = search_service.search_postgres(
            query=question,
            date_from=date_from,
            date_to=date_to,
            pubname=pubname,
            size=size,
        )
    return _context_from_search_result(
        question=question,
        context_date=context_date,
        search_result=search_result,
    )


def _context_from_search_result(
    question: str,
    context_date: str | None,
    search_result: SearchResult,
) -> PublicationContext:
    return PublicationContext(
        context_id=str(uuid4()),
        source="postgres",
        question=question,
        context_date=context_date,
        total_publications=search_result.total,
        publications=search_result.items,
    )


def _source_payload(publication: Any) -> dict[str, Any]:
    """Return a compact source payload for chatbot responses."""
    payload = publication.model_dump()
    payload.pop("body", None)
    return payload


if __name__ == "__main__":
    mcp.run(transport=settings.transport)
