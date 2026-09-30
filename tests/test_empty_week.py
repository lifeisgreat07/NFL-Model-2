"""A week with no picks is never saved (Stage 24 item 4).

A saved week can never be overwritten and determine_next_week counts any
saved file as done, so an empty `[]` for a week -- every game skipped for a
missing team rating, say -- would stand as its picks and the season would
move past it. The run now fails instead, saving nothing.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

import weekly_update as wu  # noqa: E402


def test_an_empty_week_fails_the_run():
    with pytest.raises(SystemExit, match='no picks, so nothing is saved'):
        wu.refuse_an_empty_week([], 2026, 4)


def test_a_week_with_picks_goes_through():
    assert wu.refuse_an_empty_week([{'home': 'GB'}], 2026, 4) is None


def test_main_checks_before_it_writes_and_only_when_it_writes():
    """The check sits in the branch that saves, ahead of the write: before
    the existing-file branch, a manual re-run of a saved week would fail
    instead of warning; after the write, it would guard nothing."""
    src = (ROOT / 'src' / 'weekly_update.py').read_text(encoding='utf-8')
    main = src[src.index('def main(season'):]
    save = main[main.index("    if out_path.exists():"):]
    other, saving = save.split('\n    else:\n', 1)
    assert 'refuse_an_empty_week' not in other
    call = saving.index('refuse_an_empty_week(predictions, season, week)')
    assert call < saving.index('write_json_atomic(out_path'), (
        'the empty-week check runs after the file is written')
