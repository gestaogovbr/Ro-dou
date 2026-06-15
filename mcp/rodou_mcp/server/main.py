"""Ro-DOU MCP server entrypoint."""

from __future__ import annotations

import re
from typing import Any
from uuid import uuid4

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
def search_publications_by_field(
    field: str,
    value: str,
    date_from: str | None = None,
    date_to: str | None = None,
    pubname: list[str] | None = None,
    size: int = 10,
) -> dict[str, Any]:
    """Busca publicações no PostgreSQL onde um campo textual contém um valor."""
    return search_service.search_postgres_field_contains(
        field=field,
        value=value,
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
    direct_search = _parse_direct_field_search(question)
    if direct_search:
        field, value = direct_search
        result = search_service.search_postgres_field_contains(
            field=field,
            value=value,
            date_from=date_from,
            date_to=date_to,
            pubname=pubname,
            size=size,
        )
        context = _context_from_search_result(
            question=question,
            context_date=date_from or date_to,
            search_result=result,
        )
        return {
            "answer": _direct_search_answer(
                field=field,
                value=value,
                result=result,
            ),
            "sources": [_source_payload(item) for item in result.items],
            "context_source": context.source,
            "context_id": context.context_id,
            "fresh_context": True,
            "context_date": context.context_date,
            "total_publications": context.total_publications,
            "loaded_publications": len(context.publications),
            "ai_used": False,
        }

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
        "ai_used": True,
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


def _parse_direct_field_search(question: str) -> tuple[str, str] | None:
    """Parse simple database-only search intents from the chat text."""
    pattern = re.compile(
        r"\b(?:publications?|publicacoes|publicações|materias|matérias)\b"
        r".*?\b(?:where|onde)\b\s+"
        r"(?P<field>[a-zA-Z_]+)\s+"
        r"(?P<op>contain|contains|containing|contem|cont[eé]m|contendo)\s+"
        r"(?P<quote>['\"])(?P<value>.+?)(?P=quote)",
        re.IGNORECASE,
    )
    match = pattern.search(question)
    if not match:
        return None
    return match.group("field"), match.group("value")


def _direct_search_answer(field: str, value: str, result: SearchResult) -> str:
    lines = [
        f"Busca no banco PostgreSQL por publicações onde `{field}` contém `{value}`.",
        "",
        f"Total encontrado: **{result.total}**.",
    ]
    if not result.items:
        return "\n".join(lines)

    lines.extend(["", "Resultados:"])
    for publication in result.items:
        title = publication.title or "Sem titulo"
        label = f"{title} ({publication.id})"
        if publication.url:
            label = f"[{label}]({publication.url})"
        meta = " - ".join(
            item
            for item in [publication.pubdate, publication.pubname, publication.article_type]
            if item
        )
        lines.append(f"- {label}{f' - {meta}' if meta else ''}")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run(transport=settings.transport)
