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
    dou_gen = DouDigestDagGenerator()
    cleaned_html = dou_gen.clean_html(input)

    assert cleaned_html == output