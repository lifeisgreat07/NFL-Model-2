"""A week locked with no starter listed says so, and only then (Stage 25,
after #184).

#184 warned from the data-quality step whenever the earliest unplayed week
listed no starting quarterback. That step runs on every weekly run, so a
Tuesday run merely holding next week, before nflverse had listed its
starters, would have warned about a week it was not picking. The check
now lives on the path that saves picks.
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

import weekly_update as wu  # noqa: E402


def week(listed=False):
    rows = [{'home_team': h, 'away_team': a,
             'home_qb_id': '00-0000001' if listed and i == 0 else None,
             'away_qb_id': None}
            for i, (h, a) in enumerate([('GB', 'TB'), ('KC', 'LV')])]
    return pd.DataFrame(rows)


def test_a_locked_week_with_no_starter_and_no_override_warns():
    line = wu.starter_warning(week(), {}, 2026, 5)
    assert line and line.startswith('WARNING: 2026 week 5 is being locked')


def test_one_listed_starter_is_enough():
    assert wu.starter_warning(week(listed=True), {}, 2026, 5) is None


def test_an_override_is_enough():
    assert wu.starter_warning(week(), {'TB': {'player_name': 'X'}}, 2026, 5) is None


def test_empty_strings_are_not_a_listed_starter():
    w = week()
    w['home_qb_id'] = ''
    assert wu.starter_warning(w, {}, 2026, 5) is not None


def test_it_runs_only_on_the_path_that_locks():
    """After the hold returns and before the picks are built: a Tuesday
    run that holds the week never reaches it."""
    src = (ROOT / 'src' / 'weekly_update.py').read_text(encoding='utf-8')
    main = src[src.index('def main(season, week):'):]
    hold = main.index('Nothing saved.")\n        return')
    call = main.index('no_starters = starter_warning(week_games, qb_overrides, season, week)')
    build = main.index('    predictions = []')
    assert hold < call < build
    assert 'print(no_starters)' in main[call:build]
