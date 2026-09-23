"""Unit tests for the `from_db_select` SQL validation."""

import pytest
from pydantic import ValidationError

from schemas import DBSelect
from utils.sql_guard import validate_select_only


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT nome, grupo FROM dou_inlabs.servidores;",
        "select 'cloroquina' as TERMO UNION select 'ivermectina' as TERMO",
        "WITH ativos AS (SELECT nome FROM t WHERE ativo = 1) SELECT nome FROM ativos",
        "SELECT REPLACE(nome, 'x', 'y') AS termo FROM t",
        "SELECT TOP 100 nome FROM dbo.t ORDER BY nome",
        "SELECT nome FROM t WHERE descricao LIKE '%update%' -- comentário",
        "/* termos */ SELECT CAST(x AS varchar(10)) FROM t",
    ],
)
def test_accepts_read_only_select(sql):
    assert validate_select_only(sql) == sql


@pytest.mark.parametrize(
    "sql",
    [
        "",
        "   ",
        "-- apenas comentário",
        "DELETE FROM t",
        "UPDATE t SET nome = 'x'",
        "INSERT INTO t VALUES (1)",
        "DROP TABLE t",
        "TRUNCATE t",
        "EXEC sp_executesql N'DROP TABLE t'",
        "COPY t TO '/tmp/x'",
        "GRANT ALL ON t TO public",
        "SELECT 1; DROP TABLE t",
        "SELECT 1; SELECT 2",
        "SELECT * INTO copia FROM t",
        "WITH x AS (DELETE FROM t RETURNING *) SELECT * FROM x",
        "SELECT nome FROM t FOR UPDATE",
        "MERGE INTO t USING s ON 1 = 1 WHEN MATCHED THEN DELETE",
    ],
)
def test_rejects_non_select(sql):
    with pytest.raises(ValueError):
        validate_select_only(sql)


def test_schema_rejects_invalid_sql():
    with pytest.raises(ValidationError, match="SELECT"):
        DBSelect(sql="DELETE FROM terms", conn_id="example_database_conn")


def test_schema_accepts_select():
    config = DBSelect(sql="SELECT termo FROM terms", conn_id="example_database_conn")

    assert config.sql == "SELECT termo FROM terms"
