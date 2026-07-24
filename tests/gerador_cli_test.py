"""Testa o CLI (POC) de geração de YAML: tools/gerador_cli.py."""

import os
import re
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

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def test_modo_interativo_gera_yaml_valido():
    cli = next(path for path in _CLI_PATHS if os.path.exists(path))
    src = next(path for path in _SRC_PATHS if os.path.isdir(path))
    respostas = "\n".join(
        [
            "teste_poc_cli",  # id
            "Teste do modo interativo do gerador CLI",  # description
            "",  # schedule (pula)
            "",  # owner (pula)
            "",  # callback (pula)
            "",  # fonte (pula; usa DOU)
            "dados abertos, governo aberto",  # termos
            "",  # terms_ignore (pula)
            "",  # dou_sections (pula; default TODOS)
            "destination@economia.gov.br",  # e-mails
            "",  # subject (pula)
            "",  # attach_csv (pula; default não)
            "",  # skip_null (pula; default sim)
        ]
    ) + "\n"
    resultado = subprocess.run(
        [sys.executable, cli, "--stdout"],
        input=respostas,
        capture_output=True,
        text=True,
        env={**os.environ, "RO_DOU_SRC_PATH": src},
        check=False,
    )
    assert resultado.returncode == 0, resultado.stderr
    saida = _ANSI.sub("", resultado.stdout)
    yaml_texto = saida.split("── YAML gerado ──\n", 1)[1]
    data = yaml.safe_load(yaml_texto)
    config = RoDouConfig(**data)
    assert config.dag.id == "teste_poc_cli"
    assert config.dag.search[0].terms == ["dados abertos", "governo aberto"]
