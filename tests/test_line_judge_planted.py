"""
Stage 44 item 4: a planted bad run in the synthetic league that Line Judge
must flag (src/sports/nfl/line_judge.py).

The Weekly update runs for real on tests/synthetic_league.py (as in
tests/test_weekly_update_end_to_end.py) and locks week 5; weeks 1-4, played
before the run, are recorded as skipped the way the pipeline records them.
Line Judge then reads what that run left behind. A right run gives no
finding; each planted fault -- the kind a green run could leave on main --
gives exactly the finding meant for it:

  a lock committed after the first kickoff        -> before-kickoff
  a game still to come dropped from the lock      -> before-kickoff
  a started week neither locked nor skipped       -> every-week
  a week played out and left ungraded             -> graded

Run with: pytest tests/test_line_judge_planted.py -v
"""
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent))

import synthetic_league as league

from src.sports.nfl import line_judge as lj
from src.sports.nfl import weekly_update as wu

H = pd.Timedelta(hours=1)
OFFSETS = [H, 2 * H, 3 * H, 4 * H]


@pytest.fixture
def week5(monkeypatch, tmp_path, capsys):
    """The Weekly update's real run on the synthetic league, week 5 locking
    an hour before its first kickoff. Returns (dirs, schedule, run_time)."""
    dirs = {
        'PRED_DIR': tmp_path / 'predictions',
        'SKIPPED_DIR': tmp_path / 'predictions' / 'skipped',
        'PREVIEW_DIR': tmp_path / 'predictions' / 'preview',
        'DATA_DIR': tmp_path / 'data',
        'LINE_HISTORY_DIR': tmp_path / 'data' / 'line_history',
        'QB_OVERRIDE_DIR': tmp_path / 'data' / 'qb_overrides',
    }
    for name, path in dirs.items():
        path.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(wu, name, path)
    real_simulate = wu.simulate_season
    monkeypatch.setattr(wu, 'simulate_season', lambda *a, n_sim=10000, **k: real_simulate(*a, n_sim=200, **k))
    now = pd.Timestamp.now(tz='UTC').floor('s')
    pbp, schedules = league.build(now, OFFSETS)
    monkeypatch.setattr(wu, 'load_plays', lambda seasons: pbp[pbp['season'].isin(seasons)])
    monkeypatch.setattr(wu, 'load_schedule', lambda season: schedules.get(season, league.empty_schedule()))
    wu.main(league.TARGET, league.TARGET_WEEK)
    capsys.readouterr()
    for week in range(1, league.PLAYED_WEEKS + 1):
        wu.record_skipped_week(league.TARGET, week, 'played before the run under test', now,
                               dirs['SKIPPED_DIR'])
    results = tmp_path / 'results'
    results.mkdir()
    dirs['RESULTS_DIR'] = results
    return dirs, schedules, now


def judge(dirs, schedule, now, saved_at):
    return lj.judge(league.TARGET, schedule, now, lambda path: saved_at, set(),
                    pred_dir=dirs['PRED_DIR'], skipped_dir=dirs['SKIPPED_DIR'], results_dir=dirs['RESULTS_DIR'])


def lock_file(dirs):
    return dirs['PRED_DIR'] / f'{league.TARGET}_week{league.TARGET_WEEK}.json'


def test_the_real_run_leaves_nothing_to_flag(week5):
    dirs, schedules, now = week5
    assert len(json.loads(lock_file(dirs).read_text(encoding='utf-8'))) == 4
    # Judged after the whole week has kicked off, with the lock where the run saved it.
    assert judge(dirs, schedules[league.TARGET], now + 5 * H, now) == []


def test_a_lock_committed_after_the_first_kickoff_is_flagged(week5):
    dirs, schedules, now = week5
    found = judge(dirs, schedules[league.TARGET], now + 5 * H, now + 90 * pd.Timedelta(minutes=1))
    assert [f.check for f in found] == ['before-kickoff']
    assert 'before its pick was first saved' in found[0].message


def test_a_game_still_to_come_dropped_from_the_lock_is_flagged(week5):
    dirs, schedules, now = week5
    picks = json.loads(lock_file(dirs).read_text(encoding='utf-8'))
    dropped = picks.pop()
    lock_file(dirs).write_text(json.dumps(picks), encoding='utf-8')
    found = judge(dirs, schedules[league.TARGET], now + 5 * H, now)
    assert [f.check for f in found] == ['before-kickoff']
    assert f"{dropped['away']} at {dropped['home']} had not kicked off" in found[0].message


def test_a_started_week_neither_locked_nor_skipped_is_flagged(week5):
    dirs, schedules, now = week5
    (dirs['SKIPPED_DIR'] / f'{league.TARGET}_week3.json').unlink()
    found = judge(dirs, schedules[league.TARGET], now + 5 * H, now)
    assert [f.check for f in found] == ['every-week'] and 'week 3 kicked off' in found[0].message


def test_a_week_played_out_and_left_ungraded_is_flagged(week5):
    dirs, schedules, now = week5
    played = league.play_week(schedules, league.TARGET_WEEK, [(24, 17), (20, 23), (31, 10), (13, 16)])
    found = judge(dirs, played[league.TARGET], now + 9 * H, now)
    assert [f.check for f in found] == ['graded']
    assert 'every picked game is final and there is no graded file' in found[0].message
