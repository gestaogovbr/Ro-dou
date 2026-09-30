"""Tests for the GLiNER2 enrichment of OpenSearch documents."""

from unittest.mock import MagicMock

import pytest
import requests

from dags.ro_dou_src.utils.gliner import gliner_enrichment
from dags.ro_dou_src.utils.gliner.gliner_enrichment import (
    GlinerConfigurationChanged,
    GlinerEnricher,
    GlinerServiceClient,
    GlinerServiceError,
    build_entities_mapping,
    text_hash,
)
from dags.ro_dou_src.utils.open_search.hashing import TEXT_HASH_MAPPING
from dags.ro_dou_src.utils.open_search.indexer import Indexer

FINGERPRINT = "abc123"
INFO = {
    "model": "fastino/gliner2.5-multi-v1",
    "fingerprint": FINGERPRINT,
    "entities": ["person", "process"],
    "max_texts_per_request": 32,
}


class FakeService:
    """Stands in for ``GlinerServiceClient``."""

    def __init__(self, info=None, fingerprint=FINGERPRINT, fail_on=()):
        self._info = dict(info or INFO)
        self._fingerprint = fingerprint
        self._fail_on = set(fail_on)
        self.requests = []

    def info(self):
        return self._info

    def extract(self, texts):
        self.requests.append(list(texts))
        if self._fail_on.intersection(texts):
            raise requests.ReadTimeout("simulated timeout")
        return {
            "fingerprint": self._fingerprint,
            "results": [{"person": [t.upper()]} if t else {} for t in texts],
        }


@pytest.fixture
def opensearch():
    client = MagicMock()
    client.indices.exists.return_value = True
    return client


def _hit(doc_id, text, fingerprint=None, stored_hash=None, legacy=False):
    """Scan hit with the fields requested by ``find_pending``. ``legacy``
    documents were indexed before ``texto_plain_hash`` existed."""
    source = {} if legacy else {"texto_plain_hash": text_hash(text)}
    if fingerprint is not None:
        source["gliner"] = {"fingerprint": fingerprint, "text_hash": stored_hash}
    return {"_id": doc_id, "_source": source}


def _mget_response(texts_by_id):
    def mget(index, body, _source):
        return {
            "docs": [
                {"_id": i, "found": i in texts_by_id, "_source": {"texto_plain": texts_by_id.get(i)}}
                for i in body["ids"]
            ]
        }

    return mget


@pytest.fixture
def bulk_calls(monkeypatch):
    calls = []

    def fake_bulk(client, actions, **kwargs):
        actions = list(actions)
        calls.append(actions)
        return len(actions), []

    monkeypatch.setattr(gliner_enrichment, "bulk", fake_bulk)
    return calls


# Mapping ---------------------------------------------------------------------


def test_build_entities_mapping_declares_each_entity_and_metadata():
    mapping = build_entities_mapping(["person", "process"])
    entities = mapping["properties"]["entities"]["properties"]
    assert set(entities) == {"person", "process"}
    assert entities["person"]["type"] == "text"
    assert entities["person"]["fields"]["keyword"]["type"] == "keyword"
    metadata = mapping["properties"]["gliner"]["properties"]
    assert metadata["fingerprint"] == {"type": "keyword"}
    assert metadata["enriched_at"] == {"type": "date"}


# Pending detection -----------------------------------------------------------


def test_find_pending_selects_new_changed_and_outdated_documents(opensearch, monkeypatch):
    hits = [
        _hit("new", "texto novo"),
        _hit("done", "mesmo texto", FINGERPRINT, text_hash("mesmo texto")),
        _hit("changed_text", "texto alterado", FINGERPRINT, text_hash("texto antigo")),
        _hit("old_config", "texto", "outra-config", text_hash("texto")),
    ]
    captured = {}

    def fake_scan(client, **kwargs):
        captured.update(kwargs)
        return iter(hits)

    monkeypatch.setattr(gliner_enrichment, "scan", fake_scan)
    enricher = GlinerEnricher(opensearch, FakeService(), "dou")

    pending = enricher.find_pending("2026-09-29", FINGERPRINT)

    assert pending == ["changed_text", "new", "old_config"]
    # Only hashes are read; no text is downloaded when every document has one.
    assert "texto_plain" not in captured["_source"]
    assert "texto_plain_hash" in captured["_source"]
    opensearch.mget.assert_not_called()
    # Only the publication date is filtered: every section is enriched.
    assert captured["query"] == {
        "query": {
            "bool": {
                "filter": [
                    {"range": {"pubdate": {"gte": "2026-09-29", "lte": "2026-09-29"}}}
                ]
            }
        }
    }


def test_find_pending_compares_text_of_legacy_documents(opensearch, monkeypatch):
    hits = [
        _hit("same", "igual", FINGERPRINT, text_hash("igual"), legacy=True),
        _hit("changed", "novo", FINGERPRINT, text_hash("antigo"), legacy=True),
        _hit("never", "x", legacy=True),
    ]
    monkeypatch.setattr(gliner_enrichment, "scan", lambda client, **kw: iter(hits))
    opensearch.mget.side_effect = _mget_response({"same": "igual", "changed": "novo"})

    pending = GlinerEnricher(opensearch, FakeService(), "dou").find_pending(
        "2026-09-29", FINGERPRINT
    )

    assert pending == ["changed", "never"]
    # Never-enriched documents are pending without fetching their text.
    fetched = opensearch.mget.call_args.kwargs["body"]["ids"]
    assert sorted(fetched) == ["changed", "same"]


# Run -------------------------------------------------------------------------


def test_run_updates_pending_documents_in_batches(opensearch, monkeypatch, bulk_calls):
    texts = {"1": "ana", "2": "bia", "3": "", "4": "caio"}
    monkeypatch.setattr(
        gliner_enrichment, "scan", lambda client, **kw: iter(_hit(i, t) for i, t in texts.items())
    )
    opensearch.mget.side_effect = _mget_response(texts)
    service = FakeService()

    stats = GlinerEnricher(opensearch, service, "dou").run(
        "2026-09-29", documents_per_request=3
    )

    assert stats == {"pending": 4, "processed": 4, "failed": 0}
    assert service.requests == [["ana", "bia", ""], ["caio"]]
    opensearch.indices.put_mapping.assert_called_once()
    first = bulk_calls[0][0]
    assert first["_op_type"] == "update"
    assert first["_index"] == "dou"
    assert first["_id"] == "1"
    assert "doc_as_upsert" not in first
    # Every configured entity type is written so stale values are replaced.
    assert first["doc"]["entities"] == {"person": ["ANA"], "process": []}
    assert first["doc"]["gliner"]["fingerprint"] == FINGERPRINT
    assert first["doc"]["gliner"]["text_hash"] == text_hash("ana")
    empty = bulk_calls[0][2]
    assert empty["doc"]["entities"] == {"person": [], "process": []}


def test_run_processes_all_pending_within_service_limit(opensearch, monkeypatch, bulk_calls):
    texts = {str(i): f"texto {i}" for i in range(5)}
    monkeypatch.setattr(
        gliner_enrichment, "scan", lambda client, **kw: iter(_hit(i, t) for i, t in texts.items())
    )
    opensearch.mget.side_effect = _mget_response(texts)
    service = FakeService(info={**INFO, "max_texts_per_request": 2})

    stats = GlinerEnricher(opensearch, service, "dou").run(
        "2026-09-29", documents_per_request=8
    )

    assert stats == {"pending": 5, "processed": 5, "failed": 0}
    assert [len(batch) for batch in service.requests] == [2, 2, 1]


def test_run_skips_documents_deleted_after_scan(opensearch, monkeypatch, bulk_calls):
    monkeypatch.setattr(
        gliner_enrichment, "scan", lambda client, **kw: iter([_hit("1", "a"), _hit("2", "b")])
    )
    opensearch.mget.side_effect = _mget_response({"1": "a"})
    service = FakeService()

    stats = GlinerEnricher(opensearch, service, "dou").run("2026-09-29")

    assert service.requests == [["a"]]
    assert stats["processed"] == 1
    assert stats == {"pending": 2, "processed": 1, "failed": 0}


def test_run_without_index_does_nothing(opensearch):
    opensearch.indices.exists.return_value = False
    service = MagicMock()

    stats = GlinerEnricher(opensearch, service, "dou").run("2026-09-29")

    assert stats["pending"] == 0 and stats["processed"] == 0
    service.info.assert_not_called()


def test_run_fails_when_service_configuration_changes(opensearch, monkeypatch, bulk_calls):
    monkeypatch.setattr(gliner_enrichment, "scan", lambda client, **kw: iter([_hit("1", "a")]))
    opensearch.mget.side_effect = _mget_response({"1": "a"})

    with pytest.raises(GlinerConfigurationChanged):
        GlinerEnricher(opensearch, FakeService(fingerprint="nova"), "dou").run("2026-09-29")
    assert bulk_calls == []


def test_run_raises_after_writing_when_bulk_has_errors(opensearch, monkeypatch):
    monkeypatch.setattr(
        gliner_enrichment, "scan", lambda client, **kw: iter([_hit("1", "a"), _hit("2", "b")])
    )
    opensearch.mget.side_effect = _mget_response({"1": "a", "2": "b"})
    monkeypatch.setattr(
        gliner_enrichment,
        "bulk",
        lambda client, actions, **kw: (1, [{"update": {"_id": "2", "error": "x"}}]),
    )

    with pytest.raises(RuntimeError, match="1 document"):
        GlinerEnricher(opensearch, FakeService(), "dou").run("2026-09-29")


def test_failed_batch_is_retried_one_by_one_and_run_continues(
    opensearch, monkeypatch, bulk_calls
):
    texts = {"1": "ana", "2": "ruim", "3": "bia", "4": "caio"}
    monkeypatch.setattr(
        gliner_enrichment, "scan", lambda client, **kw: iter(_hit(i, t) for i, t in texts.items())
    )
    opensearch.mget.side_effect = _mget_response(texts)
    service = FakeService(fail_on={"ruim"})

    with pytest.raises(RuntimeError, match="1 document"):
        GlinerEnricher(opensearch, service, "dou").run("2026-09-29", documents_per_request=2)

    # Batch [ana, ruim] fails, is split, and the later batch still runs.
    assert service.requests == [["ana", "ruim"], ["ana"], ["ruim"], ["bia", "caio"]]
    written = [action["_id"] for batch in bulk_calls for action in batch]
    assert written == ["1", "3", "4"]


def test_batches_respect_character_limit_and_truncate_texts(
    opensearch, monkeypatch, bulk_calls
):
    texts = {"1": "a" * 6, "2": "b" * 6, "3": "c" * 30}
    monkeypatch.setattr(
        gliner_enrichment, "scan", lambda client, **kw: iter(_hit(i, t) for i, t in texts.items())
    )
    opensearch.mget.side_effect = _mget_response(texts)
    service = FakeService(info={**INFO, "max_text_chars": 10, "max_chars_per_request": 10})

    GlinerEnricher(opensearch, service, "dou").run("2026-09-29")

    assert service.requests == [["a" * 6], ["b" * 6], ["c" * 10]]
    by_id = {action["_id"]: action for batch in bulk_calls for action in batch}
    # The stored hash is always the hash of the full text.
    assert by_id["3"]["doc"]["gliner"]["text_hash"] == text_hash("c" * 30)


def test_split_by_chars_groups_small_texts():
    sizes = {"1": 4, "2": 4, "3": 4, "4": 20}
    assert GlinerEnricher._split_by_chars(["1", "2", "3", "4"], sizes, 10) == [
        ["1", "2"],
        ["3"],
        ["4"],
    ]


# Service client --------------------------------------------------------------


def _response(payload, status=200):
    response = MagicMock()
    response.json.return_value = payload
    if status >= 400:
        response.raise_for_status.side_effect = requests.HTTPError(str(status))
    return response


@pytest.mark.parametrize("url", ["", "gliner:8000", "file:///etc/passwd", "ftp://host"])
def test_service_client_rejects_invalid_urls(url):
    with pytest.raises(ValueError):
        GlinerServiceClient(url)


def test_service_client_sends_token_and_timeout():
    session = MagicMock()
    session.headers = {}
    session.request.return_value = _response(INFO)
    client = GlinerServiceClient("http://gliner:8000", token="t0k", timeout=12, session=session)

    assert client.info() == INFO
    assert session.headers["Authorization"] == "Bearer t0k"
    session.request.assert_called_once_with("GET", "http://gliner:8000/info", timeout=12)


def test_service_client_validates_extract_result_count():
    session = MagicMock()
    session.headers = {}
    session.request.return_value = _response({"fingerprint": "x", "results": [{}]})
    client = GlinerServiceClient("http://gliner:8000/", session=session)

    with pytest.raises(GlinerServiceError):
        client.extract(["a", "b"])
    method, url = session.request.call_args.args
    assert (method, url) == ("POST", "http://gliner:8000/extract")
    assert session.request.call_args.kwargs["json"] == {"texts": ["a", "b"]}


def test_service_client_rejects_invalid_info():
    session = MagicMock()
    session.headers = {}
    session.request.return_value = _response({"entities": []})
    with pytest.raises(GlinerServiceError):
        GlinerServiceClient("http://gliner:8000", session=session).info()


def test_service_client_propagates_http_errors():
    session = MagicMock()
    session.headers = {}
    session.request.return_value = _response({}, status=503)
    with pytest.raises(requests.HTTPError):
        GlinerServiceClient("http://gliner:8000", session=session).info()


# Indexer ---------------------------------------------------------------------


def test_indexer_uses_upsert_and_stores_text_hash():
    actions = list(Indexer._to_bulk_actions([{"id": "10", "texto": "<p>Olá   mundo</p>"}]))

    assert actions == [
        {
            "_op_type": "update",
            "_index": "dou",
            "_id": "10",
            "doc": {
                "id": "10",
                "texto": "<p>Olá   mundo</p>",
                "texto_plain": "Olá mundo",
                "texto_plain_hash": text_hash("Olá mundo"),
            },
            "doc_as_upsert": True,
        }
    ]


def _indexer_with(client):
    indexer = Indexer.__new__(Indexer)
    indexer.client = client
    return indexer


def test_ensure_index_creates_index_with_text_hash_mapping():
    client = MagicMock()
    client.indices.exists.return_value = False

    _indexer_with(client)._ensure_index()

    body = client.indices.create.call_args.kwargs["body"]
    assert body["mappings"]["properties"]["texto_plain_hash"] == {"type": "keyword"}
    client.indices.put_mapping.assert_not_called()


def test_ensure_index_adds_text_hash_mapping_to_existing_index():
    client = MagicMock()
    client.indices.exists.return_value = True

    _indexer_with(client)._ensure_index()

    client.indices.create.assert_not_called()
    client.indices.put_mapping.assert_called_once_with(index="dou", body=TEXT_HASH_MAPPING)
