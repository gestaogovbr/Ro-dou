"""Test validation of yaml files according to the defined schemas."""

import glob
import os
import sys

from pydantic import ValidationError
import pytest
import yaml

# add module path so we can import from other modules
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from schemas import RoDouConfig

YAMLS_DIR = "../dags/ro_dou/dag_confs"


@pytest.mark.parametrize(
    "data_file",
    [
        data_file
        for data_file in glob.glob(f"{YAMLS_DIR}/**/*.yml", recursive=True)
        + glob.glob(f"{YAMLS_DIR}/**/*.yaml", recursive=True)
    ],
)
def test_pydantic_validation(data_file):
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

