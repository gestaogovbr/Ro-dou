"""Airflow DAG that enriches INLABS publications indexed in OpenSearch with
named entities extracted by the GLiNER2 service.

Runs after each INLABS load (assets `inlabs` and `inlabs_edicao_extra`) in
parallel with the clipping DAGs, so the enrichment never delays reports.
Only documents never enriched, whose text changed or that were enriched with
another service configuration are sent to the service.
"""

import logging
import os
from datetime import datetime, timedelta

from airflow.sdk import dag, task, get_current_context, Variable
from airflow.sdk.definitions.asset import Dataset


def _get_setting(key: str, default: str = "") -> str:
    """Read an Airflow Variable, falling back to the environment."""
    return Variable.get(key, os.getenv(key, default)) or default


def _notify_on_failure(context):
    """Sends a failure notification reusing FailureSender."""
    from types import SimpleNamespace
    from ro_dou_src.notification.failure_sender import FailureSender

    try:
        task_instance = context.get("task_instance") or context.get("ti")
        dag_run = context.get("dag_run")

        if not task_instance or not dag_run:
            logging.error("Missing required context: task_instance or dag_run")
            return

        specs = SimpleNamespace(callback=None, report=None)
        FailureSender(specs=specs).send(
            context, dag_run, task_instance, exception=context.get("exception")
        )
    except Exception as e:
        logging.error(f"Error in _notify_on_failure: {str(e)}", exc_info=True)


default_args = {
    "owner": "airflow",
    "start_date": datetime(2024, 4, 1),
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=10),
    "on_failure_callback": _notify_on_failure,
}


@dag(
    dag_id="ro-dou_inlabs_gliner_enrich",
    default_args=default_args,
    schedule=(Dataset("inlabs") | Dataset("inlabs_edicao_extra")),
    catchup=False,
    description=__doc__,
    max_active_runs=1,
    tags=["ro-dou", "inlabs", "gliner"],
)
def gliner_enrich():

    @task.short_circuit
    def check_if_enabled() -> bool:
        use_opensearch = _get_setting("RO_DOU_INLABS_USE_OPENSEARCH", "false")
        enabled = _get_setting("RO_DOU_GLINER_ENABLED", "false")
        if use_opensearch.lower() != "true" or enabled.lower() != "true":
            logging.info(
                "GLiNER2 enrichment skipped: RO_DOU_INLABS_USE_OPENSEARCH=%s, "
                "RO_DOU_GLINER_ENABLED=%s.",
                use_opensearch,
                enabled,
            )
            return False
        return True

    @task
    def get_reference_dates() -> list:
        """Return the run's reference dates in YYYY-MM-DD. Asset events
        queued for several dates may be batched into a single run."""
        from ro_dou_src.utils.date import get_reference_dates as resolve_dates

        return [day.isoformat() for day in resolve_dates(get_current_context())]

    @task(execution_timeout=timedelta(hours=8))
    def enrich_entities(reference_dates: list) -> dict:
        from ro_dou_src.utils.open_search.client_open_search import OpenSearchClient  # type: ignore
        from ro_dou_src.utils.open_search.config import INDEX_NAME  # type: ignore
        from ro_dou_src.utils.gliner.gliner_enrichment import (  # type: ignore
            GlinerEnricher,
            GlinerServiceClient,
        )

        service = GlinerServiceClient(
            base_url=_get_setting("RO_DOU_GLINER_SERVICE_URL", "http://gliner:8000"),
            token=_get_setting("RO_DOU_GLINER_API_TOKEN") or None,
            timeout=float(_get_setting("RO_DOU_GLINER_TIMEOUT", "600")),
        )
        enricher = GlinerEnricher(
            client=OpenSearchClient().get_client(),
            service=service,
            index=INDEX_NAME,
        )
        stats = {}
        failures = []
        for reference_date in reference_dates:
            # A failing date does not prevent the others from being enriched.
            try:
                stats[reference_date] = enricher.run(reference_date)
            except Exception as error:
                logging.error(
                    "GLiNER2 enrichment failed for %s: %s", reference_date, error
                )
                failures.append(reference_date)
        if failures:
            raise RuntimeError(f"GLiNER2 enrichment failed for: {', '.join(failures)}")
        return stats

    ## Orchestration
    reference_dates = get_reference_dates()
    check_if_enabled() >> reference_dates
    enrich_entities(reference_dates)


dag = gliner_enrich()
