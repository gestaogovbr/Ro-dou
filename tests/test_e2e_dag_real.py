"""End-to-end tests for a complete Ro-dou DAG execution — extended version.

This file builds on the original `test_e2e_dag_execution.py` /
`test_e2e_dag_real.py` idea (build a real DAG from YAML and run it with
Airflow's ``DAG.test()``) and closes three gaps found there:

1. The original tests mocked ``DOUHook.search_text`` directly. That bypasses
   ALL of the hook's real logic (HTTP call, pagination, HTML/JSON parsing,
   section-code mapping). Only the *href* differed between the "fake" and
   "real" versions of the test — everything else, including the mocking
   boundary, was identical. ``test_e2e_dag_real_http_boundary`` below mocks
   one level lower (``requests.get``) with a synthetic-but-structurally-real
   DOU API response, so the actual parsing code in ``hooks/dou_hook.py`` runs.

2. Neither test exercised the `terms_ignore` filter with more than one
   candidate result, so that code path was never really put under test
   even though it runs for real (it's not mocked) whenever
   ``DOUHook.search_text`` is mocked at the higher boundary. (`department`
   is deliberately NOT re-tested here: `searchers_test.py::test_match_department`
   already covers `_match_department` directly, combining `department` and
   `department_ignore` — more thoroughly than an e2e DAG run would.)

3. Neither test covered `skip_null: False`, nor asserted the *complete* task
   graph — only `notify_email` / `skip_notification` were checked, and
   `test_dag_loading.py::test_individual_dag_creation` only asserts
   `len(dag.tasks) > 0`, not which tasks or their dependencies.

Note: an "build every YAML in examples_and_tests" smoke test was
deliberately NOT added here — `test_dag_loading.py::test_all_dags_load_without_errors`
+ `test_yaml_config_files_exist` + `test_individual_dag_creation` already
cover that ground.

Field names used for spec mutation below (`report.skip_null`,
`report.attach_csv`, `search[0].terms_ignore`) were checked against
``schemas.py`` (``SearchConfig`` / ``ReportConfig``): none of the Pydantic
models are ``frozen``, so mutating a deep-copied ``DAGConfig`` before
calling ``create_dag`` is safe and doesn't re-trigger validators
(``validate_assignment`` isn't set). ``Section.SECAO_1.value == "do1"``
(used by the HTTP-boundary test below) is confirmed against
``utils/search_domains.py``. Slack/Discord notification paths, and the
plain `attach_csv=False` email path, already have their own dedicated
tests elsewhere (`slack_sender_test.py`, `discord_sender_test.py`,
`email_sender_test.py::test_send_email`) and are out of scope here.
`email_sender_test.py::test_send_email` never exercises `attach_csv=True`
though, so that specific gap (`test_e2e_dag_attach_csv_sends_csv_file_when_matches_found`
below) is kept.

The patches use top-level module names because the Ro-dou source modifies
``sys.path`` and imports modules with bare names (e.g. ``hooks.dou_hook``).
Patching ``dags.ro_dou_src.*`` would not affect the modules actually used
by the DAG. See the ``dag_gen`` fixture in ``conftest.py``.
"""

import copy
import json
import os
from unittest.mock import Mock, patch

import pytest
from airflow.utils.state import DagRunState, TaskInstanceState

from dags.ro_dou_src.dou_dag_generator import DouDigestDagGenerator

CONFIG_FILE = "basic_example.yaml"
MATCHED_TERM = "dados abertos"
RECIPIENT = "destination@economia.gov.br"

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

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
def basic_example_specs(dag_gen: DouDigestDagGenerator):
    """Parses `basic_example.yaml` into a DAGConfig, without building the DAG
    yet — lets individual tests mutate the specs (e.g. skip_null,
    department) before calling `dag_gen.create_dag(...)`, which is much
    safer than hand-writing new YAML for fields we can't fully verify the
    schema of.
    """
    filepath = os.path.join(
        dag_gen.YAMLS_DIR, "examples_and_tests", CONFIG_FILE
    )
    specs = dag_gen.parser(filepath).parse()
    return specs, filepath


@pytest.fixture()
def basic_example_dag(dag_gen: DouDigestDagGenerator, basic_example_specs):
    """Builds the real DAG for `basic_example.yaml` as-is (unmutated specs)."""
    specs, filepath = basic_example_specs
    return dag_gen.create_dag(specs, filepath)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_search_text(term_to_items: dict):
    """Stand-in for `DOUHook.search_text`, mocked at the hook-method level.

    `term_to_items` maps a search term to the list of raw match dicts it
    should return (so callers can test filters like `department` or
    `terms_ignore` with more than one candidate result, not just a single
    canned match).
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
        return [dict(item) for item in term_to_items.get(search_term, [])]

    return _search


def assert_full_task_graph(dag, *, num_searches: int, notify_task_ids: list):
    """Generic structural assertion, reusable for any Ro-dou DAG built from
    a spec with a single exec_searchs group, one `has_matches` branch, and
    a fixed set of notify tasks. Extend this as new DAG shapes show up
    (e.g. `generate_ai_executive_summary`) so future DAGs can be checked
    without opening each one manually.
    """
    task_ids = set(dag.task_dict.keys())

    expected_search_tasks = {
        f"exec_searchs.exec_search_{i}" for i in range(1, num_searches + 1)
    }
    expected_fixed_tasks = {"has_matches", "skip_notification", *notify_task_ids}

    missing = (expected_search_tasks | expected_fixed_tasks) - task_ids
    assert not missing, f"DAG is missing expected tasks: {missing}"

    has_matches = dag.get_task("has_matches")
    downstream_ids = {t.task_id for t in has_matches.downstream_list}
    assert "skip_notification" in downstream_ids
    for notify_id in notify_task_ids:
        assert notify_id in downstream_ids, (
            f"'{notify_id}' is not downstream of 'has_matches' — "
            "branching would never reach it."
        )

    for search_task_id in expected_search_tasks:
        downstream_of_search = {
            t.task_id for t in dag.get_task(search_task_id).downstream_list
        }
        assert "has_matches" in downstream_of_search, (
            f"'{search_task_id}' does not feed into 'has_matches'."
        )


# ---------------------------------------------------------------------------
# 1. Baseline behavior (kept from the original test, single canned match)
# ---------------------------------------------------------------------------


def test_e2e_dag_run_sends_email_report_when_terms_match(basic_example_dag):
    """A DOU match on one of the three configured terms should flow
    through search -> branch -> notify_email, landing in the e-mail
    HTML content with the report subject and recipient from the YAML."""
    with patch(
        "hooks.dou_hook.DOUHook.search_text",
        new=_fake_search_text({MATCHED_TERM: [FAKE_MATCH]}),
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
        "hooks.dou_hook.DOUHook.search_text", new=_fake_search_text({})
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


# ---------------------------------------------------------------------------
# 2. skip_null: False -> must notify even with zero matches
# ---------------------------------------------------------------------------


def test_e2e_dag_run_notifies_even_without_matches_when_skip_null_false(
    dag_gen: DouDigestDagGenerator, basic_example_specs
):
    """`skip_null` is read at DAG-build time into `has_matches`'s
    op_kwargs, so we mutate a deep copy of the parsed specs before calling
    `create_dag` — no new YAML needed, and no dependency on any field
    whose exact YAML syntax/validation we haven't verified."""
    specs, filepath = basic_example_specs
    mutated_specs = copy.deepcopy(specs)
    mutated_specs.report.skip_null = False

    dag = dag_gen.create_dag(mutated_specs, filepath)

    with patch(
        "hooks.dou_hook.DOUHook.search_text", new=_fake_search_text({})
    ), patch("searchers.time.sleep"), patch(
        "notification.email_sender.send_email"
    ) as mock_send_email:
        dag_run = dag.test()

    assert dag_run.state == DagRunState.SUCCESS
    mock_send_email.assert_called_once()
    assert dag_run.get_task_instance("notify_email").state == TaskInstanceState.SUCCESS
    assert (
        dag_run.get_task_instance("skip_notification").state
        == TaskInstanceState.SKIPPED
    )


def test_e2e_dag_attach_csv_sends_csv_file_when_matches_found(
    dag_gen: DouDigestDagGenerator, basic_example_specs
):
    """`ReportConfig.attach_csv` is a plain bool (confirmed in schemas.py).
    When True and there's at least one match, `EmailSender.send` builds a
    CSV tempfile and calls `send_email(..., files=[...])` instead of the
    no-attachment path — real code in `notification/email_sender.py`,
    never mocked here."""
    specs, filepath = basic_example_specs
    mutated_specs = copy.deepcopy(specs)
    mutated_specs.report.attach_csv = True

    dag = dag_gen.create_dag(mutated_specs, filepath)

    with patch(
        "hooks.dou_hook.DOUHook.search_text",
        new=_fake_search_text({MATCHED_TERM: [FAKE_MATCH]}),
    ), patch("searchers.time.sleep"), patch(
        "notification.email_sender.send_email"
    ) as mock_send_email:
        dag_run = dag.test()

    assert dag_run.state == DagRunState.SUCCESS
    mock_send_email.assert_called_once()
    _, kwargs = mock_send_email.call_args
    assert "files" in kwargs and len(kwargs["files"]) == 1
    assert kwargs["files"][0].endswith(".csv")


# ---------------------------------------------------------------------------
# 3. Real filter — terms_ignore, with >1 candidate result
#
#    (`department` is intentionally not re-tested at the DAG level here:
#    `searchers_test.py::test_match_department` already covers
#    `_match_department` directly, combining `department` AND
#    `department_ignore` across 3 candidate results — more thoroughly
#    than a DAG-level integration test would.)
# ---------------------------------------------------------------------------


def test_e2e_dag_terms_ignore_filter_drops_matching_result(
    dag_gen: DouDigestDagGenerator, basic_example_specs
):
    """Same idea for `terms_ignore` (`_match_terms_ignore`)."""
    specs, filepath = basic_example_specs
    mutated_specs = copy.deepcopy(specs)
    mutated_specs.search[0].terms_ignore = ["palavra proibida"]

    dag = dag_gen.create_dag(mutated_specs, filepath)

    clean_item = dict(FAKE_MATCH, title="Documento limpo")
    ignored_item = dict(
        FAKE_MATCH,
        title="Documento com Palavra Proibida no meio",
    )

    with patch(
        "hooks.dou_hook.DOUHook.search_text",
        new=_fake_search_text({MATCHED_TERM: [clean_item, ignored_item]}),
    ), patch("searchers.time.sleep"), patch(
        "notification.email_sender.send_email"
    ) as mock_send_email:
        dag_run = dag.test()

    assert dag_run.state == DagRunState.SUCCESS
    _, kwargs = mock_send_email.call_args
    assert "Documento limpo" in kwargs["html_content"]
    assert "Palavra Proibida" not in kwargs["html_content"]


# ---------------------------------------------------------------------------
# 4. Real parsing — mock one level lower, at requests.get, so
#    hooks/dou_hook.py's own HTML/JSON parsing actually runs.
# ---------------------------------------------------------------------------

_DOU_SCRIPT_TAG_ID = "_br_com_seatecnologia_in_buscadou_BuscaDouPortlet_params"


def _dou_api_item(
    *,
    pub_name="DO1",
    title,
    url_title,
    content,
    pub_date="25/08/2026",
    class_pk="1",
    display_date_sortable="2026-08-25",
    hierarchy_list="Ministerio da Gestao",
    hierarchy_str="Ministerio da Gestao",
    art_type="Portaria",
):
    """Builds one item exactly in the shape the real DOU API returns it
    inside the page's `jsonArray`, per `hooks/dou_hook.py::search_text`."""
    return {
        "pubName": pub_name,
        "title": title,
        "urlTitle": url_title,
        "content": content,
        "pubDate": pub_date,
        "classPK": class_pk,
        "displayDateSortable": display_date_sortable,
        "hierarchyList": hierarchy_list,
        "hierarchyStr": hierarchy_str,
        "artType": art_type,
    }


def _dou_html_page(items: list) -> bytes:
    """Wraps `items` in the minimal HTML shell that
    `DOUHook.search_text` expects to find: a single <script> tag with the
    known id, whose text is the JSON payload with a `jsonArray` key, and
    no pagination buttons (so a single page is assumed)."""
    payload = json.dumps({"jsonArray": items})
    html = f"""
    <html><body>
        <script id="{_DOU_SCRIPT_TAG_ID}">{payload}</script>
    </body></html>
    """
    return html.encode("utf-8")


def _fake_requests_get_by_term(term_to_items: dict):
    """`requests.get` replacement used to mock the real DOU HTTP endpoint.
    Inspects the outgoing payload's `q` param to decide which page/items to
    return, so different search terms in the same DAG run get different
    (possibly empty) results — same as the real API would."""

    def _get(url, params=None, headers=None, timeout=10):
        query = (params or {}).get("q", "")
        term = query.strip('"')
        items = term_to_items.get(term, [])

        response = Mock()
        response.content = _dou_html_page(items)
        response.url = url
        response.raise_for_status = lambda: None
        return response

    return _get


def test_e2e_dag_real_http_boundary_parses_dou_page(basic_example_dag):
    """Mocks `requests.get` instead of `DOUHook.search_text`, so the real
    HTML-parsing/section-mapping code in `hooks/dou_hook.py::search_text`
    actually executes. This is the check that catches breakage if the
    DOU site changes its response shape — none of the higher-boundary
    mocks above would ever notice that."""
    real_item = _dou_api_item(
        title="Portaria sobre dados abertos",
        url_title="portaria-dados-abertos-123",
        content="Texto sobre <span class='highlight'>dados abertos</span> no governo.",
    )

    with patch(
        "hooks.dou_hook.requests.get",
        side_effect=_fake_requests_get_by_term({MATCHED_TERM: [real_item]}),
    ), patch("searchers.time.sleep"), patch(
        "notification.email_sender.send_email"
    ) as mock_send_email:
        dag_run = basic_example_dag.test()

    assert dag_run.state == DagRunState.SUCCESS
    mock_send_email.assert_called_once()
    _, kwargs = mock_send_email.call_args
    # Confirms the real hook correctly built the public URL from
    # IN_WEB_BASE_URL + urlTitle, and mapped the "do1" section code
    # (Section.SECAO_1.value, confirmed in utils/search_domains.py) to
    # its human-readable "Seção 1" description — both real parsing paths.
    assert "portaria-dados-abertos-123" in kwargs["html_content"]
    assert "Seção 1" in kwargs["html_content"]
    assert dag_run.get_task_instance("notify_email").state == TaskInstanceState.SUCCESS


# ---------------------------------------------------------------------------
# 5. Full task-graph structure (generic, reusable for other DAGs)
# ---------------------------------------------------------------------------


def test_e2e_dag_has_expected_task_graph(basic_example_dag, basic_example_specs):
    specs, _ = basic_example_specs
    assert_full_task_graph(
        basic_example_dag,
        num_searches=len(specs.search),
        notify_task_ids=["notify_email"],
    )