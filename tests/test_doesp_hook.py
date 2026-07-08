import json
from datetime import datetime

import pytest

from utils.search_domains import SectionDOESP
from hooks.doesp_hook import DOESPHook


class FakeResponse:
    def __init__(self, json_obj=None, text="", status=200):
        self._json = json_obj
        self.text = text
        self.status_code = status

    def json(self):
        if self._json is None:
            raise ValueError("No JSON")
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


def test_doesp_search_builds_query_and_parses(monkeypatch):
    # Prepare fake journals response
    journals = {
        "count": 5,
        "items": [
            {"id": "JID-EXECUTIVO", "name": "Executivo", "sequence": 1},
        ],
    }

    # Prepare fake publications response
    publication_item = {
        "id": "pub-1",
        "title": "Teste Publicacao",
        "url": "/publicacao/1",
        "snippet": "Conteúdo de teste",
        "date": "2026-05-19",
        "journalName": "Executivo",
    }

    publications = {"items": [publication_item]}

    captured = {"calls": []}

    def fake_get(url, params=None, headers=None, timeout=None):
        captured["calls"].append((url, params))
        if url.endswith("/v2/journals"):
            return FakeResponse(json_obj=journals)
        if url.endswith("/v2/advanced-search/publications"):
            return FakeResponse(json_obj=publications)
        # default
        return FakeResponse(json_obj={})

    # Patch requests.get used in the module
    monkeypatch.setattr('hooks.doesp_hook.requests.get', fake_get)

    h = DOESPHook()
    # Run search
    results = h.search_text("unicamp", sections=["Executivo"], reference_date=datetime(2026,5,19))

    # Assert journals fetch then publications fetch
    assert len(captured["calls"]) >= 2
    journals_call = captured["calls"][0]
    pubs_call = captured["calls"][1]

    assert pubs_call[0].endswith('/v2/advanced-search/publications')
    params = pubs_call[1]
    # Terms[0] must be present
    assert params.get('Terms[0]') == 'unicamp'
    # JournalId must be the mapped id
    assert params.get('JournalId') == 'JID-EXECUTIVO'

    # Check parsing
    assert isinstance(results, list)
    assert len(results) == 1
    item = results[0]
    assert item['id'] == 'pub-1'
    assert 'Teste Publicacao' in (item['title'] or '')
    # date formatted as dd/mm/YYYY
    assert item['date'] == '19/05/2026'


def test_multi_terms_and_optional_ids(monkeypatch):
    journals = {"count": 0, "items": []}
    publication_item = {"id": "p2", "title": "P2", "url": "/p/2", "snippet": "x", "date": "2026-05-19"}
    publications = {"items": [publication_item]}
    captured = {"calls": []}

    def fake_get(url, params=None, headers=None, timeout=None):
        captured["calls"].append((url, params))
        if url.endswith('/v2/journals'):
            return FakeResponse(json_obj=journals)
        if url.endswith('/v2/advanced-search/publications'):
            return FakeResponse(json_obj=publications)
        return FakeResponse(json_obj={})

    monkeypatch.setattr('hooks.doesp_hook.requests.get', fake_get)

    h = DOESPHook()
    # pass two terms and explicit SectionId and PublicationTypeId via sections list
    results = h.search_text(['unicamp', 'edital'], sections=[{'SectionId':'SEC-1'}, {'PublicationTypeId':'PT-1'}], reference_date=datetime(2026,5,19))

    assert len(captured['calls']) >= 2
    pubs_call = captured['calls'][1]
    params = pubs_call[1]
    assert params.get('Terms[0]') == 'unicamp'
    assert params.get('Terms[1]') == 'edital'
    # our sections dicts should have been propagated
    assert params.get('SectionId') == 'SEC-1'
    assert params.get('PublicationTypeId') == 'PT-1'
    # JournalId should not be present since journals list was empty
    assert params.get('JournalId') is None

    assert isinstance(results, list)
    assert len(results) == 1
    assert results[0]['id'] == 'p2'
