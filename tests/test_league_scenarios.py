"""
Named scenarios on the synthetic league, each with the outcome it must have
(Stage 39 item 1, from the 2026-10-04 fourth audit). The first two are the
ways a game can fail to finish when it was scheduled to:

  postponed -- the week locks, then the schedule moves one game to a later
               day. The weeks around it are graded without it, the lock is
               never rewritten, and the game is graded by the first run
               after it is played: every weekly run grades every saved week.
  cancelled -- the game is never played and never gets a score. It is never
               graded, so it counts for no model and the drift check leaves
               it out, and the rest of its week grades normally.

(nflverse kept 2022's cancelled Bills-Bengals game as a row with no score,
which is what the fixture does here.)

The tie, the third way a game ends without a winner, is in
tests/test_pipeline_chain_end_to_end.py. The calendar cases (a Wednesday
game, Thanksgiving, a Saturday-first week) are decided by decide_lock and
held in tests/test_pick_lock_time.py.

Run with: pytest tests/test_league_scenarios.py -v
"""
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent))

import synthetic_league as league

from src.sports.nfl import check_drift as cd
from src.sports.nfl import data_loader
from src.sports.nfl import grade_predictions as gp
from src.sports.nfl import weekend_refresh as wr
from src.sports.nfl import weekly_update as wu

H = pd.Timedelta(hours=1)
S, W = league.TARGET, league.TARGET_WEEK
# round_robin(5)'s games in order; the first is the one that does not finish.
SCORES = [(None, None), (27, 17), (31, 24), (10, 13)]
HOME, AWAY = league.round_robin(W)[0]


def with_results(schedules, scores, moved_to=None):
    """A copy of `schedules` with week W's results: scores[k] is (home, away)
    for the k-th game of round_robin(W), or (None, None) for no result. With
    `moved_to`, the first game's kickoff moves to that time (UTC)."""
    sched = schedules[S].copy()
    for k, ((home, away), (hs, as_)) in enumerate(zip(league.round_robin(W), scores)):
        at = (sched['week'] == W) & (sched['home_team'] == home) & (sched['away_team'] == away)
        assert at.sum() == 1, (home, away)
        if hs is not None:
            sched.loc[at, ['home_score', 'away_score']] = [float(hs), float(as_)]
        if k == 0 and moved_to is not None:
            sched.loc[at, ['gameday', 'gametime', 'weekday']] = list(league._kickoff_fields(moved_to))
    return {**schedules, S: sched}


@pytest.fixture
def week(monkeypatch, tmp_path):
    """Lock week W on the synthetic league; return a namespace with the
    folders, the schedules, `now`, and use(schedules) to change what every
    step reads from then on."""
    dirs = {'pred': tmp_path / 'predictions', 'results': tmp_path / 'results',
            'status': tmp_path / 'data' / 'game_status', 'data': tmp_path / 'data'}
    for p in dirs.values():
        p.mkdir(parents=True, exist_ok=True)
    for name, path in (('PRED_DIR', dirs['pred']), ('SKIPPED_DIR', dirs['pred'] / 'skipped'),
                       ('PREVIEW_DIR', dirs['pred'] / 'preview'), ('DATA_DIR', dirs['data']),
                       ('LINE_HISTORY_DIR', dirs['data'] / 'line_history'),
                       ('QB_OVERRIDE_DIR', dirs['data'] / 'qb_overrides')):
        path.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(wu, name, path)
    real_simulate = wu.simulate_season
    monkeypatch.setattr(wu, 'simulate_season',
                        lambda *a, n_sim=10000, **k: real_simulate(*a, n_sim=200, **k))
    now = pd.Timestamp.now(tz='UTC')
    pbp, schedules = league.build(now, [H, 2 * H, 3 * H, 4 * H])
    monkeypatch.setattr(wu, 'load_plays', lambda seasons: pbp[pbp['season'].isin(seasons)])
    monkeypatch.setattr(wu, 'load_schedule',
                        lambda season: schedules.get(season, league.empty_schedule()))
    wu.main(S, W)
    lock = dirs['pred'] / f'{S}_week{W}.json'
    assert lock.exists(), "the week did not lock"

    current = {}

    def use(new):
        current['schedules'] = new
        monkeypatch.setattr(data_loader, 'load_schedule', lambda season: new[season])

    monkeypatch.setattr(gp, 'PRED_DIR', dirs['pred'])
    monkeypatch.setattr(gp, 'RESULTS_DIR', dirs['results'])
    monkeypatch.setattr(cd, 'RESULTS_DIR', dirs['results'])

    class Week:
        pass
    w = Week()
    w.dirs, w.schedules, w.now, w.lock, w.use = dirs, schedules, now, lock, use
    w.locked_bytes = lock.read_bytes()
    w.refresh = lambda at: wr.main(['--season', str(S)], now=at,
                                   load=lambda season: current['schedules'][season],
                                   pred_dir=dirs['pred'], results_dir=dirs['results'],
                                   status_dir=dirs['status'])
    w.graded = lambda: json.loads((dirs['results'] / f'{S}_week{W}_graded.json').read_text(encoding='utf-8'))
    w.open_weeks = lambda: wr.weeks_to_refresh(S, pred_dir=dirs['pred'], results_dir=dirs['results'])
    w.status = lambda: {(g['home'], g['away']): g['status'] for g in json.loads(
        (dirs['status'] / f'{S}_week{W}.json').read_text(encoding='utf-8'))['games']}
    return w


# --- postponed ----------------------------------------------------------------

def test_a_postponed_game_waits_ungraded_and_reads_as_upcoming(week):
    later = week.now + pd.Timedelta(days=2)
    week.use(with_results(week.schedules, SCORES, moved_to=later))
    gp.main(S, W)
    assert {(r['home'], r['away']) for r in week.graded()} == set(league.round_robin(W)[1:])
    assert week.refresh(week.now + 6 * H) == 0
    status = week.status()
    assert status[(HOME, AWAY)] == 'upcoming'
    assert [s for pair, s in status.items() if pair != (HOME, AWAY)] == ['final'] * 3
    assert week.open_weeks() == [W]


def test_a_postponed_game_is_graded_by_the_first_run_after_it_is_played(week):
    later = week.now + pd.Timedelta(days=2)
    week.use(with_results(week.schedules, SCORES, moved_to=later))
    gp.main(S, W)
    week.use(with_results(week.schedules, [(20, 17)] + SCORES[1:], moved_to=later))
    gp.main(S, W)
    rows = {(r['home'], r['away']): r for r in week.graded()}
    assert len(rows) == 4
    assert rows[(HOME, AWAY)]['actual_home_win'] == 1
    assert week.open_weeks() == []


def test_a_postponement_never_rewrites_the_lock(week):
    later = week.now + pd.Timedelta(days=2)
    week.use(with_results(week.schedules, SCORES, moved_to=later))
    gp.main(S, W)
    week.refresh(week.now + 6 * H)
    week.use(with_results(week.schedules, [(20, 17)] + SCORES[1:], moved_to=later))
    gp.main(S, W)
    assert week.lock.read_bytes() == week.locked_bytes
    original = {(p['home'], p['away']): p['gameday'] for p in json.loads(week.locked_bytes)}
    assert original[(HOME, AWAY)] != league._kickoff_fields(later)[0]


# --- cancelled ----------------------------------------------------------------

def test_a_cancelled_game_is_never_graded_and_the_rest_of_its_week_is(week):
    week.use(with_results(week.schedules, SCORES))
    gp.main(S, W)
    rows = week.graded()
    assert {(r['home'], r['away']) for r in rows} == set(league.round_robin(W)[1:])
    for r in rows:
        for key in ('model_a_correct', 'model_b_correct', 'market_correct'):
            assert r[key] in (0, 1), (key, r)


def test_the_drift_check_counts_only_the_games_played(week, capsys):
    week.use(with_results(week.schedules, SCORES))
    gp.main(S, W)
    capsys.readouterr()
    assert cd.main() == 0
    out = capsys.readouterr().out
    assert out.count('Live games graded: 3') == 2, out


def test_a_cancelled_games_week_stays_open_but_is_not_rewritten_while_nothing_changes(week, capsys):
    """The week has fewer graded games than picks, so every weekend refresh
    looks at it again. A snapshot with no change is not written, so it
    costs a read, not a commit."""
    week.use(with_results(week.schedules, SCORES))
    gp.main(S, W)
    week.refresh(week.now + 6 * H)
    capsys.readouterr()
    week.refresh(week.now + 30 * H)
    assert 'unchanged, not rewritten' in capsys.readouterr().out
    assert week.open_weeks() == [W]
