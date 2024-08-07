""" Parsers unit tests
"""

import os
import sys
import inspect
import textwrap

import pytest

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from dou_dag_generator import DouDigestDagGenerator, YAMLParser, DAGConfig


@pytest.mark.parametrize(
    "dag_id, size, hashed",
    [
        ("unique_id_for_each_dag", 60, 56),
        ("generates_sparses_hashed_results", 120, 59),
        ("unique_id_for_each_dag", 10, 6),
        ("", 10, 0),
        ("", 100, 0),
    ],
)
def test_hash_dag_id(yaml_parser, dag_id, size, hashed):
    assert yaml_parser._hash_dag_id(dag_id, size) == hashed


@pytest.mark.parametrize(
    "filepath, result_tuple",
    [
        (
            "basic_example.yaml",
            {
                "dag_id": "basic_example",
                "search": [
                    {
                        "terms": [
                            "dados abertos",
                            "governo aberto",
                            "lei de acesso à informação",
                        ],
                        "header": None,
                        "sources": ["DOU"],
                        "sql": None,
                        "conn_id": None,
                        "territory_id": None,
                        "dou_sections": ["TODOS"],
                        "search_date": "DIA",
                        "field": "TUDO",
                        "is_exact_search": True,
                        "ignore_signature_match": False,
                        "force_rematch": None,
                        "full_text": None,
                        "use_summary": None,
                        "department": None,
                    }
                ],
                "emails": ["destination@economia.gov.br"],
                "subject": "Teste do Ro-dou",
                "attach_csv": False,
                "discord_webhook": None,
                "slack_webhook": None,
                "schedule": "37 5 * * *",
                "description": "DAG de teste",
                "skip_null": True,
                "doc_md": None,
                "dag_tags": {"dou", "generated_dag"},
                "owner": "",
                "hide_filters": False,
                "header_text": None,
                "footer_text": None,
                "no_results_found_text": "Nenhum dos termos pesquisados foi encontrado nesta consulta",
            },
        ),
        (
            "all_parameters_example.yaml",
            {
                "dag_id": "all_parameters_example",
                "search": [
                    {
                        "terms": [
                            "dados abertos",
                            "governo aberto",
                            "lei de acesso à informação",
                        ],
                        "header": None,
                        "sources": ["DOU"],
                        "sql": None,
                        "conn_id": None,
                        "territory_id": None,
                        "dou_sections": ["SECAO_1", "EDICAO_SUPLEMENTAR"],
                        "search_date": "MES",
                        "field": "TUDO",
                        "is_exact_search": True,
                        "ignore_signature_match": True,
                        "force_rematch": True,
                        "full_text": True,
                        "use_summary": True,
                        "department": None,
                    }
                ],
                "emails": ["dest1@economia.gov.br", "dest2@economia.gov.br"],
                "subject": "Assunto do Email",
                "attach_csv": True,
                "discord_webhook": None,
                "slack_webhook": None,
                "schedule": "0 8 * * MON-FRI",
                "description": "DAG exemplo utilizando todos os demais parâmetros.",
                "skip_null": True,
                "doc_md": None,
                "dag_tags": {"dou", "generated_dag", "projeto_a", "departamento_x"},
                "owner": "pessoa 1, pessoa 2",
                "hide_filters": False,
                "header_text": None,
                "footer_text": None,
                "no_results_found_text": "Nenhum dos termos pesquisados foi encontrado nesta consulta",
            },
        ),
        (
            "terms_from_db_example.yaml",
            {
                "dag_id": "terms_from_db_example",
                "search": [
                    {
                        "terms": [],
                        "header": None,
                        "sources": ["DOU"],
                        "sql": (
                            "SELECT 'cloroquina' as TERMO, 'Ações inefetivas' as GRUPO "
                            "UNION SELECT 'ivermectina' as TERMO, 'Ações inefetivas' as GRUPO "
                            "UNION SELECT 'vacina contra covid' as TERMO, 'Ações efetivas' as GRUPO "
                            "UNION SELECT 'higienização das mãos' as TERMO, 'Ações efetivas' as GRUPO "
                            "UNION SELECT 'uso de máscara' as TERMO, 'Ações efetivas' as GRUPO "
                            "UNION SELECT 'distanciamento social' as TERMO, 'Ações efetivas' as GRUPO\n"
                        ),
                        "conn_id": "example_database_conn",
                        "territory_id": None,
                        "dou_sections": ["TODOS"],
                        "search_date": "MES",
                        "field": "TUDO",
                        "is_exact_search": True,
                        "ignore_signature_match": False,
                        "force_rematch": None,
                        "full_text": None,
                        "use_summary": None,
                        "department": None,
                    }
                ],
                "emails": ["destination@economia.gov.br"],
                "subject": "[String] com caracteres especiais deve estar entre aspas",
                "attach_csv": True,
                "discord_webhook": None,
                "slack_webhook": None,
                "schedule": "2 5 * * *",
                "description": "DAG de teste",
                "skip_null": True,
                "doc_md": None,
                "dag_tags": {"dou", "generated_dag"},
                "owner": "",
                "hide_filters": False,
                "header_text": None,
                "footer_text": None,
                "no_results_found_text": "Nenhum dos termos pesquisados foi encontrado nesta consulta",
            },
        ),
        (
            "basic_example_skip_null.yaml",
            {
                "dag_id": "basic_example_skip_null",
                "search": [
                    {
                        "terms": ["cimentodaaroeira"],
                        "header": None,
                        "sources": ["DOU"],
                        "sql": None,
                        "conn_id": None,
                        "territory_id": None,
                        "dou_sections": ["TODOS"],
                        "search_date": "DIA",
                        "field": "TUDO",
                        "is_exact_search": True,
                        "ignore_signature_match": False,
                        "force_rematch": None,
                        "full_text": None,
                        "use_summary": None,
                        "department": None,
                    }
                ],
                "emails": ["destination@economia.gov.br"],
                "subject": "Teste do Ro-dou",
                "attach_csv": False,
                "discord_webhook": None,
                "slack_webhook": None,
                "schedule": "29 5 * * *",
                "description": "DAG de teste",
                "skip_null": False,
                "doc_md": None,
                "dag_tags": {"dou", "generated_dag"},
                "owner": "",
                "hide_filters": False,
                "header_text": None,
                "footer_text": None,
                "no_results_found_text": "Nenhum dos termos pesquisados foi encontrado nesta consulta",
            },
        ),
        (
            "markdown_docs_example.yaml",
            {
                "dag_id": "markdown_docs_example",
                "search": [
                    {
                        "terms": [
                            "dados abertos",
                            "governo aberto",
                            "lei de acesso à informação",
                        ],
                        "header": None,
                        "sources": ["DOU"],
                        "sql": None,
                        "conn_id": None,
                        "territory_id": None,
                        "dou_sections": ["TODOS"],
                        "search_date": "DIA",
                        "field": "TUDO",
                        "is_exact_search": True,
                        "ignore_signature_match": False,
                        "force_rematch": None,
                        "full_text": None,
                        "use_summary": None,
                        "department": None,
                    }
                ],
                "emails": ["destination@economia.gov.br"],
                "subject": "Teste do Ro-dou",
                "attach_csv": False,
                "discord_webhook": None,
                "slack_webhook": None,
                "schedule": "10 5 * * *",
                "description": "DAG com documentação em markdown",
                "skip_null": True,
                "doc_md": textwrap.dedent(
                    """
                    ## Ola!
                    Esta é uma DAG de exemplo com documentação em markdown. Esta descrição é opcional e pode ser definida no parâmetro `doc_md`.

                      * Ah, aqui você também pode usar *markdown* para
                      * escrever listas, por exemplo,
                      * ou colocar [links](graph)!"""
                ).strip(),
                "dag_tags": {"dou", "generated_dag"},
                "owner": "",
                "hide_filters": False,
                "header_text": None,
                "footer_text": None,
                "no_results_found_text": "Nenhum dos termos pesquisados foi encontrado nesta consulta",
            },
        ),
        (
            "department_example.yaml",
            {
                "dag_id": "department_example",
                "search": [
                    {
                        "terms": ["dados abertos"],
                        "header": None,
                        "sources": ["DOU"],
                        "sql": None,
                        "conn_id": None,
                        "territory_id": None,
                        "dou_sections": ["TODOS"],
                        "search_date": "DIA",
                        "field": "TUDO",
                        "is_exact_search": True,
                        "ignore_signature_match": False,
                        "force_rematch": None,
                        "full_text": None,
                        "use_summary": None,
                        "department": [
                            "Ministério da Gestão e da Inovação em Serviços Públicos",
                            "Ministério da Defesa",
                        ],
                    }
                ],
                "emails": ["destination@economia.gov.br"],
                "subject": "Teste do Ro-dou",
                "attach_csv": False,
                "discord_webhook": None,
                "slack_webhook": None,
                "schedule": "59 5 * * *",
                "description": "DAG de teste (filtro por departamento)",
                "skip_null": True,
                "doc_md": None,
                "dag_tags": {"dou", "generated_dag"},
                "owner": "",
                "hide_filters": False,
                "header_text": None,
                "footer_text": None,
                "no_results_found_text": "Nenhum dos termos pesquisados foi encontrado nesta consulta",
            },
        ),
        (
            "inlabs_example.yaml",
            {
                "dag_id": "inlabs_example",
                "search": [
                    {
                        "terms": ["tecnologia", "informação"],
                        "header": None,
                        "sources": ["INLABS"],
                        "sql": None,
                        "conn_id": None,
                        "territory_id": None,
                        "dou_sections": ["TODOS"],
                        "search_date": "DIA",
                        "field": "TUDO",
                        "is_exact_search": True,
                        "ignore_signature_match": False,
                        "force_rematch": None,
                        "full_text": None,
                        "use_summary": True,
                        "department": None,
                    }
                ],
                "emails": ["destination@economia.gov.br"],
                "subject": "Teste do Ro-dou",
                "attach_csv": True,
                "discord_webhook": None,
                "slack_webhook": None,
                "schedule": "0 8 * * MON-FRI",
                "description": "DAG de teste",
                "skip_null": True,
                "doc_md": None,
                "dag_tags": {"dou", "generated_dag", "inlabs"},
                "owner": "cdata",
                "hide_filters": False,
                "header_text": None,
                "footer_text": None,
                "no_results_found_text": "Nenhum dos termos pesquisados foi encontrado nesta consulta",
            },
        ),
        (
            "inlabs_advanced_search_example.yaml",
            {
                "dag_id": "inlabs_advanced_search_example",
                "search": [
                    {
                        "terms": [
                            "designar & ( MGI | MINISTÉRIO FAZENDA)",
                            "instituto & federal ! paraná",
                        ],
                        "header": None,
                        "sources": ["INLABS"],
                        "sql": None,
                        "conn_id": None,
                        "territory_id": None,
                        "dou_sections": ["TODOS"],
                        "search_date": "DIA",
                        "field": "TUDO",
                        "is_exact_search": True,
                        "ignore_signature_match": False,
                        "force_rematch": None,
                        "full_text": None,
                        "use_summary": None,
                        "department": None,
                    }
                ],
                "emails": ["destination@economia.gov.br"],
                "subject": "Teste do Ro-dou",
                "attach_csv": True,
                "discord_webhook": None,
                "slack_webhook": None,
                "schedule": "0 8 * * MON-FRI",
                "description": "DAG de teste",
                "skip_null": True,
                "doc_md": None,
                "dag_tags": {"dou", "generated_dag", "inlabs"},
                "owner": "cdata",
                "hide_filters": False,
                "header_text": None,
                "footer_text": None,
                "no_results_found_text": "Nenhum dos termos pesquisados foi encontrado nesta consulta",
            },
        ),
        (
            "multiple_searchs_example.yaml",
            {
                "dag_id": "multiple_searchs_example",
                "search": [
                    {
                        "terms": [
                            "dados abertos",
                            "governo aberto",
                            "lei de acesso à informação",
                        ],
                        "header": "Pesquisa no DOU",
                        "sources": ["INLABS"],
                        "sql": None,
                        "conn_id": None,
                        "territory_id": None,
                        "dou_sections": ["TODOS"],
                        "search_date": "DIA",
                        "field": "TUDO",
                        "is_exact_search": True,
                        "ignore_signature_match": True,
                        "force_rematch": True,
                        "full_text": None,
                        "use_summary": None,
                        "department": None,
                    },
                    {
                        "terms": [
                            "dados abertos",
                            "governo aberto",
                            "lei de acesso à informação",
                        ],
                        "header": "Pesquisa no QD",
                        "sources": ["QD"],
                        "sql": None,
                        "conn_id": None,
                        "territory_id": None,
                        "dou_sections": ["TODOS"],
                        "search_date": "DIA",
                        "field": "TUDO",
                        "is_exact_search": True,
                        "ignore_signature_match": True,
                        "force_rematch": True,
                        "full_text": None,
                        "use_summary": None,
                        "department": None,
                    },
                ],
                "emails": ["destination@economia.gov.br"],
                "subject": "Teste do Ro-dou",
                "attach_csv": False,
                "discord_webhook": None,
                "slack_webhook": None,
                "schedule": "0 8 * * MON-FRI",
                "description": "DAG de teste com múltiplas buscas",
                "skip_null": False,
                "doc_md": None,
                "dag_tags": {"dou", "generated_dag", "inlabs"},
                "owner": "",
                "hide_filters": False,
                "header_text": None,
                "footer_text": None,
                "no_results_found_text": "Nenhum dos termos pesquisados foi encontrado nesta consulta",
            },
        ),
        (
            "hide_filters_example.yaml",
            {
                "dag_id": "hide_filters_example",
                "search": [
                    {
                        "terms": ["tecnologia", "informação"],
                        "header": "HEADER TEXT",
                        "sources": ["INLABS"],
                        "sql": None,
                        "conn_id": None,
                        "territory_id": None,
                        "dou_sections": ["TODOS"],
                        "search_date": "DIA",
                        "field": "TUDO",
                        "is_exact_search": True,
                        "ignore_signature_match": False,
                        "force_rematch": None,
                        "full_text": None,
                        "use_summary": None,
                        "department": [
                            "Ministério da Gestão e da Inovação em Serviços Públicos",
                            "Ministério da Defesa",
                        ],
                    }
                ],
                "emails": ["destination@economia.gov.br"],
                "subject": "Teste do Ro-dou",
                "attach_csv": True,
                "discord_webhook": None,
                "slack_webhook": None,
                "schedule": "0 8 * * MON-FRI",
                "description": "DAG de teste",
                "skip_null": True,
                "doc_md": None,
                "dag_tags": {"dou", "inlabs", "generated_dag"},
                "owner": "",
                "hide_filters": True,
                "header_text": None,
                "footer_text": None,
                "no_results_found_text": "Nenhum dos termos pesquisados foi encontrado nesta consulta",
            },
        ),
        (
            "header_and_footer_example.yaml",
            {
                "dag_id": "header_and_footer_example",
                "search": [
                    {
                        "terms": ["tecnologia", "informação"],
                        "header": None,
                        "sources": ["DOU"],
                        "sql": None,
                        "conn_id": None,
                        "territory_id": None,
                        "dou_sections": ["TODOS"],
                        "search_date": "DIA",
                        "field": "TUDO",
                        "is_exact_search": True,
                        "ignore_signature_match": False,
                        "force_rematch": None,
                        "full_text": None,
                        "use_summary": None,
                        "department": None,
                    }
                ],
                "emails": ["destination@economia.gov.br"],
                "subject": "Teste do Ro-dou",
                "attach_csv": False,
                "discord_webhook": None,
                "slack_webhook": None,
                "schedule": "0 8 * * MON-FRI",
                "description": "DAG de teste",
                "skip_null": True,
                "doc_md": None,
                "dag_tags": {"dou", "generated_dag"},
                "owner": "",
                "hide_filters": False,
                "header_text": "<p><strong>Greetings<strong></p>",
                "footer_text": "<p>Best Regards</p>",
                "no_results_found_text": "No results found",
            },
        ),
    ],
)

def test_parse(filepath, result_tuple):
    filepath = os.path.join(
        DouDigestDagGenerator().YAMLS_DIR, "examples_and_tests", filepath
    )
    parsed = YAMLParser(filepath=filepath).parse()

    assert parsed == DAGConfig(**result_tuple)
