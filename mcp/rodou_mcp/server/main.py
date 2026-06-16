"""Ro-DOU MCP server entrypoint."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

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
    count_date = _parse_publication_count_date(question, date_from, date_to)
    if count_date:
        result = search_service.list_publications_by_day_postgres(
            pubdate=count_date,
            pubname=pubname,
            size=1,
        )
        context = _context_from_search_result(
            question=question,
            context_date=count_date,
            search_result=result,
        )
        return {
            "answer": _count_answer(pubdate=count_date, total=result.total),
            "sources": [],
            "context_source": context.source,
            "context_id": context.context_id,
            "fresh_context": True,
            "context_date": context.context_date,
            "total_publications": context.total_publications,
            "loaded_publications": 0,
            "ai_used": False,
        }

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
    if not context.publications:
        return {
            "answer": "Nao encontrei publicacoes do DOU relacionadas a essa pergunta.",
            "sources": [],
            "context_source": context.source,
            "context_id": context.context_id,
            "fresh_context": True,
            "context_date": context.context_date,
            "total_publications": context.total_publications,
            "loaded_publications": 0,
            "ai_used": False,
        }

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
    """Load AI context from a PostgreSQL search filtered by the user's request."""
    search_date_from, search_date_to, context_date = _resolve_search_dates(
        question=question,
        date_from=date_from,
        date_to=date_to,
    )
    search_result = search_service.search_postgres(
        query=_database_query_from_question(question),
        date_from=search_date_from,
        date_to=search_date_to,
        pubname=pubname,
        size=_ai_context_size(size),
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


def _parse_publication_count_date(
    question: str,
    date_from: str | None,
    date_to: str | None,
) -> str | None:
    """Parse simple database-only count intents."""
    normalized = question.strip().lower()
    is_count = bool(
        re.search(
            r"\b(count|total|how many|quantas|quantos|contar|conte)\b",
            normalized,
        )
    )
    mentions_publications = bool(
        re.search(
            r"\b(publications?|publicacoes|publicações|materias|matérias)\b",
            normalized,
        )
    )
    if not (is_count and mentions_publications):
        return None
    if date_from and (not date_to or date_to == date_from):
        return date_from
    if date_to and not date_from:
        return date_to
    explicit_date = _parse_date_from_question(normalized)
    if explicit_date:
        return explicit_date
    if re.search(r"\b(today|hoje)\b", normalized):
        return datetime.now(ZoneInfo(settings.timezone)).date().isoformat()
    return None


def _parse_date_from_question(question: str) -> str | None:
    """Extract a date from the question and normalize it to ISO format."""
    for pattern, date_format in (
        (r"\b(?P<date>\d{4}-\d{2}-\d{2})\b", "%Y-%m-%d"),
        (r"\b(?P<date>\d{2}/\d{2}/\d{4})\b", "%d/%m/%Y"),
        (r"\b(?P<date>\d{2}-\d{2}-\d{4})\b", "%d-%m-%Y"),
    ):
        match = re.search(pattern, question)
        if not match:
            continue
        try:
            return datetime.strptime(match.group("date"), date_format).date().isoformat()
        except ValueError:
            return None
    return None


def _resolve_search_dates(
    question: str,
    date_from: str | None,
    date_to: str | None,
) -> tuple[str | None, str | None, str | None]:
    """Resolve optional date filters without falling back to a full-day context."""
    if date_from or date_to:
        context_date = date_from if date_from and date_from == date_to else None
        return date_from, date_to, context_date

    normalized = question.strip().lower()
    explicit_date = _parse_date_from_question(normalized)
    if explicit_date:
        return explicit_date, explicit_date, explicit_date
    if re.search(r"\b(today|hoje)\b", normalized):
        today = datetime.now(ZoneInfo(settings.timezone)).date().isoformat()
        return today, today, today
    return None, None, None


def _database_query_from_question(question: str) -> str:
    """Extract a compact keyword query before building AI context."""
    normalized = question.strip().lower()
    if quoted := re.findall(r"['\"]([^'\"]+)['\"]", question):
        return " ".join(item.strip() for item in quoted if item.strip())

    normalized = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", " ", normalized)
    normalized = re.sub(r"\b\d{2}[/-]\d{2}[/-]\d{4}\b", " ", normalized)
    normalized = re.sub(r"[^\wÀ-ÿ]+", " ", normalized)
    stopwords = {
        "a",
        "as",
        "about",
        "and",
        "com",
        "da",
        "das",
        "de",
        "do",
        "dos",
        "em",
        "for",
        "hoje",
        "list",
        "liste",
        "me",
        "mostre",
        "o",
        "of",
        "on",
        "os",
        "para",
        "por",
        "publicacao",
        "publicacoes",
        "publicação",
        "publicações",
        "publication",
        "publications",
        "resuma",
        "resumo",
        "sobre",
        "summarize",
        "summary",
        "the",
        "today",
        "with",
    }
    tokens = [
        token
        for token in normalized.split()
        if len(token) > 1 and token not in stopwords
    ]
    if not tokens:
        return "__ro_dou_no_ai_context_filter__"
    return " ".join(tokens)


def _ai_context_size(size: int) -> int:
    return max(1, min(size, settings.ai_context_publication_limit))


def _count_answer(pubdate: str, total: int) -> str:
    return (
        "Busca no banco PostgreSQL por contagem de publicações.\n\n"
        f"Data: `{pubdate}`\n\n"
        f"Total encontrado: **{total}**."
    )


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
