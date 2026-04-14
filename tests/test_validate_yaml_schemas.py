"""Test validation of yaml files according to the defined schemas."""

import glob
import os
import sys

from pydantic import ValidationError
import pytest
import yaml

# add module path so we can import from other modules
_TESTS_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, _TESTS_DIR)
from schemas import RoDouConfig

# Airflow layout (Docker) and repo-root `dag_confs` (dev / mount).
_YAML_DIRS = [
    os.path.normpath(os.path.join(_TESTS_DIR, "..", "dags", "ro_dou", "dag_confs")),
    os.path.normpath(os.path.join(_TESTS_DIR, "..", "dag_confs")),
]


def _collect_yaml_files():
    paths = []
    for d in _YAML_DIRS:
        if not os.path.isdir(d):
            continue
        paths.extend(glob.glob(os.path.join(d, "**", "*.yml"), recursive=True))
        paths.extend(glob.glob(os.path.join(d, "**", "*.yaml"), recursive=True))
    return sorted(set(paths))


_ALL_YAML_FILES = _collect_yaml_files()


@pytest.mark.parametrize(
    "data_file",
    _ALL_YAML_FILES if _ALL_YAML_FILES else [pytest.param(None, id="no_yaml_dirs")],
)
def test_pydantic_validation(data_file):
    if data_file is None:
        pytest.skip("Nenhum diretório de YAML encontrado para validação.")
    with open(data_file) as data_fp:
        data = yaml.safe_load(data_fp)
    try:
        RoDouConfig(**data)
    except ValidationError as e:
        pytest.fail(f"YAML file {data_file} is not valid:\n{e}")


@pytest.mark.parametrize(
    "data",
    [
        {
            "dag": {
                "id": "no_terms_example",
                "description": "DAG de teste sem termos definidos",
                "search": {
                    "sources": ["QD"],
                    "dou_sections": ["SECAO_1"],
                },
                "report": {
                    "emails": ["destination@economia.gov.br"],
                    "subject": "Teste do Ro-dou - Todas as Portarias e Resoluções do MGI",
                },
            }
        }, # no terms provided and QD in source - should raise ValidationError
        {
            "dag": {
                "id": "no_terms_example",

                "description": "DAG de teste sem termos definidos",
                "search": {
                    "sources": ["DOU"],
                    "dou_sections": ["SECAO_1"],
                },
                "report": {
                    "emails": ["destination@economia.gov.br"],
                    "subject": "Teste do Ro-dou - Todas as Portarias e Resoluções do MGI",
                },
            }
        }, # no terms and no pubtype or department provided - should raise ValidationError
        {
            "dag": {
                "id": "no_terms_example",
                "description": "DAG de teste sem termos definidos",
                "search": {
                    "sources": ["DOU"],
                    "dou_sections": ["SECAO_1"],
                    "department": ["Ministério da Gestão e da Inovação em Serviços Públicos"]
                },
                "report": {
                    "emails": ["destination@economia.gov.br"],
                    "subject": "Teste do Ro-dou - Todas as Portarias e Resoluções do MGI",
                },
            }
        }, # department provided - pass
        {
            "dag": {
                "id": "no_terms_example",
                "sources": ["DOU"],
                "description": "DAG de teste sem termos definidos",
                "search": {
                    "sources": ["DOU"],
                    "dou_sections": ["SECAO_1"],
                    "pubtype": ["Portaria", "Resolução"],
                },
                "report": {
                    "emails": ["destination@economia.gov.br"],
                    "subject": "Teste do Ro-dou - Todas as Portarias e Resoluções do MGI",
                },
            }
        }, # pubtype provided - pass
    ],
)
def test_validate_no_terms(data):
    if any(key in data["dag"]["search"] for key in ("department", "pubtype")):
        assert isinstance(RoDouConfig(**data), RoDouConfig)
    else:
        exc_info = pytest.raises(ValidationError, RoDouConfig, **data)
        if "QD" in data["dag"]["search"]["sources"]:
            assert "Os termos de pesquisa são obrigatórios quando a fonte QD é selecionada." \
                in str(exc_info.value)
        else:
            assert "Pelo menos um critério de busca deve ser fornecido" \
                in str(exc_info.value)

