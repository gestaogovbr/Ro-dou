from datetime import date
from types import SimpleNamespace

import pendulum
import pytest

from utils.date import get_reference_date, get_reference_dates


def _context(run_type, **values):
    return {"dag_run": SimpleNamespace(run_type=run_type), **values}


def test_manual_run_uses_logical_date():
    context = _context(
        "manual",
        logical_date=pendulum.datetime(2026, 7, 30, 12, tz="UTC"),
    )

    assert get_reference_date(context) == date(2026, 7, 30)


def test_scheduled_run_uses_data_interval_end():
    context = _context(
        "scheduled",
        data_interval_end=pendulum.datetime(2026, 7, 31, 11, tz="UTC"),
    )

    assert get_reference_date(context) == date(2026, 7, 31)


def test_asset_run_uses_reference_date_metadata():
    event = SimpleNamespace(extra={"reference_date": "2026-07-30"})
    context = _context(
        "asset_triggered", triggering_asset_events={"inlabs": [event]}
    )

    assert get_reference_date(context) == date(2026, 7, 30)


def test_asset_run_requires_reference_date_metadata():
    event = SimpleNamespace(extra={})
    context = _context(
        "asset_triggered", triggering_asset_events={"inlabs": [event]}
    )

    with pytest.raises(ValueError, match="does not contain reference_date"):
        get_reference_date(context)


def test_reference_dates_collects_all_batched_asset_events():
    context = _context(
        "asset_triggered",
        triggering_asset_events={
            "inlabs": [
                SimpleNamespace(extra={"reference_date": "2026-07-31"}),
                SimpleNamespace(extra={"reference_date": "2026-07-30"}),
            ],
            "inlabs_edicao_extra": [
                SimpleNamespace(extra={"reference_date": "2026-07-30"}),
            ],
        },
    )

    assert get_reference_dates(context) == [date(2026, 7, 30), date(2026, 7, 31)]


def test_reference_dates_for_manual_run_is_single_date():
    context = _context(
        "manual",
        logical_date=pendulum.datetime(2026, 7, 30, 12, tz="UTC"),
    )

    assert get_reference_dates(context) == [date(2026, 7, 30)]


def test_reference_dates_requires_reference_date_metadata():
    context = _context(
        "asset_triggered",
        triggering_asset_events={"inlabs": [SimpleNamespace(extra={})]},
    )

    with pytest.raises(ValueError, match="does not contain reference_date"):
        get_reference_dates(context)
