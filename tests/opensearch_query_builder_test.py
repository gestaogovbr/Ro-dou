import pytest

from dags.ro_dou_src.utils.open_search.query_builder import OpenSearchQueryBuilder


@pytest.fixture
def query_builder() -> OpenSearchQueryBuilder:
    """Return a fresh OpenSearch query builder for each test."""
    return OpenSearchQueryBuilder()


def _texto_clause(query_body):
    """Return the first text clause from a generated query body."""
    return query_body["query"]["bool"]["must"][0]


def _collect_names(clause):
    """Collect all OpenSearch ``_name`` values from a nested clause."""
    names = []
    if isinstance(clause, dict):
        for key, value in clause.items():
            if key in {"match", "match_phrase"}:
                for field_query in value.values():
                    names.append(field_query["_name"])
            else:
                names.extend(_collect_names(value))
    elif isinstance(clause, list):
        for item in clause:
            names.extend(_collect_names(item))
    return names


def test_build_keeps_non_text_filters(query_builder):
    """Keep existing filter behavior while adding highlight to the query."""
    query_builder.payload = {
        "pubname": ["DO1"],
        "arttype": ["Portaria", "Resolução"],
        "pubdate": ["2024-04-01", "2024-04-02"],
    }

    assert query_builder.build() == {
        "query": {
            "bool": {
                "filter": [
                    {
                        "range": {
                            "pubdate": {
                                "gte": "2024-04-01",
                                "lte": "2024-04-02",
                            }
                        }
                    }
                ],
                "must": [
                    {"match_phrase": {"pubname": "DO1"}},
                    {
                        "bool": {
                            "should": [
                                {"match_phrase": {"arttype": "Portaria"}},
                                {"match_phrase": {"arttype": "Resolução"}},
                            ],
                            "minimum_should_match": 1,
                        }
                    },
                ],
            }
        },
        "highlight": {
            "pre_tags": ["<%%>"],
            "post_tags": ["</%%>"],
            "fields": {"texto_plain": {}},
        },
        "size": 200,
        "sort": [{"_score": "desc"}],
    }


def test_build_simple_text_query_uses_named_match_with_and_operator(query_builder):
    """Build unquoted multi-word text as a named ``match`` clause."""
    query_builder.payload = {
        "texto": ["estrutura regimental"],
        "pubdate": ["2024-04-01"],
    }

    assert _texto_clause(query_builder.build()) == {
        "match": {
            "texto_plain": {
                "query": "estrutura regimental",
                "_name": "estrutura regimental",
                "operator": "and",
            }
        }
    }


def test_build_morphological_text_query_delegates_variations_to_opensearch(
    query_builder,
):
    """Allow OpenSearch analyzer to match plural variants of a singular term."""
    query_builder.payload = {
        "texto": ["Estrutura regimental"],
        "pubdate": ["2026-06-22"],
    }

    text_clause = _texto_clause(query_builder.build())

    assert "match_phrase" not in text_clause
    assert text_clause == {
        "match": {
            "texto_plain": {
                "query": "Estrutura regimental",
                "_name": "Estrutura regimental",
                "operator": "and",
            }
        }
    }


def test_build_and_query_uses_named_must_clauses(query_builder):
    """Build AND expressions as named ``must`` clauses."""
    query_builder.payload = {
        "texto": ["Resolução AND SEGES"],
        "pubdate": ["2024-04-01"],
    }

    assert _texto_clause(query_builder.build()) == {
        "bool": {
            "must": [
                {"match": {"texto_plain": {"query": "Resolução", "_name": "Resolução"}}},
                {"match": {"texto_plain": {"query": "SEGES", "_name": "SEGES"}}},
            ]
        }
    }


def test_build_or_query_uses_should_with_minimum_match(query_builder):
    """Build OR expressions as named ``should`` clauses."""
    query_builder.payload = {
        "texto": ["Resolução OR SEGES"],
        "pubdate": ["2024-04-01"],
    }

    assert _texto_clause(query_builder.build()) == {
        "bool": {
            "should": [
                {"match": {"texto_plain": {"query": "Resolução", "_name": "Resolução"}}},
                {"match": {"texto_plain": {"query": "SEGES", "_name": "SEGES"}}},
            ],
            "minimum_should_match": 1,
        }
    }


def test_build_not_query_uses_must_not(query_builder):
    """Build NOT expressions as named ``must_not`` clauses."""
    query_builder.payload = {
        "texto": ["Resolução AND NOT SEGES"],
        "pubdate": ["2024-04-01"],
    }

    assert _texto_clause(query_builder.build()) == {
        "bool": {
            "must": [
                {"match": {"texto_plain": {"query": "Resolução", "_name": "Resolução"}}},
            ],
            "must_not": [
                {"match": {"texto_plain": {"query": "SEGES", "_name": "SEGES"}}},
            ],
        }
    }


def test_build_quoted_phrase_preserves_single_named_term(query_builder):
    """Preserve quoted phrases as one named term."""
    query_builder.payload = {
        "texto": ['"estrutura regimental" AND SEGES'],
        "pubdate": ["2024-04-01"],
    }

    assert _texto_clause(query_builder.build()) == {
        "bool": {
            "must": [
                {
                    "match_phrase": {
                        "texto_plain": {
                            "query": "estrutura regimental",
                            "_name": "estrutura regimental",
                        }
                    }
                },
                {"match": {"texto_plain": {"query": "SEGES", "_name": "SEGES"}}},
            ]
        }
    }


def test_build_terms_ignore_uses_match_phrase(query_builder):
    """Exclude ignored terms as exact phrases, not broad query strings."""
    query_builder.payload = {
        "texto": ["Estrutura regimental"],
        "terms_ignore": ["Programa de Gestão de Desempenho"],
        "pubdate": ["2024-04-01"],
    }

    assert query_builder.build()["query"]["bool"]["must_not"] == [
        {"match_phrase": {"texto_plain": "Programa de Gestão de Desempenho"}}
    ]


def test_build_parentheses_preserve_boolean_precedence(query_builder):
    """Preserve parentheses and boolean precedence in generated clauses."""
    query_builder.payload = {
        "texto": ["(Resolução OR Portaria) AND NOT SEGES"],
        "pubdate": ["2024-04-01"],
    }

    assert _texto_clause(query_builder.build()) == {
        "bool": {
            "must": [
                {
                    "bool": {
                        "should": [
                            {
                                "match": {
                                    "texto_plain": {
                                        "query": "Resolução",
                                        "_name": "Resolução",
                                    }
                                }
                            },
                            {
                                "match": {
                                    "texto_plain": {
                                        "query": "Portaria",
                                        "_name": "Portaria",
                                    }
                                }
                            },
                        ],
                        "minimum_should_match": 1,
                    }
                },
            ],
            "must_not": [
                {"match": {"texto_plain": {"query": "SEGES", "_name": "SEGES"}}},
            ],
        }
    }


def test_all_final_text_terms_receive_name(query_builder):
    """Ensure every final text term receives an OpenSearch ``_name``."""
    query_builder.payload = {
        "texto": ['"estrutura regimental" AND (Resolução OR SEGES) AND NOT revogado'],
        "pubdate": ["2024-04-01"],
    }

    assert sorted(_collect_names(_texto_clause(query_builder.build())), key=str.lower) == [
        "estrutura regimental",
        "Resolução",
        "revogado",
        "SEGES",
    ]
