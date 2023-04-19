
import inspect
import os
import sys

currentdir = os.path.dirname(
    os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from notification.isender import _fix_missing_spaces


def test_fix_missing_spaces():
    test_cases = [
        ("This is a <%%>placeholder<%%> example",
         "This is a <%%>placeholder <%%> example"),
        ("<%%>This is a placeholder<%%>", " <%%>This is a placeholder <%%>"),
        ("No placeholders here!", "No placeholders here!"),
        ("<%%>Only start<%%> and end</%%>",
         " <%%>Only start <%%> and end</%%> "),
        ("<%%>No end tag", " <%%>No end tag"),
        ("No start tag</%%>", "No start tag</%%> "),
        (" <%%>Nothing to add</%%> ", " <%%>Nothing to add</%%> "),
        (" <%%> Nothing to add </%%> ", " <%%> Nothing to add </%%> "),
    ]
    for string, expected_result in test_cases:
        assert _fix_missing_spaces(string) == expected_result
