import pytest

from dags.ro_dou_src.utils.open_search.query_builder import OpenSearchQueryBuilder


@pytest.fixture
def query_builder() -> OpenSearchQueryBuilder:
    return OpenSearchQueryBuilder()


@pytest.mark.parametrize(
    "term_in, qs_out",
    [
        ("term1", '"term1"'),
        ("term1 & term2", '"term1" AND "term2"'),
        ("term1 | term2", '"term1" OR "term2"'),
        ("term1 & term2 ! term3", '"term1" AND "term2" AND NOT "term3"'),
        ("term1 & ( term2 | term3 )", '"term1" AND ( "term2" OR "term3" )'),
    ],
)
def test_term_to_opensearch_qs(query_builder, term_in, qs_out):
    assert query_builder._term_to_opensearch_qs(term_in) == qs_out


@pytest.mark.parametrize(
    "data_in, query_out",
    [
        (
            {
                "texto": ["term1 & term2 ! term3", "term4 & term5"],
                "pubname": ["DO1"],
                "pubdate": ["2024-04-01", "2024-04-02"],
            },
            {
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
                            {
                                "bool": {
                                    "should": [
                                        {
                                            "query_string": {
                                                "query": '"term1" AND "term2" AND NOT "term3"',
                                                "default_field": "texto_plain",
                                            }
                                        },
                                        {
                                            "query_string": {
                                                "query": '"term4" AND "term5"',
                                                "default_field": "texto_plain",
                                            }
                                        },
                                    ],
                                    "minimum_should_match": 1,
                                }
                            },
                            {"match_phrase": {"pubname": "DO1"}},
                        ],
                    }
                },
                "size": 10000,
            },
        ),
        (
            {
                "pubname": ["DO1"],
                "arttype": ["Portaria", "Resolução"],
                "pubdate": ["2024-04-01", "2024-04-02"],
            },
            {
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
                "size": 10000,
            },
        ),
        (
            {
                "texto": ["term1", "term2"],
                "pubname": ["DO1"],
                "pubdate": ["2024-04-01", "2024-04-02"],
                "artcategory": ["Ministério da Defesa"],
                "artcategory_ignore": ["Ministério da Defesa/Comando da Marinha"],
            },
            {
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
                            {
                                "bool": {
                                    "should": [
                                        {
                                            "query_string": {
                                                "query": '"term1"',
                                                "default_field": "texto_plain",
                                            }
                                        },
                                        {
                                            "query_string": {
                                                "query": '"term2"',
                                                "default_field": "texto_plain",
                                            }
                                        },
                                    ],
                                    "minimum_should_match": 1,
                                }
                            },
                            {"match_phrase": {"pubname": "DO1"}},
                            {"match_phrase": {"artcategory": "Ministério da Defesa"}},
                        ],
                        "must_not": [
                            {
                                "match_phrase_prefix": {
                                    "artcategory": "Ministério da Defesa/Comando da Marinha"
                                }
                            },
                        ],
                    }
                },
                "size": 10000,
            },
        ),
    ],
)
def test_build(query_builder, data_in, query_out):
    query_builder.payload = data_in
    assert query_builder.build() == query_out
