"""Fixtures dos testes live: credenciais, conexão do INLABS e data de referência."""

import json
import os
from dataclasses import dataclass, field
from datetime import date, timedelta
from urllib.parse import urljoin

import pytest
import requests
from bs4 import BeautifulSoup

INLABS_HOST = "https://inlabs.in.gov.br/"
TIMEOUT = 30
MAX_DAYS_BACK = 7
# Mesmo cabeçalho que a DAG de carga envia ao listar/baixar arquivos.
_LIST_HEADERS = {"origem": "736372697074"}


@dataclass(frozen=True)
class InlabsCredentials:
    user: str
    # repr=False: o pytest imprime os argumentos dos fixtures nos tracebacks.
    password: str = field(repr=False)


@pytest.fixture(scope="session")
def inlabs_credentials():
    
    user = os.getenv("RO_DOU_LIVE_INLABS_USER")
    password = os.getenv("RO_DOU_LIVE_INLABS_PASSWORD")
    if not user or not password:
        pytest.skip(
            "Defina RO_DOU_LIVE_INLABS_USER e RO_DOU_LIVE_INLABS_PASSWORD no .env"
        )
    return InlabsCredentials(user=user, password=password)


@pytest.fixture()
def inlabs_connection(monkeypatch, inlabs_credentials):
    """Conexão `inlabs_portal` só em memória; não toca no banco do Airflow."""
    monkeypatch.setenv(
        "AIRFLOW_CONN_INLABS_PORTAL",
        json.dumps(
            {
                "conn_type": "http",
                "host": INLABS_HOST,
                "login": inlabs_credentials.user,
                "password": inlabs_credentials.password,
            }
        ),
    )


@pytest.fixture(scope="session")
def inlabs_session(inlabs_credentials):
    session = requests.Session()
    session.post(
        urljoin(INLABS_HOST, "logar.php"),
        data={
            "email": inlabs_credentials.user,
            "password": inlabs_credentials.password,
        },
        timeout=TIMEOUT,
    )
    if not session.cookies.get("inlabs_session_cookie"):
        # Credencial inválida é o defeito que este teste existe para pegar.
        pytest.fail("Login no INLABS rejeitado: confira usuário/senha do .env")
    return session


def _has_edition(session: requests.Session, day: date) -> bool:
    response = session.get(
        urljoin(INLABS_HOST, f"index.php?p={day.isoformat()}"),
        headers=_LIST_HEADERS,
        timeout=TIMEOUT,
    )
    links = BeautifulSoup(response.text, "html.parser").find_all(
        "a", title="Baixar Arquivo"
    )
    return any(link.get("href", "").endswith(".zip") for link in links)


@pytest.fixture(scope="session")
def reference_date(inlabs_session) -> date:
    """Edição mais recente (dia útil) que existe no INLABS."""
    today = date.today()
    for days_back in range(1, MAX_DAYS_BACK + 1):
        day = today - timedelta(days=days_back)
        if day.weekday() < 5 and _has_edition(inlabs_session, day):
            return day
    pytest.skip(f"Nenhuma edição no INLABS nos últimos {MAX_DAYS_BACK} dias")
