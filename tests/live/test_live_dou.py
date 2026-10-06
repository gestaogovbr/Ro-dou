"""Cenário live: DAG de exemplo `basic_example` (fonte DOU) contra a API real.

Só o envio de e-mail é mockado. O patch usa o nome de módulo de topo
(`notification.email_sender`), como em test_e2e_dag_execution.py.
"""

from unittest.mock import patch

import pytest

from result_checks import check_search_run

pytestmark = pytest.mark.live


def test_dou_example_dag_returns_valid_results(
    build_example_dag, reference_date, reference_logical_date
):
    dag, terms = build_example_dag("basic_example.yaml")
    with patch("notification.email_sender.send_email") as mock_send_email:
        dag_run = dag.test(logical_date=reference_logical_date)

    check_search_run(dag_run, mock_send_email, terms, f"DOU em {reference_date:%d/%m/%Y}")
