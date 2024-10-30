"""INLABS Seracher unit tests
"""

from datetime import datetime
from collections import Counter
import pytest


@pytest.mark.parametrize(
    "search_terms, sections, department, pubtype, reference_date, search_date, filters_applyed",
    [
        (
            {"texto": ["a", "b"]},
            ["SECAO_2"],
            ["Ministério"],
            ["Edital"],
            datetime.now(),
            "DIA",
            {
                "texto": ["a", "b"],
                "pubname": ["DO2"],
                "artcategory": ["Ministério"],
                "arttype": ["Edital"],
                "pubdate": [
                    datetime.now().strftime("%Y-%m-%d"),
                    datetime.now().strftime("%Y-%m-%d"),
                ],
            },
        ),
    ],
)
def test_apply_filters(
    inlabs_searcher,
    search_terms,
    sections,
    department,
    pubtype,
    reference_date,
    search_date,
    filters_applyed,
):
    assert (
        inlabs_searcher._apply_filters(
            search_terms, sections, department, pubtype, reference_date, search_date
        )
        == filters_applyed
    )


@pytest.mark.parametrize(
    "terms, search_terms",
    [
        (["a", "b", "c"], {"texto": ["a", "b", "c"]}),
        (
            '{"termo": {"0": "Pessoa 0","1": "Pessoa 1"}, "termo_group": {"0": "Grupo 1","1": "Grupo 2"}}',
            {"texto": ["Pessoa 0", "Pessoa 1"]},
        ),
    ],
)
def test_prepare_search_terms(inlabs_searcher, terms, search_terms):
    search_terms_return = inlabs_searcher._prepare_search_terms(terms)
    assert set(search_terms_return.keys()) == set(
        search_terms.keys()
    ), "The dictionaries do not have the same keys."

    for key in search_terms_return:
        assert Counter(search_terms_return[key]) == Counter(
            search_terms[key]
        ), f"The lists under the key '{key}' do not have the same content."


@pytest.mark.parametrize(
    "raw_sections, parsed_sections",
    [
        (["SECAO_1"], ["DO1"]),
        (["SECAO_2"], ["DO2"]),
        (["SECAO_3"], ["DO3"]),
        (["SECAO_1", "EDICAO_EXTRA"], ["DO1", "DO1E"]),
        (
            ["SECAO_2", "EDICAO_EXTRA_1A", "EDICAO_EXTRA_2B", "EDICAO_EXTRA_3D"],
            ["DO2", "DO1E", "DO2E", "DO3E"],
        ),
    ],
)
def test_parse_sections(inlabs_searcher, raw_sections, parsed_sections):
    assert sorted(inlabs_searcher._parse_sections(raw_sections)) == sorted(
        parsed_sections
    )


@pytest.mark.parametrize(
    "sql_terms, sql_splitted_terms",
    [
        (  # sql_terms
            {
                "termo": {
                    "0": "Pessoa 0",
                    "1": "Pessoa 1",
                    "2": "Pessoa 2",
                    "3": "Pessoa 3",
                    "4": "Pessoa 4",
                    "5": "Pessoa 5",
                    "6": "Pessoa 6",
                    "7": "Pessoa 7",
                    "8": "Pessoa 8",
                    "9": "Pessoa 9",
                    "10": "Pessoa 10",
                },
                "termo_group": {
                    "0": "Grupo 1",
                    "1": "Grupo 2",
                    "2": "Grupo 2",
                    "3": "Grupo 1",
                    "4": "Grupo 3",
                    "5": "Grupo 2",
                    "6": "Grupo 1",
                    "7": "Grupo 1",
                    "8": "Grupo 1",
                    "9": "Grupo 2",
                    "10": "Grupo 1",
                },
            },
            # sql_splitted_terms
            [
                "Pessoa 0",
                "Pessoa 1",
                "Pessoa 2",
                "Pessoa 3",
                "Pessoa 4",
                "Pessoa 5",
                "Pessoa 6",
                "Pessoa 7",
                "Pessoa 8",
                "Pessoa 9",
                "Pessoa 10",
            ],
        ),
    ],
)
def test_split_sql_terms(inlabs_searcher, sql_terms, sql_splitted_terms):
    assert sorted(inlabs_searcher._split_sql_terms(sql_terms)) == sorted(
        sql_splitted_terms
    )
