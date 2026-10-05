"""Valida credenciais, conexão em memória e escolha da data (passo 2)."""

from datetime import date, timedelta

import pytest
from airflow.sdk.bases.hook import BaseHook

pytestmark = pytest.mark.live


def test_connection_is_resolved_from_env(inlabs_connection, inlabs_credentials):
    conn = BaseHook.get_connection("inlabs_portal")
    assert conn.host == "https://inlabs.in.gov.br/"
    assert conn.login == inlabs_credentials.user



def test_reference_date_is_a_recent_business_day(reference_date):
    assert reference_date.weekday() < 5
    assert date.today() - timedelta(days=7) <= reference_date < date.today()
