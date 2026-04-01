"""Module for selecting terms."""

import ast
import pandas as pd

from airflow.models import Variable
from airflow.hooks.base import BaseHook

try:
    from airflow.providers.microsoft.mssql.hooks.mssql import MsSqlHook
except ImportError:
    MsSqlHook = None
from airflow.providers.postgres.hooks.postgres import PostgresHook


class TermSelector:
    """Class for selecting terms."""

    def __init__(self):
        """Initialize the TermSelector."""
        pass

    def select_terms_from_airflow_variable(self, variable: str) -> list:
        """
        Retrieves and processes a list of terms from an Apache Airflow variable.

        This function searches for a specific Airflow variable and converts it into a list
        of terms, supporting both JSON and line-delimited text formats.

        Arguments:
        variable (str): Name of the Airflow variable to be retrieved.

        Returns:
        list: List of terms extracted from the Airflow variable.

        Raises:
        KeyError: When a specified variable was not found in Airflow.

        Examples:
        >>> # For an Airflow variable containing JSON: ["term1", "term2", "term3"]
        >>> terms = self.select_terms_from_airflow_variable("my_json_list")
        >>> print(terms)
        ['term1', 'term2', 'term3']

        >>> # For a variable An Airflow variable containing text separated by lines:
        >>>#term1
        >>>#term2
        >>>#term3
        >>> terms = self.select_terms_from_airflow_variable("my_text_list")
        >>> print (terms)
        ['term1', 'term2', 'term3']

        Note:
        - If the variable value is a list (JSON), it will be parsed with json.loads()
        - Otherwise, it will be treated as a string and split by line breaks
        - Useful for configuring dynamic lists using Airflow variables
        """

        term_list = []
        var_name = variable

        try:
            var_value = Variable.get(var_name)
            # Se já é uma lista, retorna direto
            if isinstance(var_value, list):
                return var_value

            if isinstance(var_value, str):
                if var_value.strip().startswith("["):
                    return ast.literal_eval(var_value)
                else:
                    # Trata como texto separado por linhas
                    return var_value.splitlines()
            return term_list

        except KeyError:
            raise KeyError(f"Airflow variable {var_name} not found.")

    def select_terms_from_db(self, sql: str, conn_id: str):
        """Executes a SQL query and returns the terms to be used in the DOU search.

        The first column of the result set must contain the search terms. The
        optional second column acts as a classifier to group and sort both the
        email report and the generated CSV output.

        Supports MSSQL and PostgreSQL connections (determined via ``conn_id``).

        Arguments:
            sql (str): SQL SELECT statement whose first column contains the terms.
            conn_id (str): Airflow connection ID for the target database.

        Returns:
            str: JSON string (``orient="columns"``) with the query results.

        Raises:
            RuntimeError: If MSSQL is requested but the provider package is not
                installed.
            Exception: If the connection type is not supported.
        """
        conn_type = BaseHook.get_connection(conn_id).conn_type
        if conn_type == "mssql":
            if MsSqlHook is None:
                raise RuntimeError(
                    "MsSqlHook indisponível: instale 'apache-airflow-providers-microsoft-mssql' para usar recursos MSSQL."
                )
            db_hook = MsSqlHook(conn_id)
        elif conn_type in ("postgresql", "postgres"):
            db_hook = PostgresHook(conn_id)
        else:
            raise Exception("Tipo de banco de dados não suportado: ", conn_type)

        terms_df = db_hook.get_pandas_df(sql)
        # Remove unnecessary spaces and change null for ''
        terms_df = terms_df.applymap(lambda x: str.strip(x) if pd.notnull(x) else "")

        return terms_df.to_json(orient="columns")
