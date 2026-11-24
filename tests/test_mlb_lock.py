"""MLB's per-game lock (Stage 101 item 3): each game saved by the last run at least an hour before its first pitch,
at the run times spring training's measurement chose, with an unset start following its doubleheader.

The run times here are made up (17:00, 22:00 and 23:30 UTC); the real ones are chosen in March 2027.

Run with: pytest tests/test_mlb_lock.py -v
"""
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

from src.core.sport import LockDecision, LockUnit
from src.sports.mlb import lock as mlb_lock
from src.sports.mlb import probables_timing

ROOT = Path(__file__).resolve().parents[1]
REG = json.loads((ROOT / 'experiments/mlb/stage101/registry.json').read_text(encoding='utf-8'))
RUNS = tuple((d, h, m) for d in range(7) for h, m in ((17, 0), (22, 0), (23, 30)))
RULE = mlb_lock.GameLock(runs=RUNS)


def at(hour, minute=0, day=1):
    return datetime(2027, 4, day, hour, minute, tzinfo=UTC)


def game(gid, start, status='scheduled', home='147', away='111', tbd=False, day='2027-04-01'):
    return {'game_id': gid, 'slate': day, 'status': status, 'home': home, 'away': away,
            'start_utc': pd.Timestamp(start, tz='UTC'), 'start_time_tbd': tbd}


def slate(*games):
    return pd.DataFrame(list(games))


def test_it_answers_in_the_cores_words_and_locks_game_by_game():
    assert RULE.unit is LockUnit.GAME and mlb_lock.SLACK == timedelta(hours=1)
    assert isinstance(RULE.decide(slate(game('1', '2027-04-01 23:05')), at(17)), LockDecision)
    assert 'last run at least one hour before' in REG['forward_test']['runs']['lock']


def test_a_game_is_saved_by_the_last_run_an_hour_before_it():
    s = slate(game('day', '2027-04-01 17:35'), game('night', '2027-04-01 23:05'), game('late', '2027-04-02 02:10'))
    morning = RULE.decide(s, at(12))  # next run 17:00: the 17:35 game is inside its hour, so it locks now
    assert morning.lock == ('day',) and morning.hold == ('night', 'late')
    five = RULE.decide(s, at(17))  # next run 22:00: 23:05 is not inside its hour, so it waits
    assert five.lock == ('day',) and five.hold == ('night', 'late')
    ten = RULE.decide(s, at(22))  # next run 23:30: 23:05 locks; 02:10 is held for 23:30
    assert ten.started == ('day',) and ten.lock == ('night',) and ten.hold == ('late',)
    half = RULE.decide(s, at(23, 30))  # next run 17:00 tomorrow: 02:10 locks now
    assert half.started == ('day', 'night') and half.lock == ('late',)


def test_a_started_or_finished_game_is_never_predicted_and_a_postponed_one_is_left_out():
    s = slate(game('on', '2027-04-01 17:35', status='in_progress'), game('done', '2027-04-01 17:35', status='final'),
              game('passed', '2027-04-01 17:35'), game('off', '2027-04-01 23:05', status='postponed'),
              game('gone', '2027-04-01 23:05', status='cancelled'), game('susp', '2027-04-01 23:05', status='suspended'))
    d = RULE.decide(s, at(18))
    assert d.started == ('on', 'done', 'passed') and d.lock == () and d.hold == ()


def test_an_unset_start_is_saved_with_the_other_game_of_its_doubleheader():
    # Game 1 at 17:05; game 2's listed time is a placeholder before it. Game 2 locks when game 1 does.
    s = slate(game('g1', '2027-04-01 17:05'), game('g2', '2027-04-01 07:33', tbd=True))
    assert RULE.decide(s, at(12)).lock == ('g1', 'g2')
    held = slate(game('g1', '2027-04-01 23:05'), game('g2', '2027-04-01 07:33', tbd=True))
    d = RULE.decide(held, at(12))
    assert d.hold == ('g1', 'g2') and d.started == ()


def test_an_unset_start_whose_other_game_is_under_way_is_saved_at_once():
    s = slate(game('g1', '2027-04-01 17:05', status='in_progress'), game('g2', '2027-04-01 07:33', tbd=True))
    d = RULE.decide(s, at(18))
    assert d.started == ('g1',) and d.lock == ('g2',)


def test_an_unset_start_with_no_game_to_follow_goes_by_its_placeholder():
    # The other game was postponed, and another club's game the same day is not its doubleheader.
    s = slate(game('g1', '2027-04-01 17:05', status='postponed'), game('g2', '2027-04-02 07:33', tbd=True),
              game('other', '2027-04-01 17:05', home='121'))
    d = RULE.decide(s, at(17))
    assert 'g2' in d.hold
    assert 'g2' in RULE.decide(s, at(23, 30)).lock


def test_no_run_times_no_lock(tmp_path):
    with pytest.raises(mlb_lock.MLBLockError, match='not set'):
        mlb_lock.registered_runs(tmp_path / 'probables_timing.json')


def test_the_run_times_are_the_three_the_rule_wrote(tmp_path):
    path = tmp_path / 'probables_timing.json'
    path.write_text(json.dumps({'times_utc': ['17:00', '09:00', '09:30']}), encoding='utf-8')
    runs = mlb_lock.registered_runs(path)
    assert len(runs) == 21 and {(h, m) for _, h, m in runs} == {(9, 0), (9, 30), (17, 0)}
    path.write_text(json.dumps({'times_utc': ['17:00', '17:00', '09:30']}), encoding='utf-8')
    with pytest.raises(mlb_lock.MLBLockError, match='three different'):
        mlb_lock.registered_runs(path)


def test_the_lock_reads_the_file_the_rule_writes():
    assert mlb_lock.RUN_TIMES == probables_timing.CHOSEN
