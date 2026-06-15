from __future__ import annotations

from rodou_mcp.server.services.search import DouSearchService
from rodou_mcp.server.settings import Settings


class FakeOpenSearch:
    def search(self, index: str, body: dict) -> dict:
        assert index == "dou"
        assert body["size"] == 3
        return {
            "hits": {
                "total": {"value": 1},
                "hits": [
                    {
                        "_id": "123",
                        "_score": 2.5,
                        "_source": {
                            "id": "123",
                            "titulo": "Portaria",
                            "pubdate": "2026-06-15",
                            "pubname": "DO1",
                            "texto_plain": "Texto indexado",
                        },
                    }
                ],
            }
        }


def test_search_maps_opensearch_hits(monkeypatch) -> None:
    settings = Settings(OPENSEARCH_HOST="http://opensearch:9200", ENABLE_OPENSEARCH=True)
    service = DouSearchService(settings=settings)
    monkeypatch.setattr(service, "_client", FakeOpenSearch())

    result = service.search(
        query="portaria",
        date_from="2026-06-15",
        date_to="2026-06-15",
        pubname=["DO1"],
        size=3,
    )

    assert result.total == 1
    assert result.items[0].id == "123"
    assert result.items[0].title == "Portaria"


def test_postgres_where_includes_optional_filters() -> None:
    where, params = DouSearchService._build_postgres_where(
        query="licitação",
        date_from="2026-06-01",
        date_to="2026-06-15",
        pubname=["DO1"],
    )

    assert "ILIKE %(pattern)s" in where
    assert "pubdate::date >= %(date_from)s" in where
    assert "pubdate::date <= %(date_to)s" in where
    assert "pubname = ANY(%(pubname)s)" in where
    assert params == {
        "query": "licitação",
        "pattern": "%licitação%",
        "date_from": "2026-06-01",
        "date_to": "2026-06-15",
        "pubname": ["DO1"],
    }
