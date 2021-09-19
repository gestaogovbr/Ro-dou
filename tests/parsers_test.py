""" Parsers unit tests
"""

import pytest

import pandas as pd

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
    assert yaml_parser.hash_dag_id(dag_id, size) == hashed
