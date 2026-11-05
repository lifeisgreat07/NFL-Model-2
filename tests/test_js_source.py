"""The one function_source the page tests share (Stage 86 item 7).

Run with: pytest tests/test_js_source.py -v
"""
import pytest

from tests.js_source import function_source

SRC = """// function later() is mentioned here first
function first(a) {
  if (a) {
    return 1;
  }
  return 2;
}
function later(b) {
  return b;
}
"""


def test_it_takes_the_function_through_its_own_closing_brace_only():
    got = function_source(SRC, 'first')
    assert got.startswith('function first(a) {') and got.endswith('  return 2;\n}\n')
    assert 'later' not in got


def test_at_line_start_skips_a_mention_in_a_comment():
    assert function_source(SRC, 'later', at_line_start=True) == 'function later(b) {\n  return b;\n}\n'


def test_a_missing_function_fails_with_its_name():
    with pytest.raises(AssertionError, match='nowhere is not findable'):
        function_source(SRC, 'nowhere')


def test_a_name_is_matched_as_text_not_as_a_pattern():
    with pytest.raises(AssertionError):
        function_source(SRC, 'f.rst')
