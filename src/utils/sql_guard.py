"""Validação das consultas SQL usadas em ``from_db_select``.

A validação é uma camada de defesa em profundidade: ela rejeita comandos
que não sejam uma única consulta de leitura, mas não substitui a lista de
conexões permitidas nem um usuário de banco somente leitura.
"""

import sqlparse
from sqlparse import tokens as T

_ALLOWED_STATEMENT_TYPES = {"SELECT"}

# Palavras-chave que alteram dados, estrutura ou permissões, ou que executam
# código no servidor. São rejeitadas em qualquer posição, inclusive dentro de
# CTEs (ex.: ``WITH x AS (DELETE ... RETURNING *) SELECT ...``).
_FORBIDDEN_KEYWORDS = {
    "INSERT",
    "UPDATE",
    "DELETE",
    "MERGE",
    "UPSERT",
    "REPLACE",
    "INTO",
    "CREATE",
    "ALTER",
    "DROP",
    "TRUNCATE",
    "RENAME",
    "GRANT",
    "REVOKE",
    "EXEC",
    "EXECUTE",
    "CALL",
    "DO",
    "COPY",
    "LOCK",
    "SET",
    "RESET",
    "VACUUM",
    "ANALYZE",
    "BACKUP",
    "RESTORE",
    "SHUTDOWN",
}


def validate_select_only(sql: str) -> str:
    """Garante que ``sql`` contém uma única instrução ``SELECT``.

    Args:
        sql (str): Consulta informada no YAML.

    Returns:
        str: A própria consulta, para uso em validadores.

    Raises:
        ValueError: Se a consulta estiver vazia, tiver mais de uma instrução,
            não for ``SELECT`` ou contiver palavras-chave de escrita/execução.
    """
    if not sql or not sql.strip():
        raise ValueError("A consulta SQL de `from_db_select` está vazia.")

    statements = [
        statement
        for statement in sqlparse.parse(sql)
        if sqlparse.format(statement.value, strip_comments=True).strip(" \n\t;")
    ]

    if len(statements) != 1:
        raise ValueError(
            "`from_db_select.sql` deve conter exatamente uma instrução SELECT."
        )

    statement = statements[0]
    if statement.get_type() not in _ALLOWED_STATEMENT_TYPES:
        raise ValueError(
            "`from_db_select.sql` aceita apenas consultas SELECT "
            f"(tipo encontrado: {statement.get_type()})."
        )

    for token in statement.flatten():
        if token.ttype in T.Keyword and token.normalized in _FORBIDDEN_KEYWORDS:
            raise ValueError(
                "`from_db_select.sql` contém palavra-chave não permitida: "
                f"{token.normalized}."
            )

    return sql
