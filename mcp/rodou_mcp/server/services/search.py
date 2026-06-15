"""Publication search for the MCP server."""

from __future__ import annotations

import re
from typing import Any

from opensearchpy import OpenSearch
from psycopg.rows import dict_row

from ..models import Publication, SearchResult
from ..settings import Settings


class DouSearchService:
    """Search processed DOU publications without depending on Airflow."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._index = settings.opensearch_index
        self._client: OpenSearch | None = None
        if not settings.enable_opensearch:
            return

        auth = None
        if settings.opensearch_user:
            auth = (settings.opensearch_user, settings.opensearch_pass)

        self._client = OpenSearch(
            hosts=[settings.opensearch_host],
            http_auth=auth,
            http_compress=True,
            use_ssl=settings.opensearch_use_ssl,
            verify_certs=settings.opensearch_verify_certs,
        )

    def search(
        self,
        query: str,
        date_from: str | None,
        date_to: str | None,
        pubname: list[str] | None,
        size: int,
    ) -> SearchResult:
        """Run a keyword search against the configured publication source."""
        if self._settings.enable_opensearch:
            return self._search_opensearch(
                query=query,
                date_from=date_from,
                date_to=date_to,
                pubname=pubname,
                size=size,
            )
        return self._search_postgres(
            query=query,
            date_from=date_from,
            date_to=date_to,
            pubname=pubname,
            size=size,
        )

    def search_postgres(
        self,
        query: str,
        date_from: str | None,
        date_to: str | None,
        pubname: list[str] | None,
        size: int,
    ) -> SearchResult:
        """Run a keyword search directly against the INLABS PostgreSQL source."""
        return self._search_postgres(
            query=query,
            date_from=date_from,
            date_to=date_to,
            pubname=pubname,
            size=size,
        )

    def get_publication(self, article_id: str) -> Publication:
        """Fetch one publication by document id."""
        if self._settings.enable_opensearch:
            if self._client is None:
                raise RuntimeError("OpenSearch client is not configured")
            response = self._client.get(index=self._index, id=article_id)
            return self._publication_from_source(
                source=response.get("_source", {}),
                score=response.get("_score"),
                article_id=response.get("_id", article_id),
            )
        return self._get_publication_postgres(article_id=article_id)

    def get_publication_postgres(self, article_id: str) -> Publication:
        """Fetch one INLABS publication directly from PostgreSQL by id."""
        return self._get_publication_postgres(article_id=article_id)

    def search_postgres_field_contains(
        self,
        field: str,
        value: str,
        date_from: str | None,
        date_to: str | None,
        pubname: list[str] | None,
        size: int,
    ) -> SearchResult:
        """Search a safe text field with ILIKE directly in PostgreSQL."""
        import psycopg

        safe_field = self._safe_search_field(field)
        bounded_size = max(1, min(size, 100))
        clauses = [f"{safe_field} ILIKE %(pattern)s"]
        params: dict[str, Any] = {
            "pattern": f"%{value}%",
            "limit": bounded_size,
        }
        if date_from:
            clauses.append("pubdate::date >= %(date_from)s")
            params["date_from"] = date_from
        if date_to:
            clauses.append("pubdate::date <= %(date_to)s")
            params["date_to"] = date_to
        if pubname:
            clauses.append("pubname = ANY(%(pubname)s)")
            params["pubname"] = pubname

        where = " AND ".join(clauses)
        sql = f"""
            SELECT
                {self._postgres_select_columns()}
            FROM {self._settings.inlabs_table}
            WHERE {where}
            ORDER BY pubdate DESC NULLS LAST, id DESC
            LIMIT %(limit)s
        """
        count_sql = (
            f"SELECT count(*) AS total FROM {self._settings.inlabs_table} WHERE {where}"
        )
        with psycopg.connect(
            self._settings.inlabs_postgres_dsn,
            row_factory=dict_row,
        ) as conn:
            with conn.cursor() as cur:
                cur.execute(count_sql, params)
                total = cur.fetchone()["total"]
                cur.execute(sql, params)
                rows = cur.fetchall()

        return SearchResult(
            query=f"{safe_field} contains {value}",
            total=int(total),
            items=[
                self._publication_from_source(
                    row,
                    score=None,
                    article_id=str(row["id"]),
                )
                for row in rows
            ],
        )

    def resolve_postgres_context_date(
        self,
        date_from: str | None,
        date_to: str | None,
        pubname: list[str] | None,
    ) -> str | None:
        """Resolve the publication date used for full-day context."""
        if date_from:
            return date_from
        if date_to:
            return date_to

        import psycopg

        where = "pubdate IS NOT NULL"
        params: dict[str, Any] = {}
        if pubname:
            where = f"{where} AND pubname = ANY(%(pubname)s)"
            params["pubname"] = pubname

        sql = f"""
            SELECT max(pubdate::date)::text AS pubdate
            FROM {self._settings.inlabs_table}
            WHERE {where}
        """
        with psycopg.connect(
            self._settings.inlabs_postgres_dsn,
            row_factory=dict_row,
        ) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                row = cur.fetchone()
        if not row:
            return None
        return row["pubdate"]

    def list_publications_by_day_postgres(
        self,
        pubdate: str,
        pubname: list[str] | None,
        size: int | None = None,
    ) -> SearchResult:
        """List DOU publications for a publication day from PostgreSQL."""
        import psycopg

        bounded_size = max(
            1,
            min(size or self._settings.day_context_publication_limit, 10000),
        )
        clauses = ["pubdate::date = %(pubdate)s"]
        params: dict[str, Any] = {"pubdate": pubdate, "limit": bounded_size}
        if pubname:
            clauses.append("pubname = ANY(%(pubname)s)")
            params["pubname"] = pubname
        where = " AND ".join(clauses)
        sql = f"""
            SELECT
                {self._postgres_select_columns()}
            FROM {self._settings.inlabs_table}
            WHERE {where}
            ORDER BY pubname ASC NULLS LAST, id DESC
            LIMIT %(limit)s
        """
        count_sql = (
            f"SELECT count(*) AS total FROM {self._settings.inlabs_table} WHERE {where}"
        )
        with psycopg.connect(
            self._settings.inlabs_postgres_dsn,
            row_factory=dict_row,
        ) as conn:
            with conn.cursor() as cur:
                cur.execute(count_sql, params)
                total = cur.fetchone()["total"]
                cur.execute(sql, params)
                rows = cur.fetchall()
        return SearchResult(
            query=f"pubdate:{pubdate}",
            total=int(total),
            items=[
                self._publication_from_source(
                    row,
                    score=None,
                    article_id=str(row["id"]),
                )
                for row in rows
            ],
        )

    def _search_opensearch(
        self,
        query: str,
        date_from: str | None,
        date_to: str | None,
        pubname: list[str] | None,
        size: int,
    ) -> SearchResult:
        """Run a keyword search against indexed OpenSearch publications."""
        if self._client is None:
            raise RuntimeError("OpenSearch client is not configured")
        bounded_size = max(1, min(size, 50))
        response = self._client.search(
            index=self._index,
            body=self._build_query(
                query=query,
                date_from=date_from,
                date_to=date_to,
                pubname=pubname,
                size=bounded_size,
            ),
        )
        hits = response.get("hits", {})
        return SearchResult(
            query=query,
            total=self._total_value(hits.get("total", 0)),
            items=[self._publication_from_hit(hit) for hit in hits.get("hits", [])],
        )

    def _search_postgres(
        self,
        query: str,
        date_from: str | None,
        date_to: str | None,
        pubname: list[str] | None,
        size: int,
    ) -> SearchResult:
        """Run a keyword search directly against the INLABS PostgreSQL table."""
        import psycopg

        bounded_size = max(1, min(size, 50))
        where, params = self._build_postgres_where(
            query=query,
            date_from=date_from,
            date_to=date_to,
            pubname=pubname,
        )
        sql = f"""
            SELECT
                {self._postgres_select_columns()}
            FROM {self._settings.inlabs_table}
            WHERE {where}
            ORDER BY pubdate DESC NULLS LAST, id DESC
            LIMIT %(limit)s
        """
        count_sql = (
            f"SELECT count(*) AS total FROM {self._settings.inlabs_table} WHERE {where}"
        )
        params["limit"] = bounded_size

        with psycopg.connect(
            self._settings.inlabs_postgres_dsn,
            row_factory=dict_row,
        ) as conn:
            with conn.cursor() as cur:
                cur.execute(count_sql, params)
                total = cur.fetchone()["total"]
                cur.execute(sql, params)
                rows = cur.fetchall()

        return SearchResult(
            query=query,
            total=int(total),
            items=[
                self._publication_from_source(
                    row,
                    score=None,
                    article_id=str(row["id"]),
                )
                for row in rows
            ],
        )

    def _get_publication_postgres(self, article_id: str) -> Publication:
        """Fetch one INLABS publication directly from PostgreSQL."""
        import psycopg

        sql = f"""
            SELECT
                {self._postgres_select_columns()}
            FROM {self._settings.inlabs_table}
            WHERE id = %(article_id)s
            LIMIT 1
        """
        with psycopg.connect(
            self._settings.inlabs_postgres_dsn,
            row_factory=dict_row,
        ) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, {"article_id": article_id})
                row = cur.fetchone()
        if not row:
            raise LookupError(f"Publication not found: {article_id}")
        return self._publication_from_source(row, score=None, article_id=article_id)

    @staticmethod
    def _build_postgres_where(
        query: str,
        date_from: str | None,
        date_to: str | None,
        pubname: list[str] | None,
    ) -> tuple[str, dict[str, Any]]:
        clauses = [
            """
            (
                to_tsvector(
                    'portuguese',
                    concat_ws(
                        ' ',
                        texto,
                        titulo,
                        subtitulo,
                        identifica,
                        ementa,
                        name,
                        artcategory,
                        arttype,
                        assina
                    )
                ) @@ plainto_tsquery('portuguese', %(query)s)
                OR texto ILIKE %(pattern)s
                OR titulo ILIKE %(pattern)s
                OR subtitulo ILIKE %(pattern)s
                OR identifica ILIKE %(pattern)s
                OR ementa ILIKE %(pattern)s
                OR name ILIKE %(pattern)s
                OR artcategory ILIKE %(pattern)s
                OR arttype ILIKE %(pattern)s
                OR assina ILIKE %(pattern)s
            )
            """
        ]
        params: dict[str, Any] = {"query": query, "pattern": f"%{query}%"}
        if date_from:
            clauses.append("pubdate::date >= %(date_from)s")
            params["date_from"] = date_from
        if date_to:
            clauses.append("pubdate::date <= %(date_to)s")
            params["date_to"] = date_to
        if pubname:
            clauses.append("pubname = ANY(%(pubname)s)")
            params["pubname"] = pubname
        return " AND ".join(clauses), params

    def _build_query(
        self,
        query: str,
        date_from: str | None,
        date_to: str | None,
        pubname: list[str] | None,
        size: int,
    ) -> dict[str, Any]:
        filters: list[dict[str, Any]] = []
        if date_from or date_to:
            range_filter: dict[str, str] = {}
            if date_from:
                range_filter["gte"] = date_from
            if date_to:
                range_filter["lte"] = date_to
            filters.append({"range": {"pubdate": range_filter}})

        if pubname:
            filters.append({"terms": {"pubname": pubname}})

        body = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "query_string": {
                                "query": query,
                                "default_field": "texto_plain",
                            }
                        }
                    ],
                }
            },
            "size": size,
            "sort": [{"_score": "desc"}],
        }
        if filters:
            body["query"]["bool"]["filter"] = filters
        return body

    @staticmethod
    def _publication_from_hit(hit: dict[str, Any]) -> Publication:
        return DouSearchService._publication_from_source(
            source=hit.get("_source", {}),
            score=hit.get("_score"),
            article_id=hit.get("_id"),
        )

    @staticmethod
    def _publication_from_source(
        source: dict[str, Any],
        score: float | None,
        article_id: str | None,
    ) -> Publication:
        id_materia = source.get("idmateria")
        body = source.get("texto_plain") or DouSearchService._strip_html(
            source.get("texto"),
        )
        pdfpage = source.get("pdfpage")
        return Publication(
            id=str(source.get("id") or article_id or ""),
            id_materia=str(id_materia) if id_materia else None,
            title=source.get("titulo") or source.get("identifica") or source.get("name"),
            subtitle=source.get("subtitulo"),
            pubname=source.get("pubname"),
            pubdate=source.get("pubdate"),
            category=source.get("artcategory"),
            article_type=source.get("arttype"),
            body=body,
            url=DouSearchService._dou_publication_url(pdfpage),
            score=score,
        )

    @staticmethod
    def _postgres_select_columns() -> str:
        return """
            id,
            name,
            idmateria,
            pubname,
            arttype,
            pubdate::date::text AS pubdate,
            artcategory,
            artclass,
            pdfpage,
            identifica,
            ementa,
            titulo,
            subtitulo,
            texto,
            assina,
            numberpage,
            editionnumber
        """

    @staticmethod
    def _safe_search_field(field: str) -> str:
        allowed_fields = {
            "ementa",
            "texto",
            "titulo",
            "subtitulo",
            "identifica",
            "name",
            "artcategory",
            "arttype",
            "assina",
        }
        normalized = field.strip().lower()
        if normalized not in allowed_fields:
            raise ValueError(f"Unsupported search field: {field}")
        return normalized

    @staticmethod
    def _dou_publication_url(pdfpage: Any) -> str | None:
        if not pdfpage:
            return None
        return pdfpage

    @staticmethod
    def _strip_html(value: str | None) -> str | None:
        if not value:
            return None
        return re.sub(r"\s+", " ", re.sub("<[^>]+>", " ", value)).strip()

    @staticmethod
    def _total_value(total: int | dict[str, Any]) -> int:
        if isinstance(total, dict):
            return int(total.get("value", 0))
        return int(total)
