"""Enrich INLABS documents in OpenSearch with entities from the GLiNER2 service.

The model runs in a dedicated HTTP service (``gliner_service/``); this module
only orchestrates: it finds documents of a publication date that still need
enrichment, sends their text to the service and stores the result through
partial updates, so the fields written by the ``Indexer`` are left untouched.

Each enriched document stores ``gliner.text_hash`` (hash of ``texto_plain``)
and ``gliner.fingerprint`` (hash of the service configuration). A document is
reprocessed only when one of them changes, which makes retries and repeated
runs for the same date resume from where they stopped. The current text hash
is read from ``texto_plain_hash``, written by the ``Indexer``, so pending
detection does not download the texts.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import urljoin, urlparse

import requests
from opensearchpy.helpers import bulk, scan  # type: ignore

from ..open_search.hashing import TEXT_HASH_FIELD, text_hash  # type: ignore

ENTITIES_FIELD = "entities"
METADATA_FIELD = "gliner"
# Used when the service does not advertise its limits in /info.
DEFAULT_MAX_CHARS = 100_000


def build_entities_mapping(entity_names: Iterable[str]) -> dict:
    """Return the ``put_mapping`` body for entity and metadata fields.

    Entities are searchable as text (Portuguese analyzer) and as exact values
    through the ``.keyword`` sub-field. Adding fields to an existing mapping
    is allowed by OpenSearch without reindexing.
    """
    entity_field = {
        "type": "text",
        "analyzer": "portuguese",
        "fields": {"keyword": {"type": "keyword", "ignore_above": 1024}},
    }
    return {
        "properties": {
            ENTITIES_FIELD: {
                "properties": {name: dict(entity_field) for name in entity_names}
            },
            METADATA_FIELD: {
                "properties": {
                    "fingerprint": {"type": "keyword"},
                    "model": {"type": "keyword"},
                    "text_hash": {"type": "keyword"},
                    "enriched_at": {"type": "date"},
                }
            },
        }
    }


class GlinerServiceError(RuntimeError):
    """Raised when the GLiNER2 service answers with an unexpected payload."""


class GlinerConfigurationChanged(RuntimeError):
    """Raised when the service fingerprint changes in the middle of a run."""


class GlinerServiceClient:
    """Minimal client for the GLiNER2 extraction service."""

    def __init__(
        self,
        base_url: str,
        token: Optional[str] = None,
        timeout: float = 600.0,
        session: Optional[requests.Session] = None,
    ):
        parsed = urlparse(base_url or "")
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError(
                "RO_DOU_GLINER_SERVICE_URL must be an http(s) URL, "
                f"got {base_url!r}"
            )
        self.base_url = base_url.rstrip("/") + "/"
        self.timeout = timeout
        self.session = session or requests.Session()
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"

    def _request(self, method: str, path: str, **kwargs) -> dict:
        response = self.session.request(
            method, urljoin(self.base_url, path), timeout=self.timeout, **kwargs
        )
        response.raise_for_status()
        return response.json()

    def info(self) -> dict:
        info = self._request("GET", "info")
        if not info.get("fingerprint") or not isinstance(info.get("entities"), list):
            raise GlinerServiceError(f"Invalid /info response: {info!r}")
        return info

    def extract(self, texts: Sequence[str]) -> dict:
        body = self._request("POST", "extract", json={"texts": list(texts)})
        results = body.get("results")
        if not isinstance(results, list) or len(results) != len(texts):
            raise GlinerServiceError(
                f"/extract returned {len(results) if isinstance(results, list) else 'no'} "
                f"results for {len(texts)} texts"
            )
        return body


class GlinerEnricher:
    """Enrich the documents of one publication date through partial updates."""

    def __init__(self, client, service: GlinerServiceClient, index: str):
        """Args:
        client: ``opensearchpy.OpenSearch`` instance.
        service: GLiNER2 service client.
        index: Index holding the INLABS documents.
        """
        self.client = client
        self.service = service
        self.index = index

    def ensure_mapping(self, entity_names: Iterable[str]) -> None:
        self.client.indices.put_mapping(
            index=self.index, body=build_entities_mapping(entity_names)
        )

    @staticmethod
    def _date_query(pubdate: str) -> dict:
        return {
            "query": {
                "bool": {
                    "filter": [{"range": {"pubdate": {"gte": pubdate, "lte": pubdate}}}]
                }
            }
        }

    def find_pending(self, pubdate: str, fingerprint: str) -> List[str]:
        """Return ids whose text or service configuration changed since the
        last enrichment (or that were never enriched), sorted for stable
        resumption.

        Only hashes are read. Enriched documents indexed before
        ``texto_plain_hash`` existed have their text fetched to compare.
        """
        pending = []
        legacy: Dict[str, Optional[str]] = {}
        hits = scan(
            self.client,
            index=self.index,
            query=self._date_query(pubdate),
            _source=[
                TEXT_HASH_FIELD,
                f"{METADATA_FIELD}.text_hash",
                f"{METADATA_FIELD}.fingerprint",
            ],
            size=500,
        )
        for hit in hits:
            source = hit.get("_source") or {}
            metadata = source.get(METADATA_FIELD) or {}
            if metadata.get("fingerprint") != fingerprint:
                pending.append(hit["_id"])
            elif source.get(TEXT_HASH_FIELD) is None:
                legacy[hit["_id"]] = metadata.get("text_hash")
            elif source[TEXT_HASH_FIELD] != metadata.get("text_hash"):
                pending.append(hit["_id"])

        legacy_ids = list(legacy)
        for start in range(0, len(legacy_ids), 500):
            texts = self._fetch_texts(legacy_ids[start : start + 500])
            pending.extend(
                doc_id for doc_id, text in texts.items() if legacy[doc_id] != text_hash(text)
            )
        return sorted(pending)

    def _fetch_texts(self, ids: Sequence[str]) -> Dict[str, str]:
        response = self.client.mget(
            index=self.index, body={"ids": list(ids)}, _source=["texto_plain"]
        )
        return {
            doc["_id"]: (doc.get("_source") or {}).get("texto_plain") or ""
            for doc in response.get("docs", [])
            if doc.get("found")
        }

    @staticmethod
    def _update_action(
        index: str,
        doc_id: str,
        text: str,
        entities: dict,
        entity_names: Sequence[str],
        info: dict,
        enriched_at: str,
    ) -> dict:
        # Every configured type is written (empty list when absent) so stale
        # values from a previous extraction are replaced.
        return {
            "_op_type": "update",
            "_index": index,
            "_id": doc_id,
            "doc": {
                ENTITIES_FIELD: {
                    name: list(entities.get(name) or []) for name in entity_names
                },
                METADATA_FIELD: {
                    "fingerprint": info["fingerprint"],
                    "model": info.get("model"),
                    "text_hash": text_hash(text),
                    "enriched_at": enriched_at,
                },
            },
        }

    @staticmethod
    def _split_by_chars(
        ids: Sequence[str], sizes: Dict[str, int], max_chars: int
    ) -> List[List[str]]:
        """Split ``ids`` into sub-batches whose total text size fits
        ``max_chars`` (a single oversized text still forms its own batch)."""
        batches: List[List[str]] = []
        current: List[str] = []
        total = 0
        for doc_id in ids:
            size = sizes[doc_id]
            if current and total + size > max_chars:
                batches.append(current)
                current, total = [], 0
            current.append(doc_id)
            total += size
        if current:
            batches.append(current)
        return batches

    def _extract(
        self, ids: Sequence[str], payload: Dict[str, str], fingerprint: str
    ) -> Tuple[List[Tuple[str, dict]], List[str]]:
        """Extract entities for ``ids``.

        When a batch fails (timeout, HTTP error, invalid answer), each
        document is retried alone so one problematic text does not block the
        others. Returns ``(results, failed_ids)``.
        """
        try:
            body = self.service.extract([payload[doc_id] for doc_id in ids])
        except (requests.RequestException, GlinerServiceError) as error:
            if len(ids) == 1:
                logging.error("GLiNER2 extraction failed for document %s: %s", ids[0], error)
                return [], list(ids)
            logging.warning(
                "GLiNER2 batch of %s documents failed (%s); retrying one by one.",
                len(ids),
                error,
            )
            results: List[Tuple[str, dict]] = []
            failed: List[str] = []
            for doc_id in ids:
                doc_results, doc_failed = self._extract([doc_id], payload, fingerprint)
                results.extend(doc_results)
                failed.extend(doc_failed)
            return results, failed

        if body.get("fingerprint") != fingerprint:
            raise GlinerConfigurationChanged(
                "GLiNER2 service configuration changed during the run "
                f"({fingerprint} -> {body.get('fingerprint')})."
            )
        return list(zip(ids, body["results"])), []

    def run(
        self,
        pubdate: str,
        documents_per_request: int = 8,
    ) -> dict:
        """Enrich pending documents of ``pubdate``.

        Each batch is written as soon as it is extracted, so a failure keeps
        the progress made so far. Documents that could not be extracted or
        written are reported and a ``RuntimeError`` is raised at the end,
        letting Airflow retry only what is left.

        Returns:
            dict: ``pending``, ``processed`` and ``failed`` counters.
        """
        if not self.client.indices.exists(index=self.index):
            logging.info("Index '%s' does not exist. Nothing to enrich.", self.index)
            return {"pending": 0, "processed": 0, "failed": 0}

        info = self.service.info()
        fingerprint = info["fingerprint"]
        entity_names = info["entities"]
        batch_size = max(
            1,
            min(
                documents_per_request,
                int(info.get("max_texts_per_request") or documents_per_request),
            ),
        )
        max_text_chars = int(info.get("max_text_chars") or DEFAULT_MAX_CHARS)
        max_chars = int(info.get("max_chars_per_request") or DEFAULT_MAX_CHARS)
        self.ensure_mapping(entity_names)

        pending = self.find_pending(pubdate, fingerprint)
        logging.info(
            "GLiNER2 enrichment for %s: %s pending (fingerprint %s).",
            pubdate,
            len(pending),
            fingerprint,
        )

        processed = 0
        failed: List[str] = []
        bulk_errors: List[dict] = []
        for start in range(0, len(pending), batch_size):
            group = pending[start : start + batch_size]
            texts = self._fetch_texts(group)
            # Documents deleted after the scan are simply skipped.
            group = [doc_id for doc_id in group if doc_id in texts]
            # The service truncates anyway; truncating here keeps requests
            # within its size limits. The hash always uses the full text.
            payload = {doc_id: texts[doc_id][:max_text_chars] for doc_id in group}
            sizes = {doc_id: len(text) for doc_id, text in payload.items()}

            for ids in self._split_by_chars(group, sizes, max_chars):
                results, batch_failed = self._extract(ids, payload, fingerprint)
                failed.extend(batch_failed)
                if not results:
                    continue
                enriched_at = datetime.now(timezone.utc).isoformat()
                actions = [
                    self._update_action(
                        self.index,
                        doc_id,
                        texts[doc_id],
                        entities,
                        entity_names,
                        info,
                        enriched_at,
                    )
                    for doc_id, entities in results
                ]
                success, errors = bulk(
                    self.client, actions, raise_on_error=False, raise_on_exception=False
                )
                processed += success
                bulk_errors.extend(errors)
            logging.info("GLiNER2 enrichment: %s/%s documents.", processed, len(pending))

        stats = {
            "pending": len(pending),
            "processed": processed,
            "failed": len(failed) + len(bulk_errors),
        }
        logging.info("GLiNER2 enrichment finished: %s", stats)
        if failed or bulk_errors:
            if failed:
                logging.error("Extraction failed for: %s", failed[:20])
            for error in bulk_errors[:5]:
                logging.error("  %s", error)
            raise RuntimeError(
                f"{stats['failed']} document(s) could not be enriched; "
                "they will be retried on the next attempt."
            )
        return stats
