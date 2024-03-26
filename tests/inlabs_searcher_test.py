"""INLABS Seracher unit tests
"""

import pytest


@pytest.mark.parametrize(
    "raw_sections, parsed_sections",
    [
        (["SECAO_1"], ["1"]),
        (["SECAO_2"], ["2"]),
        (["SECAO_3"], ["3"]),
        (["SECAO_1", "EDICAO_EXTRA"], ["1", "E"]),
        (
            ["SECAO_2", "EDICAO_EXTRA_1A", "EDICAO_EXTRA_2B", "EDICAO_EXTRA_3D"],
            ["2", "1E", "2E", "3E"],
        ),
    ],
)
def test_parse_sections(inlabs_searcher, raw_sections, parsed_sections):
    assert inlabs_searcher._parse_sections(raw_sections) == parsed_sections


@pytest.mark.parametrize(
    "sql_terms, sql_splitted_terms",
    [
        (   # sql_terms
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
            ]
        ),
    ],
)
def test_split_sql_terms(inlabs_searcher, sql_terms, sql_splitted_terms):
    assert inlabs_searcher._split_sql_terms(sql_terms) == sql_splitted_terms
