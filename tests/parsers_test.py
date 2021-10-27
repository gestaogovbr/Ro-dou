""" Parsers unit tests
"""

import os
import sys
import inspect

import pytest

import pandas as pd

currentdir = os.path.dirname(
    os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from dou_dag_generator import DouDigestDagGenerator, YAMLParser

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
    'filepath, result_tuple',
    [
        ('basic_example.yaml',
         (
             'basic_example',
             ['TODOS'],
             'DIA',
             'TUDO',
             True,
             False,
             False,
             ['dados abertos',
             'governo aberto',
             'lei de acesso à informação'],
             None,
             None,
             ['nitai.silva@economia.gov.br'],
             'Teste do Ro-dou',
             True,
             '37 5 * * *',
             'DAG de teste',
             {'dou', 'generated_dag'}
             )
        ),
        ('second_example.yaml',
         (
             'dag_id_deve_ser_unico_em_todo_airflow',
             ['SECAO_1', 'EDICAO_SUPLEMENTAR'],
             'DIA',
             'TUDO',
             True,
             False,
             False,
             ['alocação',
             'realoca',
             'permuta',
             'estrutura regimental',
             'organização básica',
             ],
             None,
             None,
             ['dest1@economia.gov.br', 'dest2@economia.gov.br'],
             'Assunto do Email',
             True,
             '0 8 * * MON-FRI',
             'DAG exemplo de monitoramento no DOU.',
             {'dou', 'generated_dag'}
             )
        ),
        ('third_example.yaml',
         (
             'dag_ultra_dinamica',
             ['TODOS'],
             'DIA',
             'TUDO',
             True,
             False,
             False,
             [],
             'SELECT termo, categoria FROM schema.tabela;',
             'airflow_conn_id',
             ['email-destino@economia.gov.br'],
             '[String] com caracteres especiais deve estar entre aspas',
             False,
             '4 5 * * *',
             'A pesquisa depende do select SQL.',
             {'dou', 'generated_dag', 'projeto_a', 'departamento_x'}
             )
        ),
    ])
def test_parse(filepath, result_tuple):
    filepath = os.path.join(DouDigestDagGenerator().YAMLS_DIR,
                            filepath)
    assert YAMLParser(filepath=filepath).parse() == result_tuple
