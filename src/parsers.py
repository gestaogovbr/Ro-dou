"""Abstract and concrete classes to parse DAG configuration from a file."""

import textwrap
import os
import sys

from typing import List, Tuple
import yaml

from airflow import Dataset
from airflow.models import Variable

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from schemas import RoDouConfig, DAGConfig


class YAMLParser:
    """Parses YAML file and get the DAG parameters.

    It guarantees that mandatory fields are in place and are properly
    defined providing clear error messages.
    """

    def __init__(self, filepath: str):
        self.filepath = filepath

    def read(self) -> dict:
        """Reads the contents of the YAML file."""
        with open(self.filepath, "r", encoding="utf-8") as file:
            dag_config_dict = yaml.safe_load(file)
        return dag_config_dict

    def parse(self) -> DAGConfig:
        """Processes the config file in order to instantiate the DAG in
        Airflow.
        """
        config = RoDouConfig(**self.read())
        return config.dag

    def _get_terms_params(self, search) -> Tuple[List[str], str, str]:
        """Parses the `terms` config property handling different options."""
        terms = self._try_get(search, "terms")
        sql = None
        conn_id = None

        if isinstance(terms, dict):
            if "from_airflow_variable" in terms:
                term_list = terms.get("from_airflow_variable")

            elif "from_db_select" in terms:
                from_db_select = terms.get("from_db_select")
                terms = []
                sql = self._try_get(from_db_select, "sql")
                conn_id = self._try_get(from_db_select, "conn_id")
            else:
                raise ValueError(
                    "O campo `terms` aceita como valores válidos "
                    "uma lista de strings ou parâmetros do tipo "
                    "`from_airflow_variable` ou `from_db_select`."
                )

        return terms, sql, conn_id

    def _try_get(self, variable: dict, field, error_msg=None):
        """Tries to retrieve mandatory property named `field` from
        `variable` dict and raises appropriate message"""
        try:
            return variable[field]
        except KeyError:
            if not error_msg:
                error_msg = f"O campo `{field}` é obrigatório."
            file_name = self.filepath.split("/")[-1]
            error_msg = f"Erro no arquivo {file_name}: {error_msg}"
            raise ValueError(error_msg)
