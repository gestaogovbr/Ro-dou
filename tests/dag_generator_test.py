"""DouDagGenerator unit tests
"""

import pandas as pd
import pytest
from dags.ro_dou_src.dou_dag_generator import merge_results
from dags.ro_dou_src.notification.email_sender import EmailSender, repack_match


def test_repack_match(report_example):
    match_dict = report_example['single_group']['antonio de oliveira'][0]
    repacked_match = repack_match('single_group',
                                          'antonio de oliveira',
                                          match_dict)
    assert repacked_match == ('single_group',
                              'antonio de oliveira',
                              'Seção 3',
                              match_dict['href'],
                              match_dict['title'],
                              match_dict['abstract'],
                              match_dict['date'])


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

def test_convert_report_dict__returns_tuples_of_seven(email_sender):
    tuple_list = email_sender.convert_report_dict_to_tuple_list()
    for tpl in tuple_list:
        assert len(tpl) == 7

def test_convert_report_to_dataframe__rows_count(email_sender):
    df = email_sender.convert_report_to_dataframe()
    # num_rows
    assert df.shape[0] == 15

def test_convert_report_to_dataframe__cols_single_group(email_sender):
    df = email_sender.convert_report_to_dataframe()
    assert tuple(df.columns) == ('Termo de pesquisa', 'Seção', 'URL',
                                 'Título', 'Resumo', 'Data')

def test_convert_report_to_dataframe__cols_grouped_report(email_sender, report_example):
    report_example['group_name_different_of_single_group'] = \
        report_example.pop('single_group')
    email_sender.search_report = report_example
    df = email_sender.convert_report_to_dataframe()
    assert tuple(df.columns) == ('Grupo', 'Termo de pesquisa', 'Seção', 'URL',
                                 'Título', 'Resumo', 'Data')

def test_get_csv_tempfile__valid_file_name_preffix(email_sender):
    with email_sender.get_csv_tempfile() as csv_file:
        assert csv_file.name.split('/')[-1].startswith('extracao_dou_')

def test_get_csv_tempfile__valid_file_name_suffix(email_sender):
    with email_sender.get_csv_tempfile() as csv_file:
        assert csv_file.name.endswith('.csv')

def test_get_csv_tempfile__valid_csv(email_sender):
    with email_sender.get_csv_tempfile() as csv_file:
        assert pd.read_csv(csv_file.name) is not None

def test_merge_results(merge_results_samples):
    merged_result = merge_results(
        merge_results_samples[0],
        merge_results_samples[1],
    )
    assert merged_result == merge_results_samples[2]
