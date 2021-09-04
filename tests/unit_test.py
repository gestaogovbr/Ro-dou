""" Ro-dou unit tests
"""

import pytest

import pandas as pd

@pytest.mark.parametrize(
    'raw_html, clean_text',
    [
        ('<div><a>Any text</a></div>', 'Any text'),
        ('<div><div><p>Any text</a></div>', 'Any text'),
        ('Any text</a></div>', 'Any text'),
        ('Any text', 'Any text'),
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

def test_convert_report_to_dataframe(dag_gen, report_example):
    df = dag_gen.convert_report_to_dataframe(report_example)
    num_rows = df.shape[0]
    assert num_rows == 15

def test_get_csv_tempfile_returns_valid_file(dag_gen, report_example):
    with dag_gen.get_csv_tempfile(report_example) as csv_file:
        assert pd.read_csv(csv_file.name) is not None
