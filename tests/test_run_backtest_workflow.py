"""Every script the "Run backtest" workflow offers is a module that exists
(Stage 36 item 4, from the 2026-10-04 fourth audit).

run-backtest.yml runs only by hand, from a fixed choice list, so a script
renamed or moved between packages breaks it silently: nothing runs the
workflow until someone needs it, and then it fails with ModuleNotFoundError.
Stage 32's packaging was exactly that kind of move. These tests read the
choice list and the `case` that picks each script's package, and import the
module each option resolves to.

Run with: pytest tests/test_run_backtest_workflow.py -v
"""
import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github' / 'workflows' / 'run-backtest.yml'


def _text():
    return WORKFLOW.read_text(encoding='utf-8')


def options():
    block = re.search(r'(?m)^\s+options:\n((?:\s+- \S+\n)+)', _text())
    assert block, 'run-backtest.yml has no choice list for the script input'
    return re.findall(r'-\s+(\S+)', block.group(1))


def packages():
    """{option: package} from the run step's case, plus '*' for the default."""
    case = re.search(r'case "\$\{\{ inputs\.script \}\}" in\n(.*?)\n\s*esac', _text(), re.S)
    assert case, 'the run step no longer picks a package with a case statement'
    arms = dict(re.findall(r'(\S+)\)\s*package=(\w+)\s*;;', case.group(1)))
    assert '*' in arms, 'the case has no default package'
    return arms


def test_the_run_step_runs_the_module_the_case_picks():
    assert 'python -m "src.$package.${{ inputs.script }}"' in _text()


def test_the_choice_list_is_not_empty():
    assert len(options()) >= 4, options()


@pytest.mark.parametrize('script', options())
def test_each_option_resolves_to_a_real_module(script):
    arms = packages()
    module = f"src.{arms.get(script, arms['*'])}.{script}"
    assert importlib.util.find_spec(module) is not None, (
        f'run-backtest.yml offers {script!r}, which runs {module}, and no such module exists')
