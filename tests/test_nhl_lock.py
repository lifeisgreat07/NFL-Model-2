"""The NHL's per-game lock: each game saved by the last run before its start.

Stage 54 item 1. Times here are UTC; Eastern is UTC-4 in October.

Run with: pytest tests/test_nhl_lock.py -v
"""
from datetime import UTC, datetime, timedelta

import pandas as pd

from src.core.sport import LockDecision, LockUnit
from src.sports.nhl import lock as nhl_lock


def slate(*games):
    rows = []
    for gid, start, status in games:
        rows.append({'game_id': gid, 'slate': '2026-10-10', 'status': status,
                     'start_utc': pd.Timestamp(start, tz='UTC') if start else pd.NaT})
    return pd.DataFrame(rows)


RULE = nhl_lock.GameLock()


def at(hour, minute=0, day=10):
    return datetime(2026, 10, day, hour, minute, tzinfo=UTC)


def test_it_answers_in_the_cores_words_and_locks_game_by_game():
    assert RULE.unit is LockUnit.GAME
    assert isinstance(RULE.decide(slate(), at(14)), LockDecision)


def test_runs_are_twice_a_day_every_day():
    assert len(nhl_lock.RUNS_UTC) == 14
    assert nhl_lock.next_run(at(10)) == pd.Timestamp(at(14))
    assert nhl_lock.next_run(at(14)) == pd.Timestamp(at(21))
    assert nhl_lock.next_run(at(22)) == pd.Timestamp(at(14, day=11))


def test_the_morning_run_saves_afternoon_games_and_holds_evening_ones():
    s = slate(('afternoon', '2026-10-10 17:00', 'scheduled'), ('evening', '2026-10-10 23:00', 'scheduled'))
    d = RULE.decide(s, at(14))
    assert d.lock == ('afternoon',) and d.hold == ('evening',) and d.started == ()
    assert d.next_run == at(21)


def test_the_evening_run_saves_everything_starting_before_tomorrow_morning():
    s = slate(('seven', '2026-10-10 23:00', 'scheduled'), ('late', '2026-10-11 02:30', 'scheduled'))
    assert RULE.decide(s, at(21)).lock == ('seven', 'late')


def test_a_game_starting_within_the_slack_after_the_next_run_locks_now():
    """The next run may start late; a game it might miss is saved now."""
    s = slate(('edge', '2026-10-10 21:30', 'scheduled'), ('clear', '2026-10-10 22:30', 'scheduled'))
    d = RULE.decide(s, at(14))
    assert d.lock == ('edge',) and d.hold == ('clear',)


def test_a_game_that_has_started_is_never_predicted():
    s = slate(('past', '2026-10-10 13:00', 'scheduled'), ('live', '2026-10-10 12:00', 'in_progress'),
              ('done', '2026-10-09 23:00', 'final'))
    d = RULE.decide(s, at(14))
    assert set(d.started) == {'past', 'live', 'done'} and d.lock == () and d.hold == ()


def test_postponed_suspended_and_cancelled_games_are_not_locked_or_held():
    s = slate(('ppd', '2026-10-10 17:00', 'postponed'), ('susp', '2026-10-10 17:00', 'suspended'),
              ('cncl', '2026-10-10 17:00', 'cancelled'))
    d = RULE.decide(s, at(14))
    assert d.lock == d.hold == d.started == ()


def test_a_game_with_no_time_counts_from_the_start_of_its_day():
    s = slate(('tbd', None, 'scheduled'))
    assert nhl_lock.start_of(s.iloc[0]) == pd.Timestamp('2026-10-10 04:00', tz='UTC')
    assert RULE.decide(s, at(2)).lock == ('tbd',)
    assert RULE.decide(s, at(14)).started == ('tbd',)


def test_the_slack_is_an_hour():
    assert nhl_lock.SLACK == timedelta(hours=1)
