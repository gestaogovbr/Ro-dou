"""Serachers unit tests
"""

import pytest

import pandas as pd


@pytest.mark.parametrize(
    "raw_html, clean_text",
    [
        ("<div><a>Any text</a></div>", "Any text"),
        ("<div><div><p>Any text</a></div>", "Any text"),
        ("Any text</a></div>", "Any text"),
        ("Any text", "Any text"),
        ("<a></a>", ""),
        ("<></>", ""),
        ("", ""),
    ],
)
def test_clean_html(dou_searcher, raw_html, clean_text):
    assert dou_searcher._clean_html(raw_html) == clean_text


@pytest.mark.parametrize(
    "raw_html, start_name, match_name",
    [
        ("PRIOR<>MATCHED NAME<>EVENTUALLY END NAME", "PRIOR", "MATCHED NAME"),
        (
            "JOSE<span class='highlight' style='background:#FFA;'>"
            "ANTONIO DE OLIVEIRA</span>CAMARGO",
            "JOSE",
            "ANTONIO DE OLIVEIRA",
        ),
        (
            "<span class='highlight' style='background:#FFA;'>"
            "ANTONIO DE OLIVEIRA</span>CAMARGO",
            "",
            "ANTONIO DE OLIVEIRA",
        ),
    ],
)
def test_get_prior_and_matched_name(dou_searcher, raw_html, start_name, match_name):
    assert dou_searcher._get_prior_and_matched_name(raw_html) == (
        start_name,
        match_name,
    )


@pytest.mark.parametrize(
    "raw_text, normalized_text",
    [
        ("Nitái Bêzêrrá", "nitai bezerra"),
        ("Nitái-Bêzêrrá", "nitai-bezerra"),
        ("Normaliza çedilha", "normaliza cedilha"),
        ("ìÌÒòùÙúÚáÁÀeççÇÇ~ A", "iioouuuuaaaecccc~ a"),
        ("a  %&* /  aáá  3d_U", "a %&* / aaa 3d_u"),
    ],
)
def test_normalize(dou_searcher, raw_text, normalized_text):
    assert dou_searcher._normalize(raw_text) == normalized_text


@pytest.mark.parametrize(
    "search_term, abstract",
    [
        (
            "ANTONIO DE OLIVEIRA",
            "<span class='highlight' style='background:#FFA;'>ANTONIO DE OLIVEIRA"
            "</span> FREITAS - Diretor Geral.EXTRATO DE COMPROMISSO PRONAS/PCD: "
            "Termo de Compromisso que entre si celebram a União, por intermédio "
            "do Ministério da Saúde,...",
        ),
        (
            "ANTONIO DE OLIVEIRA",
            "JOSÉ <span class='highlight' style='background:#FFA;'>ANTONIO DE "
            "OLIVEIRA</span> FREITAS - Diretor Geral.EXTRATO DE COMPROMISSO "
            "PRONAS/PCD: Termo de Compromisso que entre si celebram a União, "
            "por intermédio do Ministério da Saúde,...",
        ),
        ("MATCHED NAME", "PRIOR<>MATCHED NAME<>EVENTUALLY END NAME"),
    ],
)
def test_is_signature(dou_searcher, search_term, abstract):
    assert dou_searcher._is_signature(search_term, abstract)


@pytest.mark.parametrize(
    "search_term, abstract",
    [
        (
            "ANTONIO DE OLIVEIRA",
            "<span class='highlight' style='background:#FFA;'>ANTONIO DE "
            "OLIVEIRA</span> FREITAS - Diretor Geral.EXTRATO DE COMPROMISSO "
            "PRONAS/PCD: Termo de Compromisso que entre si celebram a União, "
            "por intermédio do Ministério da Saúde,...",
        ),
        ("MATCHED NAME", "PRIOR<>MATCHED NAME<>EVENTUALLY END NAME"),
        ("MATCHED NAME", "PRIOR MATCHED<> NAME<>EVENTUALLY END NAME"),
        ("MATCHED NAME", "PRIOR MATCHED<>   NAME   <>EVENTUALLY END NAME"),
        ("MATCHED NAME", "PRIOR MATCHED<> ... NAME<>EVENTUALLY END NAME"),
        (
            "ANTONIO DE OLIVEIRA",
            "Secretário-Executivo Adjunto do Ministério da Saúde; <span>ANTONIO"
            "</span> ... DE <span>OLIVEIRA</span> FREITAS JUNIOR - Diretor "
            "Geral.EXTRATO DE COMPROMISSO PRONAS/PCD: Termo de ,...",
        ),
    ],
)
def test_really_matched(dou_searcher, search_term, abstract):
    assert dou_searcher._really_matched(search_term, abstract)


def test_match_department(dou_searcher):
    department = ["Ministério da Defesa"]
    results = [
        {
            "section": "Seção 3",
            "title": "EXTRATO DE COMPROMISSO",
            "href": "https://www.in.gov.br/web/dou/-/extrato-de-compromisso-342504508",
            "abstract": "ALESSANDRO GLAUCO DOS ANJOS DE VASCONCELOS - Secretário-Executivo Adjunto...",
            "date": "02/09/2021",
            "hierarchyList": [
                "Ministério da Defesa",
                "Comando do Exército",
                "Comando Militar do Nordeste",
                "6ª Região Militar",
                "28º Batalhão de Caçadores",
            ],
        },
        {
            "section": "Seção 3",
            "title": "EXTRATO DE COMPROMISSO",
            "href": "https://www.in.gov.br/web/dou/-/extrato-de-compromisso-342504508",
            "abstract": "ALESSANDRO GLAUCO DOS ANJOS DE VASCONCELOS - Secretário-Executivo Adjunto...",
            "date": "02/09/2021",
            "hierarchyList": ["Ministério dos Povos Indígenas"],
        },
    ]
    dou_searcher._match_department(results, department)
    assert len(results) == 1

def test_match_pubtype(dou_searcher):
    pubtype = ["Edital"]
    results = [
        {
            "section": "Seção 3",
            "title": "EXTRATO DE COMPROMISSO",
            "href": "https://www.in.gov.br/web/dou/-/extrato-de-compromisso-342504508",
            "abstract": "ALESSANDRO GLAUCO DOS ANJOS DE VASCONCELOS - Secretário-Executivo Adjunto...",
            "date": "02/09/2021",
            "arttype": [
                "Edital",
                "Ata",
                "Portaria",
            ],
        },
        {
            "section": "Seção 3",
            "title": "EXTRATO DE COMPROMISSO",
            "href": "https://www.in.gov.br/web/dou/-/extrato-de-compromisso-342504508",
            "abstract": "ALESSANDRO GLAUCO DOS ANJOS DE VASCONCELOS - Secretário-Executivo Adjunto...",
            "date": "02/09/2021",
            "arttype": ["Portaria"],
        },
    ]
    dou_searcher._match_pubtype(results, pubtype)
    assert len(results) == 1



@pytest.mark.parametrize(
    "pre_term_list, casted_term_list",
    [
        (
            """{
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
         """,
            ["ANTONIO", "JOSE", "SILVA"],
        ),
        (
            """{
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
         """,
            ["NITAI", "BEZERRA DA", "SILVA"],
        ),
    ],
)
def test_cast_term_list__str_param(dou_searcher, pre_term_list, casted_term_list):
    assert tuple(dou_searcher._cast_term_list(pre_term_list)) == tuple(casted_term_list)


def test_cast_term_list__list_param(dou_searcher):
    pre_term_list = ["a", "b", "c"]
    assert tuple(dou_searcher._cast_term_list(pre_term_list)) == tuple(pre_term_list)

def assert_grouped_term_result(grouped_result):
    assert "ATI" in grouped_result
    assert "SILVA" in grouped_result["ATI"]
    assert len(grouped_result["ATI"]["SILVA"]) == 4
    assert "EPPGG" in grouped_result
    assert "ANTONIO DE OLIVEIRA" in grouped_result["EPPGG"]
    assert len(grouped_result["EPPGG"]["ANTONIO DE OLIVEIRA"]) == 3

def assert_grouped_term_dept_result(grouped_result):
    assert "ATI" in grouped_result
    assert "SILVA" in grouped_result["ATI"]
    assert len(grouped_result["ATI"]["SILVA"]["single_department"]) == 4
    assert "EPPGG" in grouped_result
    assert "ANTONIO DE OLIVEIRA" in grouped_result["EPPGG"]
    assert len(grouped_result["EPPGG"]["ANTONIO DE OLIVEIRA"]["single_department"]) == 3


# TODO incluir teste com search_results vazio
def test_group_by_term_group(dou_searcher, search_results, term_n_group):
    grouped_result = dou_searcher._group_by_term_group(search_results, term_n_group)
    assert_grouped_term_result(grouped_result)

def test_group_by_department(dou_searcher, search_results):
    grouped_result = dou_searcher._group_by_department(search_results, None)
    assert "single_department" in grouped_result["ANTONIO DE OLIVEIRA"]
    assert "single_department" in grouped_result["SILVA"]
    assert len(grouped_result["SILVA"]["single_department"]) == 4

def test_group_results__sql_term_list_with_group(
    dou_searcher, search_results, term_n_group
):
    grouped_result = dou_searcher._group_results(search_results, term_n_group)
    assert_grouped_term_dept_result(grouped_result)


def test_group_results__sql_term_list_without_group(dou_searcher, search_results):
    terms_str = """{
        "nomes":{
            "0":"ANTONIO DE OLIVEIRA",
            "1":"SILVA"}
        }"""
    grouped_result = dou_searcher._group_results(search_results, terms_str)

    assert "ANTONIO DE OLIVEIRA" in grouped_result["single_group"]
    assert "SILVA" in grouped_result["single_group"]


def test_group_results__list_term_list(dou_searcher, search_results):
    any_list_object = []
    grouped_result = dou_searcher._group_results(search_results, any_list_object)

    assert "ANTONIO DE OLIVEIRA" in grouped_result["single_group"]
    assert "SILVA" in grouped_result["single_group"]


def test_add_standard_highlight_formatting(dou_searcher):
    results = [
        {
            "section": "DOU - Seção 1",
            "title": "PORTARIA GM/MMA Nº 404, DE 14 DE MARÇO DE 2023",
            "href": "https://www.in.gov.br/web/dou/-/"
            "portaria-gm/mma-n-404-de-14-de-marco-de-2023-470057067",
            "abstract": "As manifestações registradas na Plataforma Fala.BR versando "
            "sobre a <span class='highlight' style='background:#FFA;'>"
            "Lei</span> de <span class='highlight' style='background:"
            "#FFA;'>Acesso à Informação</span> têm ritoPORTARIA GM/MMA "
            "Nº 404, DE 14 DE MARÇO DE 2023 Estabelece, no âmbito do "
            "Ministério do Meio Ambiente e Mudança do Clima, os "
            "procedimentos para o recebimento e o "
            "tratamento de manifestações...",
            "date": "15/03/2023",
        }
    ]
    dou_searcher._add_standard_highlight_formatting(results)
    assert results[0]["abstract"] == (
        "As manifestações registradas na Plataforma Fala.BR versando sobre "
        "a <%%>Lei</%%> de <%%>Acesso à Informação</%%> têm ritoPORTARIA "
        "GM/MMA Nº 404, DE 14 DE MARÇO DE 2023 Estabelece, no âmbito do "
        "Ministério do Meio Ambiente e Mudança do Clima, os procedimentos "
        "para o recebimento e o tratamento de manifestações..."
    )
