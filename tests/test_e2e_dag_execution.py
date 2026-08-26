"""End-to-end test for a complete Ro-dou DAG execution.

Builds a real DAG from YAML and runs it with Airflow's ``DAG.test()``,
covering the full flow: search -> branch -> notification/skip, including
XCom data passing.

Only the DOU HTTP API and email sending are mocked. YAML parsing, DAG
assembly, branching, and report generation run normally.

The patches use top-level module names because the Ro-dou source modifies
``sys.path`` and imports modules with bare names (e.g. ``hooks.dou_hook``).
Therefore, patching ``dags.ro_dou_src.*`` would not affect the modules
actually used by the DAG. See the ``dag_gen`` fixture in ``conftest.py``.
"""

import os
from unittest.mock import patch

import pytest
from airflow.utils.state import DagRunState, TaskInstanceState

from dags.ro_dou_src.dou_dag_generator import DouDigestDagGenerator
from dags.ro_dou_src.parsers import YAMLParser

CONFIG_FILE = "basic_example.yaml"
MATCHED_TERM = "dados abertos"
RECIPIENT = "destination@economia.gov.br"

FAKE_MATCH = {
    "section": "do1",
    "title": "Portaria sobre dados abertos",
    "href": "https://www.in.gov.br/web/dou/-/fake-1",
    "abstract": "Texto sobre <span class='highlight'>dados abertos</span> no governo.",
    "date": "25/08/2026",
    "id": "1",
    "display_date_sortable": "2026-08-25",
    "hierarchyList": "Ministerio da Gestao",
    "hierarchyStr": "Ministerio da Gestao",
    "arttype": "Portaria",
}


@pytest.fixture()
def basic_example_dag(dag_gen: DouDigestDagGenerator):
    """Builds the real DAG for `basic_example.yaml` (DOU source, 3 terms,
    single e-mail report, `skip_null` defaulting to True)."""
    filepath = os.path.join(dag_gen.YAMLS_DIR, "examples_and_tests", CONFIG_FILE)
    specs = dag_gen.parser(filepath).parse()
    return dag_gen.create_dag(specs, filepath)


def _fake_search_text(matched_terms: set):
    """Stand-in for `DOUHook.search_text`: returns a canned match for
    any term in `matched_terms`, nothing otherwise. Mirrors the real
    method's signature so it can be swapped in via `unittest.mock.patch`.
    """

    def _search(
        self,
        search_term,
        sections,
        reference_date=None,
        search_date=None,
        field=None,
        is_exact_search=True,
        with_retry=True,
    ):
        return [FAKE_MATCH] if search_term in matched_terms else []

    return _search


def test_e2e_dag_run_sends_email_report_when_terms_match(basic_example_dag):
    """A DOU match on one of the three configured terms should flow
    through search -> branch -> notify_email, landing in the e-mail
    HTML content with the report subject and recipient from the YAML."""
    with patch(
        "hooks.dou_hook.DOUHook.search_text", new=_fake_search_text({MATCHED_TERM})
    ), patch("searchers.time.sleep"), patch(
        "notification.email_sender.send_email"
    ) as mock_send_email:
        dag_run = basic_example_dag.test()

    assert dag_run.state == DagRunState.SUCCESS
    mock_send_email.assert_called_once()
    _, kwargs = mock_send_email.call_args
    assert kwargs["to"] == [RECIPIENT]
    assert "Teste do Ro-dou" in kwargs["subject"]
    assert "Portaria sobre dados abertos" in kwargs["html_content"]
    assert MATCHED_TERM in kwargs["html_content"].lower()

    assert dag_run.get_task_instance("notify_email").state == TaskInstanceState.SUCCESS
    assert (
        dag_run.get_task_instance("skip_notification").state
        == TaskInstanceState.SKIPPED
    )


def test_e2e_dag_run_skips_notification_when_nothing_matches(basic_example_dag):
    """When no term matches anything, the config's default `skip_null:
    true` must route the branch to `skip_notification` and no e-mail
    should ever be sent."""
    with patch(
        "hooks.dou_hook.DOUHook.search_text", new=_fake_search_text(set())
    ), patch("searchers.time.sleep"), patch(
        "notification.email_sender.send_email"
    ) as mock_send_email:
        dag_run = basic_example_dag.test()

    assert dag_run.state == DagRunState.SUCCESS
    mock_send_email.assert_not_called()

    assert dag_run.get_task_instance("notify_email").state == TaskInstanceState.SKIPPED
    assert (
        dag_run.get_task_instance("skip_notification").state
        == TaskInstanceState.SUCCESS
    )
