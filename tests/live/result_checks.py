"""Validação do contrato de resultado compartilhada pelos testes live."""

import pytest
from airflow.utils.state import DagRunState, TaskInstanceState

REQUIRED_ITEM_FIELDS = ("title", "href", "abstract", "date")
SEARCH_TASK = "exec_searchs.exec_search_1"


def assert_valid_search_result(result: dict, terms: list[str]) -> set[str]:
    """Valida grupo -> termo -> departamento -> itens e devolve os termos que
    tiveram resultado. Não exige contagem: os dados reais mudam todo dia."""
    assert result, "a busca não retornou nenhum resultado"
    matched = set()
    for by_term in result.values():
        for term, by_department in by_term.items():
            # O INLABS agrupa o artigo que casa mais de um termo sob a chave
            # "termo1, termo2".
            found_terms = term.split(", ")
            for found in found_terms:
                assert found in terms, f"termo inesperado no resultado: {found!r}"
            for department, items in by_department.items():
                assert items, f"{term!r}/{department!r}: lista de itens vazia"
                for item in items:
                    for field in REQUIRED_ITEM_FIELDS:
                        assert item.get(field), f"{term!r}/{department!r}: item sem {field!r}"
                    assert item["href"].startswith(("http://", "https://"))
            matched.update(found_terms)
    return matched


def get_search_result(dag_run) -> dict:
    """Resultado da busca (XCom da task de busca) de uma execução de DAG."""
    ti = dag_run.get_task_instance(SEARCH_TASK)
    return ti.xcom_pull(task_ids=SEARCH_TASK)["result"]


def check_search_run(dag_run, mock_send_email, terms: list[str], where: str) -> None:
    """Valida a execução de uma DAG de busca (e-mail mockado).

    Os termos das DAGs de exemplo são fixos: se não houver resultado na data, o
    teste é pulado com aviso, pois não há o que validar."""
    assert dag_run.state == DagRunState.SUCCESS
    result = get_search_result(dag_run)
    if not result:
        pytest.skip(f"Sem resultados em {where} para os termos {terms}; nada a validar")
    matched = assert_valid_search_result(result, terms)

    assert dag_run.get_task_instance("notify_email").state == TaskInstanceState.SUCCESS
    mock_send_email.assert_called_once()
    html = mock_send_email.call_args.kwargs["html_content"].lower()
    for term in matched:
        assert term in html
