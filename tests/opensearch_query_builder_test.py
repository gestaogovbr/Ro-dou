from unittest.mock import patch

import pytest

from dags.ro_dou_src.utils.open_search.query_builder import OpenSearchQueryBuilder
from dags.ro_dou_src.utils.open_search.config import NEURAL_SEARCH_MIN_SCORE


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


def test_build_simple_text_query_uses_named_match_phrase(query_builder):
    """Build unquoted multi-word text as a named ``match_phrase`` clause."""
    query_builder.payload = {
        "texto": ["estrutura regimental"],
        "pubdate": ["2024-04-01"],
    }

    assert _texto_clause(query_builder.build()) == {
        "match_phrase": {
            "texto_plain": {
                "query": "estrutura regimental",
                "_name": "estrutura regimental",
            }
        }
    }


def test_build_morphological_text_query_uses_phrase_query(
    query_builder,
):
    """Keep multi-word text terms together when delegating to OpenSearch."""
    query_builder.payload = {
        "texto": ["Estrutura regimental"],
        "pubdate": ["2026-06-22"],
    }

    text_clause = _texto_clause(query_builder.build())

    assert text_clause == {
        "match_phrase": {
            "texto_plain": {
                "query": "Estrutura regimental",
                "_name": "Estrutura regimental",
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


def test_build_unquoted_phrase_inside_boolean_expression(query_builder):
    """Keep multi-word terms as phrases inside boolean expressions."""
    query_builder.payload = {
        "texto": ["Unidade regional AND SEGES"],
        "pubdate": ["2026-06-25"],
    }

    assert _texto_clause(query_builder.build()) == {
        "bool": {
            "must": [
                {
                    "match_phrase": {
                        "texto_plain": {
                            "query": "Unidade regional",
                            "_name": "Unidade regional",
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


def test_build_neural_search_disabled_by_default(query_builder):
    """Without ``neural_search``, no vector clause is added."""
    query_builder.payload = {
        "texto": ["estrutura regimental"],
        "pubdate": ["2024-04-01"],
    }

    with patch(
        "dags.ro_dou_src.utils.open_search.query_builder.embed_query"
    ) as mock_embed_query:
        query_body = query_builder.build()

    mock_embed_query.assert_not_called()
    assert "knn" not in _texto_clause(query_body)


def test_build_neural_search_combines_text_and_knn(query_builder):
    """Hybrid mode ORs the keyword clause with a k-NN clause per term."""
    query_builder.payload = {
        "texto": ["estrutura regimental"],
        "pubdate": ["2024-04-01"],
        "neural_search": True,
    }

    with patch(
        "dags.ro_dou_src.utils.open_search.query_builder.embed_query",
        return_value=[0.1, 0.2, 0.3],
    ) as mock_embed_query:
        query_body = query_builder.build()

    mock_embed_query.assert_called_once_with("estrutura regimental")

    clause = _texto_clause(query_body)
    assert clause["bool"]["minimum_should_match"] == 1
    should = clause["bool"]["should"]
    assert {
        "match_phrase": {
            "texto_plain": {
                "query": "estrutura regimental",
                "_name": "estrutura regimental",
            }
        }
    } in should
    knn_clauses = [c for c in should if "knn" in c]
    assert len(knn_clauses) == 1
    knn = knn_clauses[0]["knn"]["embedding"]
    assert knn["vector"] == [0.1, 0.2, 0.3]
    assert knn["min_score"] == NEURAL_SEARCH_MIN_SCORE
    # No "filter" here: combined with min_score it triggers an upstream
    # OpenSearch k-NN bug (opensearch-project/k-NN#2836). Correctness is
    # preserved by the outer bool query's filter/must clauses instead.
    assert "filter" not in knn


def test_build_neural_search_uses_dis_max_across_terms(query_builder):
    """Multiple texto terms' semantic clauses combine via dis_max, not sum.

    Near-synonym terms (e.g. "IA" and "machine learning") tend to score
    similarly against the same document; summing every matching term's knn
    score via a plain bool "should" would inflate the total for documents
    only moderately related to the general topic. dis_max keeps just the
    best-matching term's score instead.
    """
    query_builder.payload = {
        "texto": ["inteligência artificial", "machine learning"],
        "pubdate": ["2024-04-01"],
        "neural_search": True,
    }

    with patch(
        "dags.ro_dou_src.utils.open_search.query_builder.embed_query",
        side_effect=[[0.1, 0.2], [0.3, 0.4]],
    ):
        query_body = query_builder.build()

    clause = _texto_clause(query_body)
    should = clause["bool"]["should"]

    text_result = next(c for c in should if "bool" in c)
    text_names = _collect_names(text_result)
    assert set(text_names) == {"inteligência artificial", "machine learning"}

    semantic_result = next(c for c in should if "dis_max" in c)
    dis_max_queries = semantic_result["dis_max"]["queries"]
    assert semantic_result["dis_max"]["tie_breaker"] == 0.0
    assert [q["knn"]["embedding"]["vector"] for q in dis_max_queries] == [
        [0.1, 0.2],
        [0.3, 0.4],
    ]


def test_build_neural_search_still_scoped_by_outer_filters(query_builder):
    """Non-text filters like ``pubname`` still apply via the outer bool query."""
    query_builder.payload = {
        "texto": ["estrutura regimental"],
        "pubname": ["DO1"],
        "pubdate": ["2024-04-01"],
        "neural_search": True,
    }

    with patch(
        "dags.ro_dou_src.utils.open_search.query_builder.embed_query",
        return_value=[0.1, 0.2, 0.3],
    ):
        query_body = query_builder.build()

    bool_query = query_body["query"]["bool"]
    assert {"range": {"pubdate": {"gte": "2024-04-01", "lte": "2024-04-01"}}} in bool_query[
        "filter"
    ]
    assert {"match_phrase": {"pubname": "DO1"}} in bool_query["must"]


def test_build_neural_search_extracts_plain_terms_for_boolean_expression(query_builder):
    """Boolean operators are stripped before computing the query embedding."""
    query_builder.payload = {
        "texto": ["Resolução AND SEGES"],
        "pubdate": ["2024-04-01"],
        "neural_search": True,
    }

    with patch(
        "dags.ro_dou_src.utils.open_search.query_builder.embed_query",
        return_value=[0.1, 0.2, 0.3],
    ) as mock_embed_query:
        query_builder.build()

    mock_embed_query.assert_called_once_with("Resolução SEGES")


def test_build_neural_search_falls_back_to_keyword_on_embedding_failure(query_builder):
    """A failing embedding model degrades to keyword-only matching."""
    query_builder.payload = {
        "texto": ["estrutura regimental"],
        "pubdate": ["2024-04-01"],
        "neural_search": True,
    }

    with patch(
        "dags.ro_dou_src.utils.open_search.query_builder.embed_query",
        side_effect=RuntimeError("model unavailable"),
    ):
        query_body = query_builder.build()

    assert _texto_clause(query_body) == {
        "match_phrase": {
            "texto_plain": {
                "query": "estrutura regimental",
                "_name": "estrutura regimental",
            }
        }
    }
