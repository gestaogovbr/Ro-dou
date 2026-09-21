"""End-to-end integration test that exercises a real Ro-dou DAG

This test runs the DAG built from `basic_example.yaml` against the
real external sources (DOU, INLABS, QD, etc.). It intentionally
does NOT mock the search hooks so that the full HTTP integration is
validated. The e-mail sending is still mocked to avoid delivering
actual messages during the test run.

This file is marked as `e2e` so it can be selected/omitted from
regular CI runs via pytest `-m`/`-k` flags.
"""

import os
import subprocess
import time
from datetime import datetime
from unittest.mock import patch

import pytest
from airflow import settings
from airflow.utils.state import DagRunState, TaskInstanceState
from sqlalchemy import text

from dags.ro_dou_src.dou_dag_generator import DouDigestDagGenerator

pytestmark = pytest.mark.e2e

RECIPIENT = "destination@economia.gov.br"


def _ensure_inlabs_load_dag_succeeded_today():
    """Ensure the INLABS loading DAG has succeeded today before running the
    real INLABS search test. If not, trigger it and wait until the load is
    complete successfully."""
    dag_id = "ro-dou_inlabs_load_pg"
    success_state = DagRunState.SUCCESS
    today = datetime.utcnow().date()

    with settings.SQL_ALCHEMY_ENGINE.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT execution_date
                FROM dag_run
                WHERE dag_id = :dag_id AND state = :state
                ORDER BY execution_date DESC
                """
            ),
            {"dag_id": dag_id, "state": success_state},
        ).fetchall()

    if rows and any(row[0].date() == today for row in rows):
        return

    subprocess.run(
        ["airflow", "dags", "trigger", dag_id],
        check=True,
        capture_output=True,
        text=True,
    )

    deadline = time.time() + 600
    while time.time() < deadline:
        with settings.SQL_ALCHEMY_ENGINE.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT execution_date
                    FROM dag_run
                    WHERE dag_id = :dag_id AND state = :state
                    ORDER BY execution_date DESC
                    """
                ),
                {"dag_id": dag_id, "state": success_state},
            ).fetchall()
        if rows and any(row[0].date() == today for row in rows):
            return
        time.sleep(15)

    raise AssertionError(
        f"A DAG {dag_id} não teve sucesso para hoje antes do teste real do INLABS."
    )


def _build_real_dag(dag_gen: DouDigestDagGenerator, config_file: str):
    filepath = os.path.join(dag_gen.YAMLS_DIR, "examples_and_tests", config_file)
    specs = dag_gen.parser(filepath).parse()
    return dag_gen.create_dag(specs, filepath)


def _assert_email_outcome(dag_run, mock_send_email):
    """Validate the common end-to-end completion state."""
    assert dag_run.state == DagRunState.SUCCESS

    notify_state = dag_run.get_task_instance("notify_email").state
    skip_state = dag_run.get_task_instance("skip_notification").state

    assert notify_state in {
        TaskInstanceState.SUCCESS,
        TaskInstanceState.SKIPPED,
    }
    assert skip_state in {
        TaskInstanceState.SUCCESS,
        TaskInstanceState.SKIPPED,
    }
    assert not (
        notify_state == TaskInstanceState.SUCCESS
        and skip_state == TaskInstanceState.SUCCESS
    )

    if mock_send_email.called:
        _, kwargs = mock_send_email.call_args
        assert kwargs["to"] == [RECIPIENT]
        assert "Teste do Ro-dou" in kwargs["subject"]


@pytest.mark.parametrize("config_file", ["basic_example.yaml"], ids=["dou"])
def test_e2e_dag_run_real_dou_search(dag_gen: DouDigestDagGenerator, config_file):
    """Validate the real DOU source end-to-end without mocking the HTTP layer."""
    dag = _build_real_dag(dag_gen, config_file)

    with patch("searchers.time.sleep"), patch(
        "notification.email_sender.send_email"
    ) as mock_send_email:
        dag_run = dag.test()

    _assert_email_outcome(dag_run, mock_send_email)


@pytest.mark.parametrize("config_file", ["inlabs_example.yaml"], ids=["inlabs"])
def test_e2e_dag_run_real_inlabs_search(dag_gen: DouDigestDagGenerator, config_file):
    """Validate the real INLABS source end-to-end without mocking the search layer."""
    _ensure_inlabs_load_dag_succeeded_today()
    dag = _build_real_dag(dag_gen, config_file)

    with patch("searchers.time.sleep"), patch(
        "notification.email_sender.send_email"
    ) as mock_send_email:
        dag_run = dag.test()

    _assert_email_outcome(dag_run, mock_send_email)


@pytest.mark.parametrize("config_file", ["qd_example.yaml"], ids=["qd"])
def test_e2e_dag_run_real_qd_search(dag_gen: DouDigestDagGenerator, config_file):
    """Validate the real QD source end-to-end without mocking the search layer."""
    dag = _build_real_dag(dag_gen, config_file)

    with patch("searchers.time.sleep"), patch(
        "notification.email_sender.send_email"
    ) as mock_send_email:
        dag_run = dag.test()

    _assert_email_outcome(dag_run, mock_send_email)
