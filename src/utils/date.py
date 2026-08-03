"""Resolve the business date used by Ro-dou DAG runs."""

import os
from datetime import date


AIRFLOW_TIMEZONE = os.getenv("AIRFLOW__CORE__DEFAULT_TIMEZONE", "UTC")


def get_reference_date(context: dict) -> date:
    """Return the business date for manual, scheduled, or asset runs."""

    run_type = getattr(
        context["dag_run"].run_type, "value", context["dag_run"].run_type
    )

    if run_type == "asset_triggered":
        events = context["triggering_asset_events"]
        event = next(
            event
            for asset_events in events.values()
            for event in asset_events
        )
        try:
            return date.fromisoformat(event.extra["reference_date"])
        except KeyError as error:
            raise ValueError(
                "Triggering asset event does not contain reference_date"
            ) from error

    run_date = (
        context["logical_date"]
        if run_type == "manual"
        else context["data_interval_end"]
    )
    return run_date.in_timezone(AIRFLOW_TIMEZONE).date()
