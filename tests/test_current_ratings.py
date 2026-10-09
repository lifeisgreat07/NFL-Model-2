"""The live run's ratings are never None (Stage 35).

build_team_ratings(..., upto_cutoff_i=N) returns None below
MIN_PLAYS_FOR_RATING plays. weekly_update.current_ratings stops the run
there, before anything is written, instead of letting the three writers
after it crash on None. The third audit's @overloads let mypy see this.

Run with: pytest tests/test_current_ratings.py -v
"""

import pandas as pd
import pytest

from src.sports.nfl import weekly_update as wu
from src.sports.nfl.config import MIN_PLAYS_FOR_RATING


def plays(n):
    """n plays alternating between two teams, all in the first of two weeks,
    shaped as prep_plays leaves them."""
    teams = ['KC', 'BUF']
    return pd.DataFrame({
        'posteam': [teams[i % 2] for i in range(n)],
        'defteam': [teams[(i + 1) % 2] for i in range(n)],
        'epa': [0.1 if i % 2 else -0.1 for i in range(n)],
        'gwidx': [0] * n,
    }), [(2026, 1), (2026, 2)]


def test_too_few_plays_stop_the_run_before_anything_is_written():
    p, weeks = plays(MIN_PLAYS_FOR_RATING - 1)
    with pytest.raises(SystemExit, match=f'fewer than {MIN_PLAYS_FOR_RATING} plays'):
        wu.current_ratings(p, weeks)


def test_enough_plays_give_every_team_a_rating():
    p, weeks = plays(MIN_PLAYS_FOR_RATING)
    got = wu.current_ratings(p, weeks)
    assert set(got) == {'KC', 'BUF'}
    assert all(len(v) == 2 for v in got.values())


def test_the_live_run_uses_it():
    """refresh_current_state takes its ratings from current_ratings, not
    from build_team_ratings directly, so the guard is on the path the run
    takes."""
    import inspect
    src = inspect.getsource(wu.refresh_current_state)
    assert 'current_ratings(plays, week_keys)' in src
    assert 'build_team_ratings(' not in src
