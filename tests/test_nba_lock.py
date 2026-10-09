"""The NBA's per-game lock (Stage 65): each game saved by the last run
before its start, at the run times the registration names.

Times here are UTC; Eastern is UTC-4 in October.

Run with: pytest tests/test_nba_lock.py -v
"""
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd

from src.core.sport import LockDecision, LockUnit
from src.sports.nba import lock as nba_lock

ROOT = Path(__file__).resolve().parents[1]
REG = json.loads((ROOT / 'experiments/nba/stage65/registry.json').read_text(encoding='utf-8'))


def slate(*games):
    rows = []
    for gid, start, status in games:
        rows.append({'game_id': gid, 'slate': '2026-10-21', 'status': status,
                     'start_utc': pd.Timestamp(start, tz='UTC') if start else pd.NaT})
    return pd.DataFrame(rows)


RULE = nba_lock.GameLock()


def at(hour, minute=0, day=21):
    return datetime(2026, 10, day, hour, minute, tzinfo=UTC)


def test_the_run_times_and_slack_are_the_registered_ones():
    runs = REG['forward_test']['runs']
    assert runs.startswith('16:00 and 21:30 UTC every day') and 'next run plus one hour' in runs
    assert sorted({(h, m) for _, h, m in nba_lock.RUNS_UTC}) == [(16, 0), (21, 30)]
    assert {d for d, _, _ in nba_lock.RUNS_UTC} == set(range(7)) and len(nba_lock.RUNS_UTC) == 14
    assert nba_lock.SLACK == timedelta(hours=1)


def test_it_answers_in_the_cores_words_and_locks_game_by_game():
    assert RULE.unit is LockUnit.GAME
    assert isinstance(RULE.decide(slate(), at(16)), LockDecision)


def test_next_run():
    assert nba_lock.next_run(at(10)) == pd.Timestamp(at(16))
    assert nba_lock.next_run(at(16)) == pd.Timestamp(at(21, 30))
    assert nba_lock.next_run(at(22)) == pd.Timestamp(at(16, day=22))


def test_opening_night_saves_at_the_evening_run():
    """2026-10-21's first tips are 23:00 UTC: held at 16:00, saved at 21:30
    with the 02:30 game, since the next run is 16:00 tomorrow."""
    s = slate(('seven', '2026-10-21 23:00', 'scheduled'), ('late', '2026-10-22 02:30', 'scheduled'))
    early = RULE.decide(s, at(16))
    assert early.lock == () and early.hold == ('seven', 'late')
    assert RULE.decide(s, at(21, 30)).lock == ('seven', 'late')


def test_a_weekend_noon_game_is_saved_the_night_before():
    """A 12 PM Eastern tip (16:00 UTC) would have started by the 16:00 run,
    so the 21:30 run before it saves it."""
    s = slate(('noon', '2026-10-25 16:00', 'scheduled'))
    assert RULE.decide(s, at(21, 30, day=24)).lock == ('noon',)


def test_a_game_within_the_slack_after_the_next_run_locks_now():
    s = slate(('edge', '2026-10-21 22:00', 'scheduled'), ('clear', '2026-10-21 23:00', 'scheduled'))
    d = RULE.decide(s, at(16))
    assert d.lock == ('edge',) and d.hold == ('clear',)


def test_a_started_game_is_never_predicted():
    s = slate(('gone', '2026-10-21 15:00', 'scheduled'), ('live', '2026-10-21 23:00', 'in_progress'),
              ('done', '2026-10-21 23:00', 'final'))
    d = RULE.decide(s, at(16))
    assert d.started == ('gone', 'live', 'done') and d.lock == () and d.hold == ()


def test_postponed_and_cancelled_games_are_in_no_list():
    s = slate(('pp', '2026-10-21 23:00', 'postponed'), ('cx', '2026-10-21 23:00', 'cancelled'))
    d = RULE.decide(s, at(21, 30))
    assert d.lock == d.hold == d.started == ()


def test_a_game_with_no_time_counts_from_the_start_of_its_date():
    """No time on 10-21 counts as 04:00 UTC that day (midnight Eastern), so
    the 21:30 run of the day before saves it, where 23:00 would be held."""
    d = RULE.decide(slate(('tbd', None, 'scheduled')), at(21, 30, day=20))
    assert d.lock == ('tbd',)
    assert RULE.decide(slate(('tbd', None, 'scheduled')), at(16, day=20)).hold == ('tbd',)
