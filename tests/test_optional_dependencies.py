"""
Stage 86 item 6: the optional-dependency helper skips locally and fails in CI,
and no test skips on a missing tool by its own private rule.

Run with: pytest tests/test_optional_dependencies.py -v
"""
import re
from pathlib import Path

import pytest

from tests import optional

TESTS = Path(__file__).resolve().parent


def test_a_missing_tool_skips_on_a_local_machine(monkeypatch):
    monkeypatch.delenv('CI', raising=False)
    with pytest.raises(pytest.skip.Exception):
        optional.require('no_such_module_xyz')


def test_a_missing_tool_fails_in_ci(monkeypatch):
    monkeypatch.setenv('CI', 'true')
    # BaseException, then the exact type: a skip is not a failure, and pytest
    # would report a skip raised here as this test skipping, not failing.
    with pytest.raises(BaseException) as raised:
        optional.require('no_such_module_xyz')
    assert raised.type is pytest.fail.Exception


def test_a_present_tool_is_imported():
    assert optional.require('json').dumps([]) == '[]'


def test_no_test_skips_on_a_missing_module_by_its_own_rule():
    """importorskip and a find_spec skipif both skip in CI too."""
    rule = re.compile(r"importorskip\(|skipif\(importlib\.util\.find_spec")
    offenders = [p.name for p in TESTS.glob('test_*.py') if rule.search(p.read_text(encoding='utf-8'))
                 and p.name != 'test_optional_dependencies.py']
    assert not offenders, f'use tests.optional.require instead: {offenders}'
