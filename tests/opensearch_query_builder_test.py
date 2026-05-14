import pytest

from dags.ro_dou_src.utils.open_search.query_builder import OpenSearchQueryBuilder


@pytest.fixture
def query_builder() -> OpenSearchQueryBuilder:
    return OpenSearchQueryBuilder()


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
                                        {"match_phrase": {"texto_plain": "term1 & term2 ! term3"}},
                                        {"match_phrase": {"texto_plain": "term4 & term5"}},
                                    ],
                                    "minimum_should_match": 1,
                                }
                            },
                            {"match_phrase": {"pubname": "DO1"}},
                        ],
                    }
                },
                "size": 10000,
                "sort": [{"_score": "desc"}],
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
                "sort": [{"_score": "desc"}],
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
                                        {"match_phrase": {"texto_plain": "term1"}},
                                        {"match_phrase": {"texto_plain": "term2"}},
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
                "sort": [{"_score": "desc"}],
            },
        ),
    ],
)
def test_build(query_builder, data_in, query_out):
    query_builder.payload = data_in
    assert query_builder.build() == query_out
