"""Cenário live: carga real do INLABS (download -> Postgres) e busca com a DAG
de exemplo `inlabs_example`.

A DAG de carga roda de verdade, exceto as tasks que emitem o dataset `inlabs`
(`mark_success_pattern`): emitir o dataset dispararia, no ambiente local, as
DAGs agendadas por ele. Efeitos colaterais conhecidos, só no ambiente local:
as linhas de `dou_inlabs.article_raw` da data são regravadas e a execução entra
no histórico da DAG de carga.
"""

from pathlib import Path
from unittest.mock import patch

import pytest
from airflow.models import DagBag
from airflow.utils.state import DagRunState, TaskInstanceState

from result_checks import check_search_run

pytestmark = pytest.mark.live

DAGS_ROOT = Path("/opt/airflow/dags")
LOADER_FILE = str(DAGS_ROOT / "ro_dou/dag_load_inlabs/ro_dou_inlabs_load_pg_dag.py")
LOADER_DAG_ID = "ro-dou_inlabs_load_pg"
SKIP_DATASET_TRIGGERS = "trigger_dataset_inlabs.*"


@pytest.fixture(scope="module")
def loaded_inlabs_run(inlabs_connection, tmp_path_factory, reference_logical_date):
    """Roda a DAG de carga uma vez e devolve o DagRun."""
    with pytest.MonkeyPatch.context() as mp:
        # path_tmp isolado: não mexe no diretório usado pela carga agendada.
        mp.setenv("AIRFLOW_VAR_PATH_TMP", str(tmp_path_factory.mktemp("inlabs")))
        bag = DagBag(
            dag_folder=LOADER_FILE, bundle_path=DAGS_ROOT, bundle_name="dags-folder"
        )
        assert not bag.import_errors, f"DAG de carga não importou: {bag.import_errors}"
        dag = bag.dags[LOADER_DAG_ID]
        for task in dag.tasks:
            task.retries = 0  # o default são 3 retries com 5 min de espera
        return dag.test(
            logical_date=reference_logical_date,
            mark_success_pattern=SKIP_DATASET_TRIGGERS,
        )


def test_inlabs_load_dag_downloads_and_loads_data(loaded_inlabs_run):
    assert loaded_inlabs_run.state == DagRunState.SUCCESS
    for task_id in ("download_n_unzip_files", "load_data", "check_loaded_data"):
        ti = loaded_inlabs_run.get_task_instance(task_id)
        assert ti.state == TaskInstanceState.SUCCESS, task_id


def test_inlabs_example_dag_returns_valid_results(
    loaded_inlabs_run, build_example_dag, reference_date, reference_logical_date
):
    assert loaded_inlabs_run.state == DagRunState.SUCCESS, "a carga falhou"
    dag, terms = build_example_dag("inlabs_example.yaml")
    with patch("notification.email_sender.send_email") as mock_send_email:
        dag_run = dag.test(logical_date=reference_logical_date)

    check_search_run(
        dag_run, mock_send_email, terms, f"INLABS em {reference_date:%d/%m/%Y}"
    )
