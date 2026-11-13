"""Um YAML inválido não deve impedir a geração das demais DAGs (#266)."""

import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import dou_dag_generator
from dou_dag_generator import DouDigestDagGenerator

VALID_YAML = """\
dag:
  id: dag_valida_ao_lado_de_invalidas
  description: DAG de teste
  search:
    terms:
      - dados abertos
  report:
    emails:
      - destination@economia.gov.br
    subject: "Teste do Ro-dou"
"""

INVALID_SCHEMA_YAML = """\
dag:
  id: dag_com_schema_invalido
  description: DAG de teste
  search:
    terms:
      - dados abertos
"""

INVALID_SYNTAX_YAML = """\
dag:
  id: dag_com_sintaxe_invalida
  description: [sem fechar
"""


def test_invalid_yaml_does_not_block_other_dags(tmp_path, caplog):
    (tmp_path / "a_schema_invalido.yaml").write_text(INVALID_SCHEMA_YAML, encoding="utf-8")
    (tmp_path / "b_sintaxe_invalida.yml").write_text(INVALID_SYNTAX_YAML, encoding="utf-8")
    (tmp_path / "c_valida.yaml").write_text(VALID_YAML, encoding="utf-8")

    generator = DouDigestDagGenerator()
    generator.YAMLS_DIR_LIST = [str(tmp_path)]

    try:
        with caplog.at_level(logging.ERROR):
            generator.generate_dags()

        assert "dag_valida_ao_lado_de_invalidas" in vars(dou_dag_generator)
        assert "dag_com_schema_invalido" not in vars(dou_dag_generator)
        assert "dag_com_sintaxe_invalida" not in vars(dou_dag_generator)
        assert "a_schema_invalido.yaml" in caplog.text
        assert "b_sintaxe_invalida.yml" in caplog.text
    finally:
        vars(dou_dag_generator).pop("dag_valida_ao_lado_de_invalidas", None)
