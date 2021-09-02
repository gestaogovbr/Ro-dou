""" Ro-dou unit tests
"""

import os
import sys
import inspect

import pytest

currentdir = os.path.dirname(
    os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

from dou_dag_generator import DouDigestDagGenerator

@pytest.mark.parametrize('raw_html, clean_text',
    [
    ('<div><a>Any text</a></div>', 'Any text'),
    ('<div><div><p>Any text</a></div>', 'Any text'),
    ('Any text</a></div>', 'Any text'),
    ('Any text', 'Any text'),
    ])
def test_clean_html(raw_html, clean_text):
    assert DouDigestDagGenerator().clean_html(raw_html) == clean_text

@pytest.mark.parametrize('raw_html, start_name, match_name',
    [
    ("PRIOR<>MATCHED NAME<>EVENTUALLY END NAME",
     "PRIOR",
     "MATCHED NAME")
    ,
    ("JOSE<span class='highlight' style='background:#FFA;'>ANTONIO DE OLIVEIRA</span>CAMARGO",
     "JOSE",
     "ANTONIO DE OLIVEIRA")
    ,
    ("<span class='highlight' style='background:#FFA;'>ANTONIO DE OLIVEIRA</span>CAMARGO",
     "",
     "ANTONIO DE OLIVEIRA"),
    ])
def test_get_prior_and_matched_name(raw_html, start_name, match_name):
    assert DouDigestDagGenerator()\
        .get_prior_and_matched_name(raw_html) == (start_name, match_name)

@pytest.mark.parametrize('raw_text, normalized_text',
    [
    ('Nitái Bêzêrrá', 'nitai bezerra'),
    ('Nitái-Bêzêrrá', 'nitai bezerra'),
    ('Normaliza çedilha', 'normaliza cedilha'),
    ('ìÌÒòùÙúÚáÁÀeççÇÇ~ A', 'iioouuuuaaaecccc a'),
    ('a  %&* /  aáá  3d_U', 'a aaa 3d u'),
    ])
def test_normalize(raw_text, normalized_text):
    assert DouDigestDagGenerator().normalize(raw_text) == normalized_text

@pytest.mark.parametrize('search_term, abstract',
    [
    ("ANTONIO DE OLIVEIRA",
     "<span class='highlight' style='background:#FFA;'>ANTONIO DE OLIVEIRA</span> FREITAS - Diretor Geral.EXTRATO DE COMPROMISSO PRONAS/PCD: Termo de Compromisso que entre si celebram a União, por intermédio do Ministério da Saúde,...")
    ,
    ("ANTONIO DE OLIVEIRA",
     "JOSÉ <span class='highlight' style='background:#FFA;'>ANTONIO DE OLIVEIRA</span> FREITAS - Diretor Geral.EXTRATO DE COMPROMISSO PRONAS/PCD: Termo de Compromisso que entre si celebram a União, por intermédio do Ministério da Saúde,...")
    ,
    ("MATCHED NAME",
     "PRIOR<>MATCHED NAME<>EVENTUALLY END NAME"),
    ])
def test_is_signature(search_term, abstract):
    assert DouDigestDagGenerator().is_signature(search_term, abstract)
