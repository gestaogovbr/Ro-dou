"""Module for selecting terms."""

import ast
import json
from contextlib import closing

import pandas as pd

from airflow.sdk import Variable
from airflow.sdk.bases.hook import BaseHook

try:
    from airflow.providers.microsoft.mssql.hooks.mssql import MsSqlHook
except ImportError:
    MsSqlHook = None
from airflow.providers.postgres.hooks.postgres import PostgresHook

from utils.sql_guard import validate_select_only

# Variable do Airflow (ou AIRFLOW_VAR_RO_DOU_ALLOWED_TERMS_CONN_IDS) com os
# conn_ids que os YAMLs podem usar em `from_db_select`. Sem ela, nenhuma
# conexão é permitida.
ALLOWED_CONN_IDS_VARIABLE = "ro_dou_allowed_terms_conn_ids"
# Tempo máximo da consulta (PostgreSQL), em milissegundos.
STATEMENT_TIMEOUT_MS = 60_000
# Número máximo de linhas aceitas como termos.
MAX_TERM_ROWS = 10_000


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
            ValueError: If ``sql`` is not a single SELECT statement, if
                ``conn_id`` is not listed in the Airflow Variable
                ``ro_dou_allowed_terms_conn_ids`` or if the query returns more
                than ``MAX_TERM_ROWS`` rows.
            RuntimeError: If MSSQL is requested but the provider package is not
                installed.
            Exception: If the connection type is not supported.
        """
        validate_select_only(sql)
        _ensure_conn_id_allowed(conn_id)

        conn_type = BaseHook.get_connection(conn_id).conn_type
        if conn_type == "mssql":
            if MsSqlHook is None:
                raise RuntimeError(
                    "MsSqlHook indisponível: instale 'apache-airflow-providers-microsoft-mssql' para usar recursos MSSQL."
                )
            db_hook = MsSqlHook(conn_id)
            session_statements = []
        elif conn_type in ("postgresql", "postgres"):
            db_hook = PostgresHook(conn_id)
            # Bloqueia escrita e limita o tempo mesmo que o usuário do banco
            # tenha mais permissões do que o necessário.
            session_statements = [
                "SET TRANSACTION READ ONLY",
                f"SET LOCAL statement_timeout = {STATEMENT_TIMEOUT_MS}",
            ]
        else:
            raise Exception("Tipo de banco de dados não suportado: ", conn_type)

        terms_df = _fetch_dataframe(db_hook, sql, session_statements)
        # Remove unnecessary spaces and change null for ''
        terms_df = terms_df.map(lambda x: str.strip(x) if pd.notnull(x) else "")

        return terms_df.to_json(orient="columns")


def _allowed_conn_ids() -> set[str]:
    """Lê a lista de conn_ids permitidos (JSON ou separada por vírgula/linha)."""
    raw_value = Variable.get(ALLOWED_CONN_IDS_VARIABLE, default=None)
    if not raw_value:
        return set()

    if isinstance(raw_value, list):
        values = raw_value
    else:
        raw_value = str(raw_value).strip()
        if raw_value.startswith("["):
            values = json.loads(raw_value)
        else:
            values = raw_value.replace("\n", ",").split(",")

    return {str(value).strip() for value in values if str(value).strip()}


def _ensure_conn_id_allowed(conn_id: str) -> None:
    """Impede que o YAML use conexões não autorizadas pela operação."""
    allowed = _allowed_conn_ids()
    if conn_id not in allowed:
        raise ValueError(
            f"A conexão '{conn_id}' não está autorizada para `from_db_select`. "
            f"Inclua-a na Variable do Airflow '{ALLOWED_CONN_IDS_VARIABLE}' "
            "(lista JSON ou separada por vírgulas) e garanta que o usuário "
            "dessa conexão tenha apenas permissão de leitura nas tabelas de termos."
        )


def _fetch_dataframe(db_hook, sql: str, session_statements: list[str]) -> pd.DataFrame:
    """Executa a consulta numa transação descartada ao final (rollback)."""
    with closing(db_hook.get_conn()) as conn:
        try:
            cursor = conn.cursor()
            try:
                for statement in session_statements:
                    cursor.execute(statement)
                cursor.execute(sql)
                columns = [column[0] for column in cursor.description or []]
                rows = cursor.fetchmany(MAX_TERM_ROWS + 1)
            finally:
                cursor.close()
        finally:
            conn.rollback()

    if len(rows) > MAX_TERM_ROWS:
        raise ValueError(
            f"A consulta de `from_db_select` retornou mais de {MAX_TERM_ROWS} "
            "linhas. Refine o SELECT."
        )

    return pd.DataFrame.from_records(rows, columns=columns)
