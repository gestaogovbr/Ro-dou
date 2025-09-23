"""Test validation of yaml files according to the defined schemas."""

import glob
import os
import sys

from pydantic import ValidationError
import pytest
import yaml

# add module path so we can import from other modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))
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


@pytest.mark.parametrize(
    "field,invalid_value,error_message",
    [
        ("sources", ["INVALID_SOURCE"], "Invalid source 'INVALID_SOURCE'"),
        ("date", "INVALID_DATE", "Invalid date 'INVALID_DATE'"),
        ("dou_sections", ["INVALID_SECTION"], "Invalid DOU section 'INVALID_SECTION'"),
        ("field", "INVALID_FIELD", "Invalid field 'INVALID_FIELD'"),
        ("pubtype", "INVALID_PUBTYPE", "Input should be a valid list"),
        ("pubtype", [123, "valid_string"], "Input should be a valid string"),
    ],
)
def test_domain_validation_invalid_values(field, invalid_value, error_message):
    """Test that invalid domain values are rejected by validation"""
    base_config = {
        "dag": {
            "id": "test_dag",
            "description": "Test DAG with invalid domain values",
            "search": {
                "terms": ["test_term"],
            },
            "report": {
                "emails": ["test@example.com"],
                "subject": "Test Subject",
            },
        }
    }
    
    # Set the invalid field value
    base_config["dag"]["search"][field] = invalid_value
    
    with pytest.raises(ValidationError) as exc_info:
        RoDouConfig(**base_config)
    
    assert error_message in str(exc_info.value)


@pytest.mark.parametrize(
    "field,valid_values",
    [
        ("sources", ["DOU"]),
        ("sources", ["QD"]),
        ("sources", ["INLABS"]),
        ("sources", ["DOU", "QD", "INLABS"]),
        ("date", "DIA"),
        ("date", "SEMANA"),
        ("date", "MES"),
        ("date", "ANO"),
        ("dou_sections", ["SECAO_1"]),
        ("dou_sections", ["SECAO_2", "SECAO_3"]),
        ("dou_sections", ["TODOS"]),
        ("dou_sections", ["EDICAO_EXTRA", "EDICAO_SUPLEMENTAR"]),
        ("field", "TUDO"),
        ("field", "TITULO"),
        ("field", "CONTEUDO"),
        ("pubtype", ["PORTARIA"]),
        ("pubtype", ["DECRETO", "RESOLUÇÃO"]),
        ("pubtype", ["ATO", "EDITAL", "EXTRATO"]),
        ("pubtype", ["CUSTOM_TYPE", "ANOTHER_TYPE"]),
    ],
)
def test_domain_validation_valid_values(field, valid_values):
    """Test that valid domain values are accepted by validation"""
    base_config = {
        "dag": {
            "id": "test_dag",
            "description": "Test DAG with valid domain values",
            "search": {
                "terms": ["test_term"],
            },
            "report": {
                "emails": ["test@example.com"],
                "subject": "Test Subject",
            },
        }
    }
    
    # Set the valid field value
    base_config["dag"]["search"][field] = valid_values
    
    # Should not raise any validation error
    config = RoDouConfig(**base_config)
    assert isinstance(config, RoDouConfig)

