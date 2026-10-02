"""The type check run-tests.yml gates on, run from the suite (Stage 35).

run-tests.yml runs `python -m mypy --ignore-missing-imports
src/pipeline/weekly_update.py src/pipeline/ratings_engine.py` as its own step. This runs the
same command (tasks.TYPES) so a change that breaks it -- dropping one of
build_team_ratings' @overloads, a bare `return` under `-> Plan | None`
creeping back -- fails a test the mutation corpus can name, not only a CI
step it cannot reach. Skipped where mypy is not installed; CI installs it
from requirements-dev.txt.

Run with: pytest tests/test_type_check.py -v
"""
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import tasks  # noqa: E402


def test_the_weekly_modules_type_check(tmp_path):
    if importlib.util.find_spec('mypy') is None:
        pytest.skip('mypy not installed (pip install -r requirements-dev.txt)')
    cmd = [*tasks.TYPES, '--cache-dir', str(tmp_path / 'mypy-cache')]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-500:]
