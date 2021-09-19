"""DouDagGenerator unit tests
"""

import pytest

import pandas as pd

def test_repack_match(dag_gen, report_example):
    match_dict = report_example['single_group']['antonio de oliveira'][0]
    repacked_match = dag_gen.repack_match('single_group',
                                          'antonio de oliveira',
                                          match_dict)
    assert repacked_match == ('single_group',
                              'antonio de oliveira',
                              'Seção 3',
                              match_dict['href'],
                              match_dict['title'],
                              match_dict['abstract'],
                              match_dict['date'])

def test_convert_report_dict__returns_list(dag_gen, report_example):
    tuple_list = dag_gen.convert_report_dict_to_tuple_list(report_example)
    assert isinstance(tuple_list, list)

def test_convert_report_dict__returns_tuples(dag_gen, report_example):
    tuple_list = dag_gen.convert_report_dict_to_tuple_list(report_example)
    for tpl in tuple_list:
        assert isinstance(tpl, tuple)

def test_convert_report_dict__returns_tuples_of_seven(dag_gen, report_example):
    tuple_list = dag_gen.convert_report_dict_to_tuple_list(report_example)
    for tpl in tuple_list:
        assert len(tpl) == 7

def test_convert_report_to_dataframe__rows_count(dag_gen, report_example):
    df = dag_gen.convert_report_to_dataframe(report_example)
    # num_rows
    assert df.shape[0] == 15

def test_convert_report_to_dataframe__cols_single_group(
        dag_gen, report_example):
    df = dag_gen.convert_report_to_dataframe(report_example)
    assert tuple(df.columns) == ('Termo de pesquisa', 'Seção', 'URL',
                                 'Título', 'Resumo', 'Data')

def test_convert_report_to_dataframe__cols_grouped_report(
        dag_gen, report_example):
    report_example['group_name_different_of_single_group'] = \
        report_example.pop('single_group')
    df = dag_gen.convert_report_to_dataframe(report_example)
    assert tuple(df.columns) == ('Grupo', 'Termo de pesquisa', 'Seção', 'URL',
                                 'Título', 'Resumo', 'Data')

def test_get_csv_tempfile__valid_file_name_preffix(dag_gen, report_example):
    with dag_gen.get_csv_tempfile(report_example) as csv_file:
        assert csv_file.name.split('/')[-1].startswith('extracao_dou_')

def test_get_csv_tempfile__valid_file_name_suffix(dag_gen, report_example):
    with dag_gen.get_csv_tempfile(report_example) as csv_file:
        assert csv_file.name.endswith('.csv')

def test_get_csv_tempfile__valid_csv(dag_gen, report_example):
    with dag_gen.get_csv_tempfile(report_example) as csv_file:
        assert pd.read_csv(csv_file.name) is not None
