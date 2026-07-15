"""Testa o CLI (POC) de geração de YAML: tools/gerador_cli.py."""

import os
import subprocess
import sys

import yaml

# add module path so we can import from other modules
_TESTS_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, _TESTS_DIR)
from schemas import RoDouConfig

# Airflow layout (Docker) and repo-root layout (dev / mount).
_CLI_PATHS = [
    "/opt/airflow/tools/gerador_cli.py",
    os.path.normpath(os.path.join(_TESTS_DIR, "..", "tools", "gerador_cli.py")),
]
_SRC_PATHS = [
    "/opt/airflow/dags/ro_dou_src",
    os.path.normpath(os.path.join(_TESTS_DIR, "..", "src")),
]


def test_modo_flags_gera_yaml_valido():
    cli = next(path for path in _CLI_PATHS if os.path.exists(path))
    src = next(path for path in _SRC_PATHS if os.path.isdir(path))
    resultado = subprocess.run(
        [
            sys.executable, cli,
            "--id", "teste_poc_cli",
            "--description", "Teste do modo por flags do gerador CLI",
            "--terms", "dados abertos",
            "--terms", "governo aberto",
            "--emails", "destination@economia.gov.br",
            "--stdout",
        ],
        capture_output=True,
        text=True,
        env={**os.environ, "RO_DOU_SRC_PATH": src},
        check=False,
    )
    assert resultado.returncode == 0, resultado.stderr
    data = yaml.safe_load(resultado.stdout)
    config = RoDouConfig(**data)
    assert config.dag.id == "teste_poc_cli"
    assert config.dag.search[0].terms == ["dados abertos", "governo aberto"]
