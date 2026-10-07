"""Valida o próprio verificador de resultados usado pelos testes live."""

from unittest.mock import Mock

import pytest
from airflow.utils.state import DagRunState

from result_checks import check_search_run, has_results

pytestmark = pytest.mark.live


@pytest.mark.parametrize(
    "result, expected",
    [
        ({}, False),
        ({"single_group": {}}, False),
        ({"single_group": {"dados abertos": {"Ministério": [{}]}}}, True),
    ],
)
def test_has_results(result, expected):
    assert has_results(result) is expected


def test_check_search_run_skips_when_groups_are_empty():
    dag_run = Mock(state=DagRunState.SUCCESS)
    dag_run.get_task_instance.return_value.xcom_pull.return_value = {
        "result": {"single_group": {}}
    }

    with pytest.raises(pytest.skip.Exception, match="Sem resultados"):
        check_search_run(dag_run, Mock(), ["dados abertos"], "DOU em 06/10/2026")
