"""Unit tests for TermSelector."""

import json
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from utils.select_terms import TermSelector


@pytest.fixture()
def term_selector() -> TermSelector:
    return TermSelector()


class TestSelectTermsFromAirflowVariable:
    def test_json_list_string(self, term_selector):
        with patch(
            "utils.select_terms.Variable.get",
            return_value='["term1", "term2", "term3"]',
        ):
            result = term_selector.select_terms_from_airflow_variable("my_var")
        assert result == ["term1", "term2", "term3"]

    def test_multiline_text_string(self, term_selector):
        with patch(
            "utils.select_terms.Variable.get", return_value="term1\nterm2\nterm3"
        ):
            result = term_selector.select_terms_from_airflow_variable("my_var")
        assert result == ["term1", "term2", "term3"]

    def test_already_a_list(self, term_selector):
        with patch("utils.select_terms.Variable.get", return_value=["term1", "term2"]):
            result = term_selector.select_terms_from_airflow_variable("my_var")
        assert result == ["term1", "term2"]

    def test_single_term_string(self, term_selector):
        with patch("utils.select_terms.Variable.get", return_value="only_term"):
            result = term_selector.select_terms_from_airflow_variable("my_var")
        assert result == ["only_term"]

    def test_json_list_with_whitespace(self, term_selector):
        with patch("utils.select_terms.Variable.get", return_value='  ["a", "b"]'):
            result = term_selector.select_terms_from_airflow_variable("my_var")
        assert result == ["a", "b"]

    def test_raises_key_error_when_variable_not_found(self, term_selector):
        with patch("utils.select_terms.Variable.get", side_effect=KeyError("my_var")):
            with pytest.raises(KeyError, match="my_var"):
                term_selector.select_terms_from_airflow_variable("my_var")


class TestSelectTermsFromDb:
    def _make_connection(self, conn_type: str):
        conn = MagicMock()
        conn.conn_type = conn_type
        return conn

    def test_postgres_returns_json(self, term_selector):
        df = pd.DataFrame({"term": ["SILVA", "SOUZA"], "group": ["EPPGG", "ATI"]})
        mock_hook = MagicMock()
        mock_hook.get_pandas_df.return_value = df

        with patch(
            "utils.select_terms.BaseHook.get_connection",
            return_value=self._make_connection("postgres"),
        ), patch("utils.select_terms.PostgresHook", return_value=mock_hook):
            result = term_selector.select_terms_from_db(
                "SELECT * FROM terms", "my_pg_conn"
            )

        parsed = json.loads(result)
        assert "term" in parsed
        assert "group" in parsed

    def test_postgresql_conn_type_also_accepted(self, term_selector):
        df = pd.DataFrame({"term": ["SILVA"]})
        mock_hook = MagicMock()
        mock_hook.get_pandas_df.return_value = df

        with patch(
            "utils.select_terms.BaseHook.get_connection",
            return_value=self._make_connection("postgresql"),
        ), patch("utils.select_terms.PostgresHook", return_value=mock_hook):
            result = term_selector.select_terms_from_db(
                "SELECT term FROM terms", "my_pg_conn"
            )

        assert json.loads(result) is not None

    def test_mssql_returns_json(self, term_selector):
        df = pd.DataFrame({"term": ["JOSE"], "cargo": ["ATI"]})
        mock_hook = MagicMock()
        mock_hook.get_pandas_df.return_value = df
        mock_mssql_hook_class = MagicMock(return_value=mock_hook)

        with patch(
            "utils.select_terms.BaseHook.get_connection",
            return_value=self._make_connection("mssql"),
        ), patch("utils.select_terms.MsSqlHook", mock_mssql_hook_class):
            result = term_selector.select_terms_from_db(
                "SELECT * FROM terms", "my_mssql_conn"
            )

        assert "term" in json.loads(result)

    def test_mssql_raises_runtime_error_when_hook_unavailable(self, term_selector):
        with patch(
            "utils.select_terms.BaseHook.get_connection",
            return_value=self._make_connection("mssql"),
        ), patch("utils.select_terms.MsSqlHook", None):
            with pytest.raises(
                RuntimeError, match="apache-airflow-providers-microsoft-mssql"
            ):
                term_selector.select_terms_from_db(
                    "SELECT * FROM terms", "my_mssql_conn"
                )

    def test_unsupported_conn_type_raises_exception(self, term_selector):
        with patch(
            "utils.select_terms.BaseHook.get_connection",
            return_value=self._make_connection("sqlite"),
        ):
            with pytest.raises(Exception, match="não suportado"):
                term_selector.select_terms_from_db(
                    "SELECT * FROM terms", "my_sqlite_conn"
                )

    def test_strips_whitespace_and_replaces_null(self, term_selector):
        df = pd.DataFrame({"term": ["  SILVA  ", None], "cargo": [" ATI ", "EPPGG"]})
        mock_hook = MagicMock()
        mock_hook.get_pandas_df.return_value = df

        with patch(
            "utils.select_terms.BaseHook.get_connection",
            return_value=self._make_connection("postgres"),
        ), patch("utils.select_terms.PostgresHook", return_value=mock_hook):
            result = term_selector.select_terms_from_db(
                "SELECT * FROM terms", "my_pg_conn"
            )

        parsed = json.loads(result)
        terms = list(parsed["term"].values())
        assert "SILVA" in terms
        assert "" in terms
        assert "ATI" in list(parsed["cargo"].values())
