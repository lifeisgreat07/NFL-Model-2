"""
weekly_update.main(), run for real on the synthetic league in
tests/synthetic_league.py: no network, about a second.

Before this file, every test of main() read its source, because main()
needs six seasons of nflverse play-by-play. These tests run it instead,
with the two loaders replaced by the fixture and every directory it writes
pointed at tmp_path. They cover each way a run can end:

  lock        -- the week is saved, with the schema below, once, and never
                 overwritten by a second run
  preview     -- held for the next scheduled run; a preview is saved, no lock
  started     -- a game that already kicked off gets no pick; the rest lock
  all started -- nothing was ever locked: the run fails and records the skip
  too early   -- outside the lock-in window: nothing is saved at all

The only other substitution is the season simulation's draw count, cut from
10,000 to 200 so the test stays fast. The simulation itself still runs.

Run with: pytest tests/test_weekly_update_end_to_end.py -v
"""
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / 'src'))
sys.path.insert(0, str(Path(__file__).parent))

import synthetic_league as league  # noqa: E402
import weekly_update as wu  # noqa: E402
from config import MODEL_VERSION  # noqa: E402

H = pd.Timedelta(hours=1)

# Every key a saved pick carries. generate_dashboard.py, grade_predictions.py
# and the Week Board read these files, and a saved file is permanent, so a key
# added or dropped here is an interface change for every week saved after it.
PICK_KEYS = {
    'season', 'week', 'home', 'away', 'gameday', 'gametime_et', 'weekday',
    'model_version', 'off_matchup', 'def_matchup', 'qb_matchup', 'qb_change_diff',
    'spread_line', 'model_a_home_win_prob', 'model_b_home_win_prob',
    'market_prob_home', 'context_notes', 'why', 'confidence_rank',
    'confidence_points',
    *(f'{prefix}{side}_qb{suffix}'
      for side in ('home', 'away')
      for prefix, suffix in (('', ''), ('', '_id'), ('', '_basis'),
                             ('announced_', ''), ('announced_', '_id'),
                             ('last_game_', ''), ('last_game_', '_id'))),
}


@pytest.fixture
def run(monkeypatch, tmp_path, capsys):
    """run(offsets) -> (stdout, tmp_path): main() on the synthetic league,
    with week 5's four kickoffs at now + offsets."""
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
    monkeypatch.setattr(wu, 'simulate_season',
                        lambda *a, n_sim=10000, **k: real_simulate(*a, n_sim=200, **k))

    def go(offsets):
        pbp, schedules = league.build(pd.Timestamp.now(tz='UTC'), offsets)
        monkeypatch.setattr(wu, 'load_plays', lambda seasons: pbp[pbp['season'].isin(seasons)])
        monkeypatch.setattr(wu, 'load_schedule',
                            lambda season: schedules.get(season, league.empty_schedule()))
        wu.main(league.TARGET, league.TARGET_WEEK)
        return capsys.readouterr().out, tmp_path
    return go


def locked(tmp):
    return tmp / 'predictions' / f'{league.TARGET}_week{league.TARGET_WEEK}.json'


def previews(tmp):
    return sorted((tmp / 'predictions' / 'preview').glob('*.json'))


# --- the fixture --------------------------------------------------------------

def test_the_fixture_is_a_real_round_robin():
    """Each team plays once a week and meets every other team once, so a
    fixture bug cannot pass itself off as a pipeline result."""
    seen = set()
    for week in range(1, league.LAST_WEEK + 1):
        games = league.round_robin(week)
        teams = [t for g in games for t in g]
        assert sorted(teams) == sorted(league.TEAMS), (week, games)
        seen |= {frozenset(g) for g in games}
    assert len(seen) == len(league.TEAMS) * (len(league.TEAMS) - 1) // 2


# --- lock ---------------------------------------------------------------------

def test_a_week_inside_the_lock_saves_every_game_with_the_full_schema(run):
    out, tmp = run([H, 2 * H, 3 * H, 4 * H])
    picks = json.loads(locked(tmp).read_text(encoding='utf-8'))
    assert len(picks) == 4, out
    for p in picks:
        assert set(p) == PICK_KEYS, f"keys differ: {sorted(set(p) ^ PICK_KEYS)}"
        assert p['season'] == league.TARGET and p['week'] == league.TARGET_WEEK
        assert p['model_version'] == MODEL_VERSION
        for key in ('model_a_home_win_prob', 'model_b_home_win_prob', 'market_prob_home'):
            assert 0 < p[key] < 1, (key, p[key])
        assert p['gameday'] and p['gametime_et'] and p['weekday']
    assert sorted(p['confidence_rank'] for p in picks) == [1, 2, 3, 4]
    assert sorted(p['confidence_points'] for p in picks) == [1, 2, 3, 4]
    assert {(p['away'], p['home']) for p in picks} == {
        (a, h) for h, a in league.round_robin(league.TARGET_WEEK)}
    assert not previews(tmp)


def test_the_starters_come_from_the_schedule(run):
    """The fixture lists each team's quarterback on the schedule, so every
    pick names that player as the schedule's, not last game's fallback."""
    _, tmp = run([H, 2 * H, 3 * H, 4 * H])
    for p in json.loads(locked(tmp).read_text(encoding='utf-8')):
        for side in ('home', 'away'):
            assert p[f'{side}_qb'] == league.QB[p[side]][1], p
            assert p[f'{side}_qb_basis'] == 'announced', p


def test_a_sourced_override_replaces_the_listed_starter(run, tmp_path):
    """The Thursday case: the schedule still lists a starter who has been
    ruled out, and a sourced override names the one who plays."""
    home, away = league.round_robin(league.TARGET_WEEK)[0]
    (tmp_path / 'data' / 'qb_overrides').mkdir(parents=True, exist_ok=True)
    (tmp_path / 'data' / 'qb_overrides' / f'{league.TARGET}_week{league.TARGET_WEEK}.json').write_text(
        json.dumps([{'team': home, 'player_id': '00-0009999', 'player_name': 'B.Ackup',
                     'source': 'https://example.com/injury-report'}]), encoding='utf-8')
    out, tmp = run([H, 2 * H, 3 * H, 4 * H])
    [pick] = [p for p in json.loads(locked(tmp).read_text(encoding='utf-8')) if p['home'] == home]
    assert (pick['home_qb'], pick['home_qb_basis']) == ('B.Ackup', 'override')
    assert pick['announced_home_qb'] == league.QB[home][1]
    assert pick['qb_change_diff'] == 1, "a new starter has to count as a change"
    assert any('B.Ackup is expected to start' in n for n in pick['context_notes'])
    assert f'{home} -> B.Ackup' in out


def test_a_locking_run_writes_the_ratings_odds_history_and_lines(run):
    _, tmp = run([H, 2 * H, 3 * H, 4 * H])
    ratings = json.loads((tmp / 'data' / 'current_ratings.json').read_text())
    assert {r['team'] for r in ratings} == set(league.TEAMS)
    assert all(r['games_played'] == league.PLAYED_WEEKS for r in ratings)
    odds = json.loads((tmp / 'data' / 'playoff_odds.json').read_text())
    assert odds['season'] == league.TARGET and odds['games_played'] == 4 * league.PLAYED_WEEKS
    history = json.loads((tmp / 'data' / f'team_history_{league.TARGET}.json').read_text())
    assert all(e[-1]['week'] == league.PLAYED_WEEKS for e in history.values())
    lines = tmp / 'data' / 'line_history' / f'{league.TARGET}_week{league.TARGET_WEEK}_lines.json'
    assert lines.exists()


def test_a_second_run_never_overwrites_a_locked_week(run):
    _, tmp = run([H, 2 * H, 3 * H, 4 * H])
    first = locked(tmp).read_bytes()
    out, _ = run([H, 2 * H, 3 * H, 4 * H])
    assert locked(tmp).read_bytes() == first
    assert 'NOT overwriting' in out


# --- the other endings -----------------------------------------------------------

def test_a_week_after_the_next_scheduled_run_is_previewed_not_locked(run):
    """Six days out is inside the seven-day window but after the next
    scheduled run (at most five days away) plus its slack."""
    week_out = pd.Timedelta(days=6)
    out, tmp = run([week_out, week_out + H, week_out + 2 * H, week_out + 3 * H])
    assert not locked(tmp).exists(), out
    [preview] = previews(tmp)
    rows = json.loads(preview.read_text(encoding='utf-8'))
    assert len(rows) == 4 and all(r['preview'] is True for r in rows)


def test_a_game_that_already_kicked_off_gets_no_pick(run):
    out, tmp = run([-H, 2 * H, 3 * H, 4 * H])
    picks = json.loads(locked(tmp).read_text(encoding='utf-8'))
    home, away = league.round_robin(league.TARGET_WEEK)[0]
    assert len(picks) == 3
    assert (away, home) not in {(p['away'], p['home']) for p in picks}
    assert f'{away}@{home} has already kicked off' in out


def test_a_week_that_all_kicked_off_unlocked_fails_and_is_skipped(run, tmp_path):
    with pytest.raises(SystemExit, match='nothing was ever locked'):
        run([-4 * H, -3 * H, -2 * H, -H])
    assert not locked(tmp_path).exists()
    [skip] = sorted((tmp_path / 'predictions' / 'skipped').glob('*.json'))
    assert f'week{league.TARGET_WEEK}' in skip.name


def test_a_locked_week_run_again_after_kickoff_is_left_alone(run, tmp_path):
    """Stage 30 item 4. A week that is already locked, run again by hand
    (`--week N`) after every game has kicked off, used to fall into the
    skip branch: a skip record beside the saved picks, and a failed run."""
    run([H, 2 * H, 3 * H, 4 * H])
    first = locked(tmp_path).read_bytes()
    out, _ = run([-4 * H, -3 * H, -2 * H, -H])
    assert 'already locked' in out
    assert locked(tmp_path).read_bytes() == first
    assert not list((tmp_path / 'predictions' / 'skipped').glob('*.json'))


def test_a_week_outside_the_lock_in_window_saves_nothing(run):
    far = pd.Timedelta(days=10)
    out, tmp = run([far, far + H, far + 2 * H, far + 3 * H])
    assert 'lock-in window' in out
    assert not locked(tmp).exists() and not previews(tmp)
