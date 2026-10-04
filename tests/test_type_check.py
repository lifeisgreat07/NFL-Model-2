"""The type check run-tests.yml gates on, run from the suite (Stage 35).

run-tests.yml runs `python -m mypy --ignore-missing-imports
src/pipeline/weekly_update.py src/pipeline/ratings_engine.py` as its own step. This runs the
same command (tasks.TYPES) so a change that breaks it -- dropping one of
build_team_ratings' @overloads, a bare `return` under `-> Plan | None`
creeping back -- fails a test the mutation corpus can name, not only a CI
step it cannot reach. Skipped where mypy is not installed, except under CI
(the `CI` variable every GitHub runner sets): requirements-dev.txt installs
it there, so a missing mypy in CI is a broken install and fails. A skip is
how a guard goes quiet unnoticed (conftest.py records the earlier bite);
the fourth audit, Q4, Stage 36 item 3.

Run with: pytest tests/test_type_check.py -v
"""
import importlib.util
import os
import subprocess
from pathlib import Path

import pytest

import tasks

ROOT = Path(__file__).resolve().parents[1]


def mypy_or_skip():
    """Skip without mypy locally; fail without it in CI."""
    if importlib.util.find_spec('mypy') is None:
        if os.environ.get('CI'):
            pytest.fail('mypy is not installed in CI, where requirements-dev.txt installs it')
        pytest.skip('mypy not installed (pip install -r requirements-dev.txt)')


def test_the_weekly_modules_type_check(tmp_path):
    mypy_or_skip()
    cmd = [*tasks.TYPES, '--cache-dir', str(tmp_path / 'mypy-cache')]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-500:]


def _no_mypy(monkeypatch):
    real = importlib.util.find_spec
    monkeypatch.setattr(importlib.util, 'find_spec', lambda name, *a: None if name == 'mypy' else real(name, *a))


def test_a_missing_mypy_fails_under_ci(monkeypatch):
    _no_mypy(monkeypatch)
    monkeypatch.setenv('CI', 'true')
    # Caught by hand, not with pytest.raises: if the CI branch were gone,
    # the helper would raise Skipped, which pytest.raises lets through and
    # pytest reports as a skip -- this test going quiet the same way.
    try:
        mypy_or_skip()
    except pytest.fail.Exception as e:
        assert 'not installed in CI' in str(e)
        return
    except BaseException as e:
        raise AssertionError(f'a missing mypy under CI raised {type(e).__name__}, not a failure') from None
    raise AssertionError('a missing mypy under CI raised nothing')


def test_a_missing_mypy_skips_on_a_machine_without_the_dev_install(monkeypatch):
    _no_mypy(monkeypatch)
    monkeypatch.delenv('CI', raising=False)
    with pytest.raises(pytest.skip.Exception):
        mypy_or_skip()
