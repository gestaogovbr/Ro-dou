from __future__ import annotations

from datetime import date, datetime

import rodou_chatbot.search as search_module
from rodou_chatbot.config import SearchConfig
from rodou_chatbot.models import SearchIntent
from rodou_chatbot.search import PublicationSearchService


def test_postgres_query_uses_structured_filters_and_parameters() -> None:
    intent = SearchIntent(
        terms=["dengue"],
        excluded_terms=["licitação"],
        organizations=["Ministério da Saúde"],
        sections=["DO1"],
        date_from=date(2026, 9, 16),
        date_to=date(2026, 9, 16),
    )

    where, params = PublicationSearchService.build_postgres_where(intent)

    assert "plainto_tsquery" in where
    assert "NOT ILIKE %(excluded_0)s" in where
    assert "artcategory" in where
    assert "pubname = ANY(%(sections)s)" in where
    assert params["query_0"] == "dengue"
    assert params["excluded_0"] == "%licitação%"
    assert params["date_from"] == date(2026, 9, 16)


def test_exact_search_uses_phrase_contains_semantics() -> None:
    where, params = PublicationSearchService.build_postgres_where(
        SearchIntent(terms=["inteligência artificial"], exact_search=True)
    )

    assert "ILIKE %(term_0)s" in where
    assert params["term_0"] == "%inteligência artificial%"


def test_like_wildcards_are_escaped() -> None:
    where, params = PublicationSearchService.build_postgres_where(
        SearchIntent(
            terms=["100%_efetivo"],
            excluded_terms=["50%"],
            exact_search=True,
        )
    )

    assert "ESCAPE" in where
    assert params["term_0"] == r"%100\%\_efetivo%"
    assert params["excluded_0"] == r"%50\%%"


def test_opensearch_dsl_is_built_only_inside_search_service() -> None:
    body = PublicationSearchService.build_opensearch_query(
        SearchIntent(
            terms=["dengue"],
            excluded_terms=["licitação"],
            organizations=["ANVISA"],
            exact_search=True,
            limit=7,
        )
    )

    assert body["size"] == 7
    assert body["query"]["bool"]["must"][0]["multi_match"]["type"] == "phrase"
    assert body["query"]["bool"]["must_not"]
    organization_filter = body["query"]["bool"]["filter"][0]["bool"]
    assert {
        "match_phrase": {
            "artcategory": "Agência Nacional de Vigilância Sanitária"
        }
    } in organization_filter["should"]
    assert organization_filter["minimum_should_match"] == 1
    assert body["highlight"]["fields"]["texto_plain"]["number_of_fragments"] == 1


def test_multiple_organizations_use_or_semantics() -> None:
    intent = SearchIntent(organizations=["ANVISA", "Ministério da Saúde"])

    where, _ = PublicationSearchService.build_postgres_where(intent)
    body = PublicationSearchService.build_opensearch_query(intent)

    assert " OR " in where
    assert len(body["query"]["bool"]["filter"][0]["bool"]["should"]) == 2


def test_known_organization_aliases_are_expanded_by_backend() -> None:
    intent = SearchIntent(organizations=["MGI", "ANVISA"])

    _, params = PublicationSearchService.build_postgres_where(intent)
    body = PublicationSearchService.build_opensearch_query(intent)
    phrases = body["query"]["bool"]["filter"][0]["bool"]["should"]

    assert "%ministerio%" in params.values()
    assert "%gestao%" in params.values()
    assert "%agencia%" in params.values()
    assert {
        "match_phrase": {
            "artcategory": "Ministério da Gestão e da Inovação em Serviços Públicos"
        }
    } in phrases


def test_opensearch_maps_text_field_to_indexed_plain_text() -> None:
    body = PublicationSearchService.build_opensearch_query(
        SearchIntent(terms=["portaria"], field="texto")
    )

    assert body["query"]["bool"]["must"][0]["multi_match"]["fields"] == [
        "texto_plain"
    ]


def test_opensearch_section_uses_keyword_mapping_directly() -> None:
    body = PublicationSearchService.build_opensearch_query(
        SearchIntent(terms=["portaria"], sections=["DO1"])
    )

    assert {"terms": {"pubname": ["DO1"]}} in body["query"]["bool"]["filter"]


def test_service_caps_result_limit() -> None:
    service = PublicationSearchService(SearchConfig(), max_results=5)
    captured: dict[str, int] = {}

    def fake_search(intent: SearchIntent):
        captured["limit"] = intent.limit
        from rodou_chatbot.models import SearchResult

        return SearchResult()

    service._search_postgres = fake_search  # type: ignore[method-assign]
    service.search(SearchIntent(terms=["dengue"], limit=20))

    assert captured["limit"] == 5


def test_service_forces_current_day_for_every_search(monkeypatch) -> None:
    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 9, 16, tzinfo=tz)

    monkeypatch.setattr(search_module, "datetime", FrozenDatetime)
    captured: list[tuple[date | None, date | None]] = []
    returned_results = []

    def fake_search(intent: SearchIntent):
        captured.append((intent.date_from, intent.date_to))
        from rodou_chatbot.models import SearchResult

        return SearchResult()

    for source in ("postgres", "opensearch"):
        service = PublicationSearchService(SearchConfig(source=source), max_results=5)
        if source == "postgres":
            service._search_postgres = fake_search  # type: ignore[method-assign]
        else:
            service._search_opensearch = fake_search  # type: ignore[method-assign]
        returned_results.append(
            service.search(
                SearchIntent(
                    terms=["dengue"],
                    date_from=date(2020, 1, 1),
                    date_to=date(2020, 1, 31),
                )
            )
        )

    assert captured == [
        (date(2026, 9, 16), date(2026, 9, 16)),
        (date(2026, 9, 16), date(2026, 9, 16)),
    ]
    assert all(result.effective_date == date(2026, 9, 16) for result in returned_results)
    assert all(
        result.message == "Não há publicações no dia de hoje para os filtros informados."
        for result in returned_results
    )


def test_publication_prefers_ementa_over_body_excerpt() -> None:
    publication = PublicationSearchService._publication_from_source(
        {
            "id": 1,
            "ementa": "Resumo oficial da publicação.",
            "texto": "Corpo longo com o termo dengue.",
        },
        bounded_terms=["dengue"],
    )

    assert publication.content == "Resumo oficial da publicação."
    assert publication.content_type == "ementa"


def test_publication_excerpt_is_centered_on_searched_term() -> None:
    body = "início " + ("x" * 600) + " Ministério da Saúde " + ("y" * 600)

    publication = PublicationSearchService._publication_from_source(
        {"id": 1, "ementa": None, "texto": body},
        bounded_terms=["Ministerio da Saude"],
    )

    assert publication.content_type == "excerpt"
    assert "Ministério da Saúde" in publication.content
    assert publication.content.startswith("(...) ")
    assert publication.content.endswith(" (...)")
    assert "início" not in publication.content


def test_publication_uses_opensearch_highlight_as_excerpt() -> None:
    publication = PublicationSearchService._publication_from_source(
        {
            "id": 1,
            "ementa": "None",
            "texto_plain": "texto que não deve ser usado",
            "opensearch_highlights": [
                "contexto da publicação com <em>servidores</em> federais"
            ],
        },
        bounded_terms=["servidor"],
    )

    assert publication.content_type == "excerpt"
    assert publication.content == "contexto da publicação com servidores federais"


def test_publication_uses_postgres_headline_for_inflected_term() -> None:
    publication = PublicationSearchService._publication_from_source(
        {
            "id": 1,
            "texto": "começo " + ("irrelevante " * 200),
            "postgres_excerpt": (
                "trecho selecionado pelo banco sobre o <mark>servidor</mark> federal"
            ),
        },
        bounded_terms=["servidores"],
    )

    assert publication.content_type == "excerpt"
    assert publication.content == (
        "trecho selecionado pelo banco sobre o servidor federal"
    )
