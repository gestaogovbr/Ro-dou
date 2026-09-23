"""Unit tests for TermSelector."""

import json
from unittest.mock import MagicMock, patch

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


ALLOWED_CONN_IDS = '["my_pg_conn", "my_mssql_conn", "my_sqlite_conn"]'


def _make_connection(conn_type: str):
    conn = MagicMock()
    conn.conn_type = conn_type
    return conn


def _make_hook(rows, columns):
    """Hook whose DB-API connection returns ``rows`` with ``columns``."""
    cursor = MagicMock()
    cursor.description = [(column,) for column in columns]
    cursor.fetchmany.return_value = rows
    db_conn = MagicMock()
    db_conn.cursor.return_value = cursor
    hook = MagicMock()
    hook.get_conn.return_value = db_conn
    return hook, db_conn, cursor


@pytest.fixture()
def allowed_conn_ids():
    with patch("utils.select_terms.Variable.get", return_value=ALLOWED_CONN_IDS):
        yield


@pytest.mark.usefixtures("allowed_conn_ids")
class TestSelectTermsFromDb:
    def test_postgres_returns_json(self, term_selector):
        hook, _, _ = _make_hook([("SILVA", "EPPGG"), ("SOUZA", "ATI")], ["term", "group"])

        with patch(
            "utils.select_terms.BaseHook.get_connection",
            return_value=_make_connection("postgres"),
        ), patch("utils.select_terms.PostgresHook", return_value=hook):
            result = term_selector.select_terms_from_db(
                "SELECT * FROM terms", "my_pg_conn"
            )

        parsed = json.loads(result)
        assert list(parsed["term"].values()) == ["SILVA", "SOUZA"]
        assert list(parsed["group"].values()) == ["EPPGG", "ATI"]

    def test_postgres_runs_in_read_only_transaction(self, term_selector):
        hook, db_conn, cursor = _make_hook([("SILVA",)], ["term"])

        with patch(
            "utils.select_terms.BaseHook.get_connection",
            return_value=_make_connection("postgres"),
        ), patch("utils.select_terms.PostgresHook", return_value=hook):
            term_selector.select_terms_from_db("SELECT term FROM terms", "my_pg_conn")

        executed = [call.args[0] for call in cursor.execute.call_args_list]
        assert executed[0] == "SET TRANSACTION READ ONLY"
        assert executed[1].startswith("SET LOCAL statement_timeout")
        assert executed[2] == "SELECT term FROM terms"
        db_conn.rollback.assert_called_once()
        db_conn.close.assert_called_once()

    def test_postgresql_conn_type_also_accepted(self, term_selector):
        hook, _, _ = _make_hook([("SILVA",)], ["term"])

        with patch(
            "utils.select_terms.BaseHook.get_connection",
            return_value=_make_connection("postgresql"),
        ), patch("utils.select_terms.PostgresHook", return_value=hook):
            result = term_selector.select_terms_from_db(
                "SELECT term FROM terms", "my_pg_conn"
            )

        assert json.loads(result) is not None

    def test_mssql_returns_json(self, term_selector):
        hook, db_conn, cursor = _make_hook([("JOSE", "ATI")], ["term", "cargo"])
        mock_mssql_hook_class = MagicMock(return_value=hook)

        with patch(
            "utils.select_terms.BaseHook.get_connection",
            return_value=_make_connection("mssql"),
        ), patch("utils.select_terms.MsSqlHook", mock_mssql_hook_class):
            result = term_selector.select_terms_from_db(
                "SELECT * FROM terms", "my_mssql_conn"
            )

        assert "term" in json.loads(result)
        cursor.execute.assert_called_once_with("SELECT * FROM terms")
        db_conn.rollback.assert_called_once()

    def test_mssql_raises_runtime_error_when_hook_unavailable(self, term_selector):
        with patch(
            "utils.select_terms.BaseHook.get_connection",
            return_value=_make_connection("mssql"),
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
            return_value=_make_connection("sqlite"),
        ):
            with pytest.raises(Exception, match="não suportado"):
                term_selector.select_terms_from_db(
                    "SELECT * FROM terms", "my_sqlite_conn"
                )

    def test_strips_whitespace_and_replaces_null(self, term_selector):
        hook, _, _ = _make_hook(
            [("  SILVA  ", " ATI "), (None, "EPPGG")], ["term", "cargo"]
        )

        with patch(
            "utils.select_terms.BaseHook.get_connection",
            return_value=_make_connection("postgres"),
        ), patch("utils.select_terms.PostgresHook", return_value=hook):
            result = term_selector.select_terms_from_db(
                "SELECT * FROM terms", "my_pg_conn"
            )

        parsed = json.loads(result)
        terms = list(parsed["term"].values())
        assert "SILVA" in terms
        assert "" in terms
        assert "ATI" in list(parsed["cargo"].values())

    def test_rejects_too_many_rows(self, term_selector):
        hook, db_conn, _ = _make_hook([("x",)] * 3, ["term"])

        with patch(
            "utils.select_terms.BaseHook.get_connection",
            return_value=_make_connection("postgres"),
        ), patch("utils.select_terms.PostgresHook", return_value=hook), patch(
            "utils.select_terms.MAX_TERM_ROWS", 2
        ):
            with pytest.raises(ValueError, match="mais de 2 linhas"):
                term_selector.select_terms_from_db("SELECT term FROM t", "my_pg_conn")

        db_conn.rollback.assert_called_once()

    def test_rejects_non_select_before_connecting(self, term_selector):
        with patch("utils.select_terms.BaseHook.get_connection") as get_connection:
            with pytest.raises(ValueError, match="SELECT"):
                term_selector.select_terms_from_db(
                    "SELECT 1; DROP TABLE terms", "my_pg_conn"
                )

        get_connection.assert_not_called()


class TestConnIdAllowlist:
    @pytest.mark.parametrize("variable_value", [None, ""])
    def test_denies_everything_when_variable_is_missing(
        self, term_selector, variable_value
    ):
        with patch(
            "utils.select_terms.Variable.get", return_value=variable_value
        ), patch("utils.select_terms.BaseHook.get_connection") as get_connection:
            with pytest.raises(ValueError, match="ro_dou_allowed_terms_conn_ids"):
                term_selector.select_terms_from_db("SELECT 1", "my_pg_conn")

        get_connection.assert_not_called()

    def test_denies_conn_id_not_listed(self, term_selector):
        with patch(
            "utils.select_terms.Variable.get", return_value='["other_conn"]'
        ), patch("utils.select_terms.BaseHook.get_connection") as get_connection:
            with pytest.raises(ValueError, match="'inlabs_db' não está autorizada"):
                term_selector.select_terms_from_db("SELECT 1", "inlabs_db")

        get_connection.assert_not_called()

    @pytest.mark.parametrize(
        "variable_value",
        [
            '["a_conn", "my_pg_conn"]',
            ["a_conn", "my_pg_conn"],
            "a_conn, my_pg_conn",
            "a_conn\nmy_pg_conn\n",
        ],
    )
    def test_accepts_supported_variable_formats(self, term_selector, variable_value):
        hook, _, _ = _make_hook([("SILVA",)], ["term"])

        with patch(
            "utils.select_terms.Variable.get", return_value=variable_value
        ), patch(
            "utils.select_terms.BaseHook.get_connection",
            return_value=_make_connection("postgres"),
        ), patch("utils.select_terms.PostgresHook", return_value=hook):
            result = term_selector.select_terms_from_db("SELECT term FROM t", "my_pg_conn")

        assert "term" in json.loads(result)
