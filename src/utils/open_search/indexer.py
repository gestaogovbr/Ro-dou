"""Indexing pipeline for DOU articles from PostgreSQL into OpenSearch."""

import logging
import re

from opensearchpy.helpers import bulk  # type: ignore
from .client_open_search import OpenSearchClient  # type: ignore
from .config import INDEX_NAME, MAPPING, COLUMNS_NAME  # type: ignore


class Indexer:
    """Pipeline for indexing DOU articles from PostgreSQL into OpenSearch.

    Provides three pipeline steps:

    1. ``_ensure_index`` — creates the OpenSearch index if it does not exist.
    2. ``_fetch_from_postgres`` — streams article rows from the INLABS PostgreSQL
       database for a given publication date.
    3. ``run`` — orchestrates the full pipeline, calling the two steps above
       and bulk-loading the documents into OpenSearch.

    Example usage::

        indexer = Indexer(conn_id="inlabs_db")
        indexer.run(pubdate="2024-04-01")
    """

    def __init__(self, conn_id: str = "inlabs_db"):
        """Args:
        conn_id (str): Airflow connection ID for the INLABS PostgreSQL database.
            Defaults to ``"inlabs_db"``.
        STG_TABLE (str): PostgreSQL table name containing the article data.
            Defaults to ``"dou_inlabs.article_raw"``.
        """
        self.conn_id = conn_id
        self.STG_TABLE = "dou_inlabs.article_raw"
        self.client = OpenSearchClient().get_client()

    def _ensure_index(self):
        """Create the OpenSearch index if it does not already exist."""
        if not self.client.indices.exists(index=INDEX_NAME):
            self.client.indices.create(index=INDEX_NAME, body=MAPPING)
            logging.info(f"Índice '{INDEX_NAME}' criado.")

    def _fetch_from_postgres(self, pubdate: str, batch_size: int = 500):
        """Yield article documents from the INLABS PostgreSQL database.

        Queries ``{self.STG_TABLE}`` filtering by ``pubdate`` and streams rows in
        batches to avoid loading the full result set into memory at once.

        Args:
            pubdate (str): Publication date to filter by (``YYYY-MM-DD``).
            batch_size (int): Number of rows fetched per database round-trip.
                Defaults to 500.

        Yields:
            dict: One document per article row, with ``pubdate`` serialised to
                an ISO-8601 string.
        """
        from airflow.providers.postgres.hooks.postgres import PostgresHook  # type: ignore

        hook = PostgresHook(postgres_conn_id=self.conn_id)

        try:
            with hook.get_conn().cursor() as cur:
                cur.execute(
                    f"SELECT {', '.join(COLUMNS_NAME)} FROM {self.STG_TABLE} WHERE pubdate IS NOT NULL AND pubdate = %s",
                    (pubdate,),
                )
                while True:
                    rows = cur.fetchmany(batch_size)
                    if not rows:
                        break
                    for row in rows:
                        doc = dict(zip(COLUMNS_NAME, row))
                        if doc["pubdate"]:
                            doc["pubdate"] = doc["pubdate"].strftime("%Y-%m-%d")
                        yield doc
        finally:
            hook.get_conn().close()

    @staticmethod
    def _to_bulk_actions(docs):
        """Wrap documents in the OpenSearch bulk action format.

        Args:
            docs (Iterable[dict]): Documents to wrap.

        Yields:
            dict: Bulk action dict with ``_index``, ``_id``, and ``_source``.
        """
        for doc in docs:
            texto = doc.get("texto") or ""
            doc["texto_plain"] = re.sub(
                r"\s+", " ", re.sub("<[^>]+>", " ", texto)
            ).strip()
            yield {"_index": INDEX_NAME, "_id": doc["id"], "_source": doc}

    def run(self, pubdate: str, batch_size: int = 500):
        """Run the full PostgreSQL → OpenSearch indexing pipeline.

        Ensures the index exists, fetches articles from PostgreSQL, and
        bulk-loads them into OpenSearch. Errors are reported but do not raise.

        Args:
            pubdate (str): Publication date to index (``YYYY-MM-DD``).
            batch_size (int): Rows fetched per PostgreSQL round-trip. Defaults to 500.
        """
        self._ensure_index()

        success, errors = bulk(
            self.client,
            self._to_bulk_actions(self._fetch_from_postgres(pubdate, batch_size)),
            raise_on_error=False,
        )
        logging.info(f"Indexados: {success} documento(s)")
        if errors:
            logging.info(f"Erros: {len(errors)}")
            for err in errors[:5]:
                logging.info(f"  {err}")
