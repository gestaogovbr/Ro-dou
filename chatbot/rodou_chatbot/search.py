"""Reusable publication search service; all query languages stay in this layer."""

from __future__ import annotations

import logging
import re
import time
import unicodedata
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from psycopg.rows import dict_row

from .audit import AuditLog
from .config import AuditLogConfig, SearchConfig
from .models import PublicationResult, SearchIntent, SearchResult


SEARCHABLE_COLUMNS = (
    "texto",
    "titulo",
    "subtitulo",
    "identifica",
    "ementa",
    "name",
    "artcategory",
    "arttype",
    "assina",
)
logger = logging.getLogger("rodou_chatbot.search")
ORGANIZATION_ALIASES = {
    "mgi": "Ministério da Gestão e da Inovação em Serviços Públicos",
    "anvisa": "Agência Nacional de Vigilância Sanitária",
}
EXCERPT_CONTEXT_LENGTH = 400
NO_PUBLICATIONS_TODAY_MESSAGE = (
    "Não há publicações no dia de hoje para os filtros informados."
)


def result_limit_message(limit: int) -> str:
    return (
        f"Os resultados ultrapassam o limite de {limit} publicações definido "
        f"na configuração. Exibindo as primeiras {limit} publicações. "
        f"Tente refinar sua busca para reduzir o número de resultados."
    )


class PublicationSearchService:
    """Translate validated SearchIntent objects into internal source queries."""

    def __init__(
        self,
        config: SearchConfig,
        max_results: int,
        timezone: str = "America/Sao_Paulo",
        audit_log: AuditLog | None = None,
    ) -> None:
        self._config = config
        self._max_results = max_results
        self._timezone = timezone
        self._audit_log = audit_log or AuditLog(AuditLogConfig(enabled=False))
        self._opensearch_client = None

    def search(self, intent: SearchIntent) -> SearchResult:
        today = datetime.now(ZoneInfo(self._timezone)).date()
        bounded_intent = intent.model_copy(
            update={
                "limit": min(intent.limit, self._max_results),
                "date_from": today,
                "date_to": today,
            }
        )
        started = time.perf_counter()
        try:
            if self._config.source == "opensearch":
                result = self._search_opensearch(bounded_intent)
            else:
                result = self._search_postgres(bounded_intent)
        except Exception as exc:
            logger.error(
                "publication_search_failed source=%s error=%s",
                self._config.source,
                type(exc).__name__,
            )
            raise
        configuration_limit_reached = (
            bool(result.results)
            and intent.limit >= self._max_results
            and result.total > self._max_results
        )
        if not result.results:
            response_message = NO_PUBLICATIONS_TODAY_MESSAGE
        elif configuration_limit_reached:
            response_message = result_limit_message(self._max_results)
        else:
            response_message = None
        result = result.model_copy(
            update={
                "effective_date": today,
                "message": response_message,
            }
        )
        logger.info(
            "publication_search_completed source=%s duration_ms=%.2f result_count=%d",
            self._config.source,
            (time.perf_counter() - started) * 1000,
            result.total,
        )
        return result

    def _search_postgres(self, intent: SearchIntent) -> SearchResult:
        import psycopg

        where, params = self.build_postgres_where(intent)
        table = self._config.postgres_table
        if intent.terms and not intent.exact_search:
            params["headline_query"] = " ".join(intent.terms)
            excerpt_expression = """
                ts_headline(
                    'portuguese', coalesce(texto, ''),
                    plainto_tsquery('portuguese', %(headline_query)s),
                    'StartSel=<mark>, StopSel=</mark>, MaxFragments=1, MaxWords=80, MinWords=40'
                ) AS postgres_excerpt
            """
        else:
            excerpt_expression = "NULL::text AS postgres_excerpt"
        select_sql = f"""
            SELECT id, titulo, identifica, name, artcategory, pubname,
                   pubdate::date AS publication_date, texto, ementa, pdfpage,
                   {excerpt_expression}
              FROM {table}
             WHERE {where}
             ORDER BY pubdate DESC NULLS LAST, id DESC
             LIMIT %(limit)s
        """
        count_sql = f"SELECT count(*) AS total FROM {table} WHERE {where}"
        params["limit"] = intent.limit
        timeout_ms = str(int(self._config.timeout * 1000))
        with psycopg.connect(
            self._config.postgres_dsn,
            row_factory=dict_row,
            connect_timeout=max(1, int(self._config.timeout)),
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT set_config('statement_timeout', %(timeout)s, true)",
                    {"timeout": timeout_ms},
                )
                self._execute_sql(cursor, "count_publications", count_sql, params)
                total = int(cursor.fetchone()["total"])
                self._execute_sql(cursor, "search_publications", select_sql, params)
                rows = cursor.fetchall()
        return SearchResult(
            total=total,
            results=[
                self._publication_from_source(row, bounded_terms=intent.terms)
                for row in rows
            ],
        )

    def _execute_sql(
        self,
        cursor: Any,
        operation: str,
        statement: str,
        parameters: dict[str, Any],
    ) -> None:
        self._audit_log.log_sql(operation, statement, parameters)
        cursor.execute(statement, parameters)

    @classmethod
    def build_postgres_where(
        cls,
        intent: SearchIntent,
    ) -> tuple[str, dict[str, Any]]:
        """Build parameterized SQL predicates from a fully validated intent."""
        clauses: list[str] = ["TRUE"]
        params: dict[str, Any] = {}
        search_expression = cls._search_expression(intent.field)
        for index, term in enumerate(intent.terms):
            if intent.exact_search:
                key = f"term_{index}"
                params[key] = f"%{cls._escape_like(term)}%"
                clauses.append(f"{search_expression} ILIKE %({key})s ESCAPE '\\'")
            else:
                query_key = f"query_{index}"
                params[query_key] = term
                clauses.append(
                    f"to_tsvector('portuguese', {search_expression}) "
                    f"@@ plainto_tsquery('portuguese', %({query_key})s)"
                )
        for index, term in enumerate(intent.excluded_terms):
            key = f"excluded_{index}"
            params[key] = f"%{cls._escape_like(term)}%"
            clauses.append(
                f"{search_expression} NOT ILIKE %({key})s ESCAPE '\\'"
            )
        organization_groups: list[str] = []
        for organization_index, organization in enumerate(intent.organizations):
            tokens = cls._organization_tokens(organization)
            token_clauses: list[str] = []
            for token_index, token in enumerate(tokens):
                key = f"organization_{organization_index}_{token_index}"
                params[key] = f"%{cls._escape_like(token)}%"
                token_clauses.append(
                    "translate(lower(coalesce(artcategory, '')), "
                    "'áàãâäéèêëíìîïóòõôöúùûüç', "
                    "'aaaaaeeeeiiiiooooouuuuc') ILIKE %(" + key + ")s ESCAPE '\\'"
                )
            organization_groups.append("(" + " AND ".join(token_clauses) + ")")
        if organization_groups:
            clauses.append("(" + " OR ".join(organization_groups) + ")")
        if intent.sections:
            clauses.append("pubname = ANY(%(sections)s)")
            params["sections"] = intent.sections
        if intent.date_from:
            clauses.append("pubdate::date >= %(date_from)s")
            params["date_from"] = intent.date_from
        if intent.date_to:
            clauses.append("pubdate::date <= %(date_to)s")
            params["date_to"] = intent.date_to
        return " AND ".join(clauses), params

    @staticmethod
    def _search_expression(field: str | None) -> str:
        if field:
            # Pydantic's SearchField literal is the identifier allowlist.
            return f"coalesce({field}, '')"
        values = ", ".join(SEARCHABLE_COLUMNS)
        return f"concat_ws(' ', {values})"

    @staticmethod
    def _organization_tokens(value: str) -> list[str]:
        value = PublicationSearchService._expand_organization_alias(value)
        normalized = "".join(
            character
            for character in unicodedata.normalize("NFKD", value.lower())
            if not unicodedata.combining(character)
        )
        ignored = {"a", "as", "da", "das", "de", "do", "dos", "e", "em"}
        tokens = [
            token for token in re.findall(r"\w+", normalized) if token not in ignored
        ]
        return tokens or [normalized]

    @staticmethod
    def _expand_organization_alias(value: str) -> str:
        normalized = "".join(
            character
            for character in unicodedata.normalize("NFKD", value.strip().lower())
            if not unicodedata.combining(character)
        )
        return ORGANIZATION_ALIASES.get(normalized, value)

    @staticmethod
    def _escape_like(value: str) -> str:
        return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

    def _search_opensearch(self, intent: SearchIntent) -> SearchResult:
        if self._opensearch_client is None:
            from opensearchpy import OpenSearch

            auth = None
            if self._config.opensearch_user:
                password = (
                    self._config.opensearch_password.get_secret_value()
                    if self._config.opensearch_password
                    else ""
                )
                auth = (self._config.opensearch_user, password)
            self._opensearch_client = OpenSearch(
                hosts=[self._config.opensearch_host],
                http_auth=auth,
                timeout=self._config.timeout,
            )
        response = self._opensearch_client.search(
            index=self._config.opensearch_index,
            body=self.build_opensearch_query(intent),
        )
        hits = response.get("hits", {})
        total = hits.get("total", 0)
        if isinstance(total, dict):
            total = total.get("value", 0)
        return SearchResult(
            total=int(total),
            results=[
                self._publication_from_source(
                    {
                        **hit.get("_source", {}),
                        "id": hit.get("_id"),
                        "opensearch_highlights": hit.get("highlight", {}).get(
                            "texto_plain", []
                        ),
                    },
                    bounded_terms=intent.terms,
                )
                for hit in hits.get("hits", [])
            ],
        )

    @staticmethod
    def build_opensearch_query(intent: SearchIntent) -> dict[str, Any]:
        opensearch_field = "texto_plain" if intent.field == "texto" else intent.field
        fields = [opensearch_field] if opensearch_field else [
            "texto_plain",
            "titulo",
            "subtitulo",
            "identifica",
            "ementa",
            "name",
            "artcategory",
            "arttype",
            "assina",
        ]
        must: list[dict[str, Any]] = []
        for term in intent.terms:
            if intent.exact_search:
                must.append({"multi_match": {"query": term, "fields": fields, "type": "phrase"}})
            else:
                must.append({"multi_match": {"query": term, "fields": fields, "operator": "and"}})
        must_not = [
            {"multi_match": {"query": term, "fields": fields, "type": "phrase"}}
            for term in intent.excluded_terms
        ]
        filters: list[dict[str, Any]] = []
        if intent.organizations:
            filters.append(
                {
                    "bool": {
                        "should": [
                            {
                                "match_phrase": {
                                    "artcategory": PublicationSearchService._expand_organization_alias(
                                        organization
                                    )
                                }
                            }
                            for organization in intent.organizations
                        ],
                        "minimum_should_match": 1,
                    }
                }
            )
        if intent.sections:
            filters.append({"terms": {"pubname": intent.sections}})
        if intent.date_from or intent.date_to:
            date_range: dict[str, str] = {}
            if intent.date_from:
                date_range["gte"] = intent.date_from.isoformat()
            if intent.date_to:
                date_range["lte"] = intent.date_to.isoformat()
            filters.append({"range": {"pubdate": date_range}})
        bool_query: dict[str, Any] = {"filter": filters}
        bool_query["must"] = must or [{"match_all": {}}]
        if must_not:
            bool_query["must_not"] = must_not
        query = {
            "query": {"bool": bool_query},
            "size": intent.limit,
            "sort": [{"pubdate": "desc"}, {"_score": "desc"}],
        }
        if intent.terms:
            query["highlight"] = {
                "fields": {
                    "texto_plain": {
                        "fragment_size": EXCERPT_CONTEXT_LENGTH * 2,
                        "number_of_fragments": 1,
                    }
                }
            }
        return query

    @classmethod
    def _publication_from_source(
        cls,
        source: dict[str, Any],
        bounded_terms: list[str] | None = None,
    ) -> PublicationResult:
        raw_date = source.get("publication_date") or source.get("pubdate")
        if isinstance(raw_date, str):
            try:
                raw_date = date.fromisoformat(raw_date[:10])
            except ValueError:
                raw_date = None
        summary = cls._clean_text(source.get("ementa"))
        if summary and summary.lower() not in {"none", "nan", "null"}:
            content = summary
            content_type = "ementa"
        else:
            highlights = source.get("opensearch_highlights")
            if isinstance(highlights, list) and highlights:
                body = cls._clean_text(highlights[0])
            elif source.get("postgres_excerpt"):
                body = cls._clean_text(source["postgres_excerpt"])
            else:
                body = cls._clean_text(
                    source.get("texto_plain") or source.get("texto") or ""
                )
            content = cls._excerpt_around_terms(body, bounded_terms or [])
            content_type = "excerpt"
        return PublicationResult(
            id=str(source.get("id") or ""),
            title=source.get("titulo") or source.get("identifica") or source.get("name"),
            organization=source.get("artcategory"),
            section=source.get("pubname"),
            publication_date=raw_date,
            content=content,
            content_type=content_type,
            url=source.get("url") or source.get("pdfpage"),
        )

    @staticmethod
    def _clean_text(value: Any) -> str:
        if value is None:
            return ""
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", str(value))).strip()

    @classmethod
    def _excerpt_around_terms(cls, text: str, terms: list[str]) -> str:
        """Return a plain-text excerpt centered on the first searched term.

        This mirrors Ro-DOU's clipping behavior: keep context on both sides of
        the match and indicate omitted content. Matching ignores accents so a
        query such as ``Ministerio`` can anchor on ``Ministério``.
        """
        if not text:
            return ""
        normalized_text = cls._normalize(text)
        matches: list[tuple[int, int]] = []
        for term in terms:
            normalized_term = cls._normalize(term).strip()
            if not normalized_term:
                continue
            match = re.search(re.escape(normalized_term), normalized_text)
            if match:
                matches.append(match.span())

        if matches:
            match_start, match_end = min(matches, key=lambda match: match[0])
            start = max(0, match_start - EXCERPT_CONTEXT_LENGTH)
            end = min(len(text), match_end + EXCERPT_CONTEXT_LENGTH)
        else:
            start = 0
            end = min(len(text), EXCERPT_CONTEXT_LENGTH * 2)

        excerpt = text[start:end].strip()
        if start > 0:
            excerpt = f"(...) {excerpt}"
        if end < len(text):
            excerpt = f"{excerpt} (...)"
        return excerpt

    @staticmethod
    def _normalize(value: str) -> str:
        return "".join(
            character
            for character in unicodedata.normalize("NFKD", value.lower())
            if not unicodedata.combining(character)
        )
