""" Ro-dou unit tests
"""
import os
import sys
import inspect

import pytest

import pandas as pd

currentdir = os.path.dirname(
    os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from dou_dag_generator import hash_dag_id, get_safe_schedule

@pytest.mark.parametrize(
    'dag_id, size, hashed',
    [
        ('unique_id_for_each_dag', 60, 56),
        ('generates_sparses_hashed_results', 120, 59),
        ('unique_id_for_each_dag', 10, 6),
        ('', 10, 0),
        ('', 100, 0),
    ])
def test_hash_dag_id(dag_id, size, hashed):
    assert hash_dag_id(dag_id, size) == hashed

@pytest.mark.parametrize(
    'raw_html, clean_text',
    [
        ('<div><a>Any text</a></div>', 'Any text'),
        ('<div><div><p>Any text</a></div>', 'Any text'),
        ('Any text</a></div>', 'Any text'),
        ('Any text', 'Any text'),
        ('<a></a>', ''),
        ('<></>', ''),
        ('', ''),
    ])
def test_clean_html(dag_gen, raw_html, clean_text):
    assert dag_gen.clean_html(raw_html) == clean_text

@pytest.mark.parametrize(
    'raw_html, start_name, match_name',
    [
        ("PRIOR<>MATCHED NAME<>EVENTUALLY END NAME",
         "PRIOR",
         "MATCHED NAME")
        ,
        ("JOSE<span class='highlight' style='background:#FFA;'>"
            "ANTONIO DE OLIVEIRA</span>CAMARGO",
         "JOSE",
         "ANTONIO DE OLIVEIRA")
        ,
        ("<span class='highlight' style='background:#FFA;'>"
            "ANTONIO DE OLIVEIRA</span>CAMARGO",
         "",
         "ANTONIO DE OLIVEIRA")
        ,
    ])
def test_get_prior_and_matched_name(dag_gen, raw_html, start_name, match_name):
    assert dag_gen.get_prior_and_matched_name(raw_html) == (start_name, match_name)

@pytest.mark.parametrize(
    'raw_text, normalized_text',
    [
        ('Nitái Bêzêrrá', 'nitai bezerra'),
        ('Nitái-Bêzêrrá', 'nitai bezerra'),
        ('Normaliza çedilha', 'normaliza cedilha'),
        ('ìÌÒòùÙúÚáÁÀeççÇÇ~ A', 'iioouuuuaaaecccc a'),
        ('a  %&* /  aáá  3d_U', 'a aaa 3d u'),
    ])
def test_normalize(dag_gen, raw_text, normalized_text):
    assert dag_gen.normalize(raw_text) == normalized_text

@pytest.mark.parametrize(
    'search_term, abstract',
    [
        ("ANTONIO DE OLIVEIRA",
         "<span class='highlight' style='background:#FFA;'>ANTONIO DE OLIVEIRA"
         "</span> FREITAS - Diretor Geral.EXTRATO DE COMPROMISSO PRONAS/PCD: "
         "Termo de Compromisso que entre si celebram a União, por intermédio "
         "do Ministério da Saúde,...")
        ,
        ("ANTONIO DE OLIVEIRA",
         "JOSÉ <span class='highlight' style='background:#FFA;'>ANTONIO DE "
         "OLIVEIRA</span> FREITAS - Diretor Geral.EXTRATO DE COMPROMISSO "
         "PRONAS/PCD: Termo de Compromisso que entre si celebram a União, "
         "por intermédio do Ministério da Saúde,...")
        ,
        ("MATCHED NAME",
         "PRIOR<>MATCHED NAME<>EVENTUALLY END NAME")
        ,
    ])
def test_is_signature(dag_gen, search_term, abstract):
    assert dag_gen.is_signature(search_term, abstract)

@pytest.mark.parametrize(
    'search_term, abstract',
    [
        ("ANTONIO DE OLIVEIRA",
         "<span class='highlight' style='background:#FFA;'>ANTONIO DE "
         "OLIVEIRA</span> FREITAS - Diretor Geral.EXTRATO DE COMPROMISSO "
         "PRONAS/PCD: Termo de Compromisso que entre si celebram a União, "
         "por intermédio do Ministério da Saúde,...")
        ,
        ("MATCHED NAME",
         "PRIOR<>MATCHED NAME<>EVENTUALLY END NAME")
        ,
        ("MATCHED NAME",
         "PRIOR MATCHED<> NAME<>EVENTUALLY END NAME")
        ,
        ("MATCHED NAME",
         "PRIOR MATCHED<>   NAME   <>EVENTUALLY END NAME")
        ,
        ("MATCHED NAME",
         "PRIOR MATCHED<> ... NAME<>EVENTUALLY END NAME")
        ,
        ("ANTONIO DE OLIVEIRA",
         "Secretário-Executivo Adjunto do Ministério da Saúde; <span>ANTONIO"
         "</span> ... DE <span>OLIVEIRA</span> FREITAS JUNIOR - Diretor "
         "Geral.EXTRATO DE COMPROMISSO PRONAS/PCD: Termo de ,...")
        ,
    ])
def test_really_matched(dag_gen, search_term, abstract):
    assert dag_gen.really_matched(search_term, abstract)

@pytest.mark.parametrize(
    'pre_term_list, casted_term_list',
    [
        ('''{
            "servidor":{
                "0":"ANTONIO",
                "1":"JOSE",
                "2":"SILVA"
                },
            "carreira":{
                "0":"EPPGG",
                "1":"ATI",
                "2":"OIA"
                }
            }
         ''',
         ['ANTONIO', 'JOSE', 'SILVA']),
        ('''{
            "tanto_faz":{
                "0":"NITAI",
                "1":"BEZERRA DA",
                "2":"SILVA"
                },
            "o_nome_das_colunas":{
                "0":"ESSE",
                "1":"VALOR",
                "2":"E IGNORADO"
                }
            }
         ''',
         ['NITAI', 'BEZERRA DA', 'SILVA']),
    ]
)
def test_cast_term_list__str_param(dag_gen, pre_term_list, casted_term_list):
    assert tuple(dag_gen.cast_term_list(pre_term_list)) == tuple(casted_term_list)

def test_cast_term_list__list_param(dag_gen):
    pre_term_list = ['a', 'b', 'c']
    assert tuple(dag_gen.cast_term_list(pre_term_list)) == tuple(pre_term_list)

def assert_grouped_result(grouped_result):
    assert 'ATI' in grouped_result
    assert 'SILVA' in grouped_result['ATI']
    assert len(grouped_result['ATI']['SILVA']) == 4
    assert 'EPPGG' in grouped_result
    assert 'ANTONIO DE OLIVEIRA' in grouped_result['EPPGG']
    assert len(grouped_result['EPPGG']['ANTONIO DE OLIVEIRA']) == 3


def test_group_by_term_group(dag_gen, search_results, term_n_group):
    grouped_result = dag_gen.group_by_term_group(search_results, term_n_group)
    assert_grouped_result(grouped_result)

def test_group_results__sql_term_list_with_group(dag_gen,
                                             search_results,
                                             term_n_group):
    grouped_result = dag_gen.group_results(search_results, term_n_group)
    assert_grouped_result(grouped_result)

def test_group_results__sql_term_list_without_group(dag_gen,
                                                    search_results):
    terms_str = """{
        "nomes":{
            "0":"ANTONIO DE OLIVEIRA",
            "1":"SILVA"}
        }"""
    grouped_result = dag_gen.group_results(search_results, terms_str)

    assert 'ANTONIO DE OLIVEIRA' in grouped_result['single_group']
    assert 'SILVA' in grouped_result['single_group']

def test_group_results__list_term_list(dag_gen,
                                       search_results):
    any_list_object = []
    grouped_result = dag_gen.group_results(search_results, any_list_object)

    assert 'ANTONIO DE OLIVEIRA' in grouped_result['single_group']
    assert 'SILVA' in grouped_result['single_group']

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
