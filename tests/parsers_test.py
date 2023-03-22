""" Parsers unit tests
"""

import os
import sys
import inspect
import textwrap

import pytest

import pandas as pd

currentdir = os.path.dirname(
    os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from dou_dag_generator import DouDigestDagGenerator, YAMLParser, DAGConfig

@pytest.mark.parametrize(
    'dag_id, size, hashed',
    [
        ('unique_id_for_each_dag', 60, 56),
        ('generates_sparses_hashed_results', 120, 59),
        ('unique_id_for_each_dag', 10, 6),
        ('', 10, 0),
        ('', 100, 0),
    ])
def test_hash_dag_id(yaml_parser, dag_id, size, hashed):
    assert yaml_parser._hash_dag_id(dag_id, size) == hashed

@pytest.mark.parametrize(
    "filepath, result_tuple",
    [
        ("basic_example.yaml",
            {
                "dag_id": "basic_example",
                "sources": ["DOU"],
                "territory_id": None,
                "dou_sections": ["TODOS"],
                "search_date": "DIA",
                "field": "TUDO",
                "is_exact_search": True,
                "ignore_signature_match": False,
                "force_rematch": None,
                "terms": ["dados abertos",
                    "governo aberto",
                    "lei de acesso à informação"],
                "sql": None,
                "conn_id": None,
                "emails": ["destination@economia.gov.br"],
                "subject": "Teste do Ro-dou",
                "attach_csv": False,
                "discord_webhook": None,
                "schedule": "37 5 * * *",
                "description": "DAG de teste",
                "skip_null": True,
                "doc_md": None,
                "dag_tags": {"dou", "generated_dag"}
            }
        ),
        ("all_parameters_example.yaml",
            {
                "dag_id": "all_parameters_example",
                "sources": ["DOU"],
                "territory_id": None,
                "dou_sections": ["SECAO_1", "EDICAO_SUPLEMENTAR"],
                "search_date": "MES",
                "field": "TUDO",
                "is_exact_search": True,
                "ignore_signature_match": True,
                "force_rematch": True,
                "terms": ["dados abertos",
                    "governo aberto",
                    "lei de acesso à informação"],
                "sql": None,
                "conn_id": None,
                "emails": ["dest1@economia.gov.br", "dest2@economia.gov.br"],
                "subject": "Assunto do Email",
                "attach_csv": True,
                "discord_webhook": None,
                "schedule": "0 8 * * MON-FRI",
                "description": "DAG exemplo utilizando todos os demais parâmetros.",
                "skip_null": True,
                "doc_md": None,
                "dag_tags": {"dou", "generated_dag", "projeto_a", "departamento_x"}
            }
        ),
        ("terms_from_db_example.yaml",
            {
                "dag_id": "terms_from_db_example",
                "sources": ["DOU"],
                "territory_id": None,
                "dou_sections": ["TODOS"],
                "search_date": "MES",
                "field": "TUDO",
                "is_exact_search": True,
                "ignore_signature_match": False,
                "force_rematch": None,
                "terms": [],
                "sql": ("SELECT 'cloroquina' as TERMO, 'Ações inefetivas' as GRUPO "
                    "UNION SELECT 'ivermectina' as TERMO, 'Ações inefetivas' as GRUPO "
                    "UNION SELECT 'vacina contra covid' as TERMO, 'Ações efetivas' as GRUPO "
                    "UNION SELECT 'higienização das mãos' as TERMO, 'Ações efetivas' as GRUPO "
                    "UNION SELECT 'uso de máscara' as TERMO, 'Ações efetivas' as GRUPO "
                    "UNION SELECT 'distanciamento social' as TERMO, 'Ações efetivas' as GRUPO\n"),
                "conn_id": "example_database_conn",
                "emails": ["destination@economia.gov.br"],
                "subject": "[String] com caracteres especiais deve estar entre aspas",
                "attach_csv": True,
                "discord_webhook": None,
                "schedule": "2 5 * * *",
                "description": "DAG de teste",
                "skip_null": True,
                "doc_md": None,
                "dag_tags": {"dou", "generated_dag"}
            }
        ),
        ("basic_example_skip_null.yaml",
            {
                "dag_id": "basic_example_skip_null",
                "sources": ["DOU"],
                "territory_id": None,
                "dou_sections": ["TODOS"],
                "search_date": "DIA",
                "field": "TUDO",
                "is_exact_search": True,
                "ignore_signature_match": False,
                "force_rematch": None,
                "terms": ["cimentodaaroeira"],
                "sql": None,
                "conn_id": None,
                "emails": ["destination@economia.gov.br"],
                "subject": 'Teste do Ro-dou',
                "attach_csv": False,
                "discord_webhook": None,
                "schedule": "29 5 * * *",
                "description": "DAG de teste",
                "skip_null": False,
                "doc_md": None,
                "dag_tags": {"dou", "generated_dag"}
            },
        ),
        ("markdown_docs_example.yaml",
            {
                "dag_id": "markdown_docs_example",
                "sources": ["DOU"],
                "territory_id": None,
                "dou_sections": ["TODOS"],
                "search_date": "DIA",
                "field": "TUDO",
                "is_exact_search": True,
                "ignore_signature_match": False,
                "force_rematch": None,
                "terms": ["dados abertos",
                    "governo aberto",
                    "lei de acesso à informação"],
                "sql": None,
                "conn_id": None,
                "emails": ["destination@economia.gov.br"],
                "subject": "Teste do Ro-dou",
                "attach_csv": False,
                "discord_webhook": None,
                "schedule": "10 5 * * *",
                "description": "DAG com documentação em markdown",
                "skip_null": True,
                "doc_md": textwrap.dedent("""
                    ## Ola!
                    Esta é uma DAG de exemplo com documentação em markdown. Esta descrição é opcional e pode ser definida no parâmetro `doc_md`.

                      * Ah, aqui você também pode usar *markdown* para
                      * escrever listas, por exemplo,
                      * ou colocar [links](graph)!""").strip(),
                "dag_tags": {"dou", "generated_dag"}
            }
        ),
    ])
def test_parse(filepath, result_tuple):
    filepath = os.path.join(DouDigestDagGenerator().YAMLS_DIR, filepath)
    parsed = YAMLParser(filepath=filepath).parse()

    assert parsed == DAGConfig(**result_tuple)
