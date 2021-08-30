""" Ro-dou tests
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

# Unit tests
@pytest.mark.parametrize('input, output',
                          [
                            ('<div><a>Any text</a></div>', 'Any text'),
                            ('<div><div><p>Any text</a></div>', 'Any text'),
                            ('Any text</a></div>', 'Any text'),
                            ('Any text', 'Any text'),
                            ])
def test_clean_html(input, output):
    assert DouDigestDagGenerator().clean_html(input) == output

@pytest.mark.parametrize('input, output',
                          [
                            ('Nitái Bêzêrrá', 'nitai bezerra'),
                            ('Nitái-Bêzêrrá', 'nitai bezerra'),
                            ('Normaliza çedilha', 'normaliza cedilha'),
                            ('ìÌÒòùÙúÚáÁÀeççÇÇ~ A', 'iioouuuuaaaecccc a'),
                            ('a  \|%&* /  aáá  3d_U', 'a aaa 3d u'),
                            ])
def test_normalize(input, output):
    assert DouDigestDagGenerator().normalize(input) == output
