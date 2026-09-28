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


def _ensure_inlabs_load_dag_succeeded_today(force_run: bool = True):
    """Ensure the INLABS loading DAG has run successfully for today's
    reference date. For a true end-to-end validation we optionally force a
    new run of the loader even if a successful run exists already.

    After the run succeeds, the helper verifies the `dou_inlabs.article_raw`
    table contains at least one row for today's reference date to assert the
    download/persistence steps executed as expected.
    """
    dag_id = "ro-dou_inlabs_load_pg"
    success_state = DagRunState.SUCCESS
    today = datetime.utcnow().date()

    def _has_success_today():
        from sqlalchemy import create_engine

        engine = create_engine(settings.SQL_ALCHEMY_CONN)
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT start_date
                    FROM dag_run
                    WHERE dag_id = :dag_id AND state = :state
                    ORDER BY start_date DESC
                    """
                ),
                {"dag_id": dag_id, "state": success_state},
            ).fetchall()
        return bool(rows and any(r[0].date() == today for r in rows))

    # If force_run is False and we already have a success today, nothing else to do
    if not force_run and _has_success_today():
        return

    # Trigger a fresh run to exercise authentication, download and load steps
    subprocess.run(
        ["airflow", "dags", "trigger", dag_id],
        check=True,
        capture_output=True,
        text=True,
    )

    deadline = time.time() + 1200
    while time.time() < deadline:
        if _has_success_today():
            # verify data persisted in the target table for today's date
            from sqlalchemy import create_engine

            engine = create_engine(settings.SQL_ALCHEMY_CONN)
            with engine.connect() as conn:
                count = conn.execute(
                    text(
                        "SELECT count(*) FROM dou_inlabs.article_raw WHERE DATE(pubdate) = :today"
                    ),
                    {"today": today},
                ).scalar()
            if count and count > 0:
                return
            # If DAG succeeded but table empty, keep waiting briefly for eventual consistency
        time.sleep(15)

    raise AssertionError(
        f"A DAG {dag_id} não carregou dados válidos para {today} antes do teste real do INLABS."
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
    # Force a fresh load run to exercise portal auth, download and persistence
    _ensure_inlabs_load_dag_succeeded_today(force_run=True)
    dag = _build_real_dag(dag_gen, config_file)

    with patch("searchers.time.sleep"), patch(
        "notification.email_sender.send_email"
    ) as mock_send_email:
        dag_run = dag.test()

    _assert_email_outcome(dag_run, mock_send_email)

    # Collect exec_search task XComs to ensure at least one publication was found
    search_results = []
    counter = 1
    while True:
        task_id = f"exec_searchs.exec_search_{counter}"
        if task_id not in dag.task_dict:
            break
        ti = dag_run.get_task_instance(task_id)
        try:
            val = ti.xcom_pull(task_ids=task_id)
        except Exception:
            val = None
        search_results.append(val)
        counter += 1

    # Flatten and check presence of at least one match
    has_match = False
    for res in search_results:
        if res:
            # Expect hook transforms to return iterable-like results
            try:
                if isinstance(res, (list, tuple)) and len(res) > 0:
                    has_match = True
                    break
                if isinstance(res, dict) and any(v for v in res.values()):
                    has_match = True
                    break
            except Exception:
                has_match = True
                break

    assert has_match, "Nenhuma publicação encontrada pela DAG de busca do INLABS após a carga."


@pytest.mark.parametrize("config_file", ["qd_example.yaml"], ids=["qd"])
def test_e2e_dag_run_real_qd_search(dag_gen: DouDigestDagGenerator, config_file):
    """Validate the real QD source end-to-end without mocking the search layer."""
    dag = _build_real_dag(dag_gen, config_file)

    with patch("searchers.time.sleep"), patch(
        "notification.email_sender.send_email"
    ) as mock_send_email:
        dag_run = dag.test()

    _assert_email_outcome(dag_run, mock_send_email)
