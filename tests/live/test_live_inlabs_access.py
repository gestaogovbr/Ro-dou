"""Valida credenciais, conexão em memória e escolha da data (passo 2)."""

from datetime import date, timedelta
from unittest.mock import Mock

import pytest
import requests
from airflow.sdk.bases.hook import BaseHook

from conftest import _has_edition

pytestmark = pytest.mark.live


def test_has_edition_raises_on_http_error():
    response = requests.Response()
    response.status_code = 503
    response._content = b"<html>Service unavailable</html>"
    session = Mock()
    session.get.return_value = response

    with pytest.raises(requests.HTTPError):
        _has_edition(session, date(2026, 10, 5))


def test_connection_is_resolved_from_env(inlabs_connection, inlabs_credentials):
    conn = BaseHook.get_connection("inlabs_portal")
    assert conn.host == "https://inlabs.in.gov.br/"
    assert conn.login == inlabs_credentials.user



def test_reference_date_is_a_recent_business_day(reference_date):
    assert reference_date.weekday() < 5
    assert date.today() - timedelta(days=7) <= reference_date <= date.today()
