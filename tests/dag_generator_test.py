"""DouDagGenerator unit tests
"""

import pandas as pd
import pytest
from dags.ro_dou_src.dou_dag_generator import merge_results
from dags.ro_dou_src.notification.email_sender import EmailSender, repack_match
from airflow import Dataset
from airflow.timetables.datasets import DatasetOrTimeSchedule


def test_repack_match(report_example):
    match_dict = report_example[0]["result"]["single_group"]["antonio de oliveira"]["single_department"][0]
    repacked_match = repack_match(
        "Teste Report", "single_group", "antonio de oliveira", "single_department", match_dict
    )
    assert repacked_match == (
        "Teste Report",
        "single_group",
        "antonio de oliveira",
        "single_department",
        "Seção 3",
        match_dict["href"],
        match_dict["title"],
        match_dict["abstract"],
        match_dict["date"],
    )


@pytest.fixture
def email_sender(report_example):
    email_sender = EmailSender(None)
    email_sender.search_report = report_example
    return email_sender


def test_convert_report_dict__returns_list(email_sender):
    tuple_list = email_sender.convert_report_dict_to_tuple_list()
    assert isinstance(tuple_list, list)


def test_convert_report_dict__returns_tuples(email_sender):
    tuple_list = email_sender.convert_report_dict_to_tuple_list()
    for tpl in tuple_list:
        assert isinstance(tpl, tuple)


def test_convert_report_dict__returns_tuples_of_nine(email_sender):
    tuple_list = email_sender.convert_report_dict_to_tuple_list()
    for tpl in tuple_list:
        assert len(tpl) == 9


def test_convert_report_to_dataframe__rows_count(email_sender):
    df = email_sender.convert_report_to_dataframe()
    # num_rows
    assert df.shape[0] == 15


def test_convert_report_to_dataframe__cols_single_group(email_sender):
    df = email_sender.convert_report_to_dataframe()
    assert tuple(df.columns) == (
        "Consulta",
        "Termo de pesquisa",
        "Seção",
        "URL",
        "Título",
        "Resumo",
        "Data",
    )


def test_convert_report_to_dataframe__cols_grouped_report(email_sender, report_example):
    report_example[0]["result"]["group_name_different_of_single_group"] = (
        report_example[0]["result"].pop("single_group")
    )
    email_sender.search_report = report_example
    df = email_sender.convert_report_to_dataframe()
    assert tuple(df.columns) == (
        "Consulta",
        "Grupo",
        "Termo de pesquisa",
        "Seção",
        "URL",
        "Título",
        "Resumo",
        "Data",
    )


def test_get_csv_tempfile__valid_file_name_preffix(email_sender):
    with email_sender.get_csv_tempfile() as csv_file:
        assert csv_file.name.split("/")[-1].startswith("extracao_dou_")


def test_get_csv_tempfile__valid_file_name_suffix(email_sender):
    with email_sender.get_csv_tempfile() as csv_file:
        assert csv_file.name.endswith(".csv")


def test_get_csv_tempfile__valid_csv(email_sender):
    with email_sender.get_csv_tempfile() as csv_file:
        assert pd.read_csv(csv_file.name) is not None


def test_merge_results(merge_results_samples):
    merged_result = merge_results(
        merge_results_samples[0],
        merge_results_samples[1],
    )
    assert merged_result == merge_results_samples[2]


@pytest.mark.parametrize(
    "dag_id, size, hashed",
    [
        ("unique_id_for_each_dag", 60, 56),
        ("generates_sparses_hashed_results", 120, 59),
        ("unique_id_for_each_dag", 10, 6),
        ("", 10, 0),
        ("", 100, 0),
    ],
)
def test_hash_dag_id(dag_gen, dag_id, size, hashed):
    assert dag_gen._hash_dag_id(dag_id, size) == hashed


@pytest.mark.parametrize(
    "dataset, schedule, is_default_schedule",
    [
        ("inlabs", "0 8 * * MON-FRI", True),
        ("inlabs", "0 8 * * MON-FRI", False),
    ],
)
def test_update_schedule_with_dataset(dag_gen, dataset, schedule, is_default_schedule):

    schedule = dag_gen._update_schedule_with_dataset(
        dataset, schedule, is_default_schedule
    )

    if is_default_schedule is True:
        assert isinstance(schedule[0], Dataset)
    else:
        assert isinstance(schedule, DatasetOrTimeSchedule)
