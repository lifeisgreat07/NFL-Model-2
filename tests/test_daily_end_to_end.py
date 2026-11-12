"""Each day sport's daily run, end to end, with no network (Stage 68 item 15, E29).

`daily.main` had never run whole in a test for either sport: every piece
was tested alone, and the join between them only ran in the workflow. Here
each runs over the committed history and schedule, with every outside
source answered by a stub: no price (so Model A makes the pick), no
projected goalie, no injury report. Everything it writes goes to a
temporary folder. The run must save a pick for each game it locks, grade,
write the drift check and the page inputs, and, run again at the same
moment, save nothing twice.

Each run reads the committed schedule AS IT STOOD at the run's own moment:
every game that starts at or after it is put back to scheduled, with no
score. The daily runs rewrite that file, so read as it is today the test's
games had gone final under it: on 2026-10-11 the NHL test locked nothing and
failed (issue #425), and the NBA test would have done the same after its
opening night.

Run with: pytest tests/test_daily_end_to_end.py -v
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from tests.shared_tables import share_nba_tables, share_nhl_features

ROOT = Path(__file__).resolve().parents[1]


def committed_schedule(sport: str, season: int, as_of: datetime) -> pd.DataFrame:
    """The schedule the daily run last wrote, as load_schedule returns it,
    with every game starting at or after `as_of` not yet played."""
    doc = json.loads((ROOT / 'results' / sport / f'schedule_{season}.json').read_text(encoding='utf-8'))
    df = pd.DataFrame(doc['games'])
    df['start_utc'] = pd.to_datetime(df['start_utc'], utc=True)
    later = df['start_utc'] >= pd.Timestamp(as_of)
    df.loc[later, 'status'] = 'scheduled'
    df.loc[later, ['home_score', 'away_score']] = None
    final = df['status'] == 'final'
    df['home_win'] = pd.NA
    df.loc[final, 'home_win'] = (df.loc[final, 'home_score'] > df.loc[final, 'away_score']).astype(int)
    df['season'] = season
    return df


def temp_paths(tmp_path: Path, sport: str) -> SimpleNamespace:
    real = ROOT
    return SimpleNamespace(data=tmp_path / 'data', predictions=tmp_path / 'predictions',
                           results=tmp_path / 'results', experiments=real / 'experiments' / sport)


def run_twice(daily, now, get, capsys):
    assert daily.main(now=now, get=get) == 0
    first = capsys.readouterr().out
    assert daily.main(now=now, get=get) == 0
    second = capsys.readouterr().out
    return first, second


@pytest.mark.slow
def test_the_nhl_daily_run_end_to_end(tmp_path, monkeypatch, capsys):
    from src.sports.nhl import daily, goalies, history, injuries, market

    season = 2026
    now = datetime(2026, 10, 10, 16, 30, tzinfo=UTC)
    sched = committed_schedule('nhl', season, now)
    share_nhl_features(monkeypatch)
    monkeypatch.setattr(daily, 'PATHS', temp_paths(tmp_path, 'nhl'))
    monkeypatch.setattr(daily.nhl_schedule, 'load_schedule', lambda s, *a, **k: sched.copy())
    have = history.HISTORY / f'boxscores_{season}.csv'
    stored = pd.read_csv(have, dtype={'game_id': str}) if have.exists() else None
    monkeypatch.setattr(daily, 'refresh_season', lambda s, sc, *a, **k: stored.copy())

    def get(url: str) -> bytes:
        if url == market.SOURCE:
            return b'{"games": []}'
        if url.startswith(goalies.SOURCE):
            return b'<html></html>'
        if 'roster' in url:
            return b'{"goalies": []}'
        if url == injuries.source(season):
            raise OSError('no injury report in this test')
        raise AssertionError(f'unexpected fetch: {url}')

    first, second = run_twice(daily, now, get, capsys)
    picks = sorted((tmp_path / 'predictions' / str(season)).glob('*.json'))
    locked = [line for line in first.splitlines() if line.startswith('saved ')]
    assert picks and len(picks) == len(locked)
    for p in picks:
        rec = json.loads(p.read_text(encoding='utf-8'))
        assert rec['pick_model'] == 'model_a' and rec['model_b'] is None and rec['market'] is None
        assert rec['pick'] in (rec['home'], rec['away']) and rec['saved_utc'] == '2026-10-10T16:30:00Z'
        assert rec['start_utc'] > rec['saved_utc']
    assert not [ln for ln in second.splitlines() if ln.startswith('saved ')]
    assert second.count('already saved ') == len(picks)
    graded = json.loads((tmp_path / 'results' / f'graded_{season}.json').read_text(encoding='utf-8'))
    assert {r['game_id'] for r in graded} == {p.stem for p in picks}
    # Stage 85 item 1: the file says which registered looks were made and when the next is.
    drift_file = json.loads((tmp_path / 'results' / f'drift_{season}.json').read_text(encoding='utf-8'))
    assert drift_file['looks'] == [] and drift_file['next_look'] == 100, drift_file
    assert (tmp_path / 'results' / f'standings_{season}.json').exists()


@pytest.mark.slow
def test_the_nba_daily_run_end_to_end(tmp_path, monkeypatch, capsys):
    from src.sports.nba import daily, history

    share_nba_tables(monkeypatch)
    season = 2026
    now = datetime(2026, 10, 20, 16, 5, tzinfo=UTC)
    sched = committed_schedule('nba', season, now)
    monkeypatch.setattr(daily, 'PATHS', temp_paths(tmp_path, 'nba'))
    monkeypatch.setattr(daily.nba_schedule, 'load_schedule', lambda s, *a, **k: sched.copy())
    real_refresh = daily.refresh_season
    monkeypatch.setattr(daily, 'refresh_season',
                        lambda s, sc, *a, **k: real_refresh(s, sc, folder=history.HISTORY, get=k.get('get')))

    def get(url: str) -> bytes:
        raise OSError(f'offline: {url}')

    first, second = run_twice(daily, now, get, capsys)
    picks = sorted((tmp_path / 'predictions' / str(season)).glob('*.json'))
    assert picks, first[-2000:]
    for p in picks:
        rec = json.loads(p.read_text(encoding='utf-8'))
        assert rec['market_source'] is None and rec['pick'] in (rec['home'], rec['away'])
        assert rec['start_utc'] > rec['saved_utc']
    assert not [ln for ln in second.splitlines() if ln.startswith('saved ')]
    assert (tmp_path / 'results' / f'graded_{season}.json').exists()
    # Stage 85 item 1: the file says which registered looks were made and when the next is.
    drift_file = json.loads((tmp_path / 'results' / f'drift_{season}.json').read_text(encoding='utf-8'))
    assert drift_file['looks'] == [] and drift_file['next_look'] == 100, drift_file
    # Stage 104 item 3: the ratings the Power Ratings and Teams pages read, written every run.
    rated = json.loads((tmp_path / 'results' / f'ratings_{season}.json').read_text(encoding='utf-8'))
    assert rated['as_of'] == '2026-10-20' and len(rated['teams']) == len(set(sched['home']) | set(sched['away']))
    points = [t['point'] for t in rated['teams']]
    assert points == sorted(points, reverse=True) and len(set(points)) > 1, 'real ratings, best first'
    # Stage 104 item 4: the standings odds, in a run that saved picks.
    odds = json.loads((tmp_path / 'results' / f'standings_{season}.json').read_text(encoding='utf-8'))
    assert len(odds['teams']) == 30 and odds['simulations'] == 10000
    for conf in ('East', 'West'):
        clubs = [t for t in odds['teams'] if t['conference'] == conf]
        assert abs(sum(t['playoff_pct'] for t in clubs) - 8) < 1e-6, 'eight playoff places a conference'


def test_a_game_after_the_moment_reads_as_not_yet_played():
    """The schedule is read as it stood: a game that has since gone final
    reads as scheduled with no score, and one before the moment is left
    alone."""
    moment = datetime(2026, 10, 10, 16, 30, tzinfo=UTC)
    now_file = committed_schedule('nhl', 2026, datetime(2100, 1, 1, tzinfo=UTC))
    rewound = committed_schedule('nhl', 2026, moment)
    later = rewound['start_utc'] >= pd.Timestamp(moment)
    assert later.any() and (~later).any()
    assert (rewound.loc[later, 'status'] == 'scheduled').all()
    assert rewound.loc[later, 'home_win'].isna().all() and rewound.loc[later, 'home_score'].isna().all()
    pd.testing.assert_frame_equal(rewound.loc[~later], now_file.loc[~later])


def test_the_nba_page_inputs_write_every_field_plainly(tmp_path):
    """src/sports/nba/page_inputs.py had no test at all (E30)."""
    from src.sports.nba import page_inputs
    sched = pd.DataFrame([
        {'game_id': '1', 'slate': '2026-10-20', 'start_utc': pd.Timestamp('2026-10-20T19:00:00Z'), 'home': 'DET',
         'away': 'BOS', 'status': 'final', 'game_type': 'regular', 'home_score': np.int64(101),
         'away_score': np.int64(99), 'neutral_site': False, 'time_valid': np.bool_(True), 'extra': 'dropped'},
        {'game_id': '2', 'slate': '2026-10-20', 'start_utc': pd.Timestamp('2026-10-20T23:30:00Z'), 'home': 'NY',
         'away': 'PHI', 'status': 'scheduled', 'game_type': 'regular', 'home_score': np.nan,
         'away_score': pd.NA, 'neutral_site': None},
    ])
    doc = page_inputs.schedule_json(sched, '2026-10-20T16:00:00Z')
    assert doc['as_of'] == '2026-10-20T16:00:00Z'
    assert doc['games'][0] == {'game_id': '1', 'slate': '2026-10-20', 'start_utc': '2026-10-20T19:00:00Z',
                               'home': 'DET', 'away': 'BOS', 'status': 'final', 'game_type': 'regular',
                               'home_score': 101, 'away_score': 99, 'neutral_site': False, 'time_valid': True}
    assert doc['games'][1]['home_score'] is None and doc['games'][1]['away_score'] is None
    assert doc['games'][1]['time_valid'] is None   # a row with no flag writes null, not a missing key
    out = page_inputs.write(tmp_path / 'a' / 'schedule_2026.json', doc)
    assert json.loads(out.read_text(encoding='utf-8')) == doc and not out.with_suffix('.tmp').exists()


def test_the_nba_ratings_file_lists_every_club_best_first():
    """Stage 104 item 3: a club with no rated games yet is listed at zero, not left out."""
    from src.sports.nba import page_inputs, ratings
    rated = ratings.DayRatings({'BOS': 3.21234, 'NY': -1.5, 'DET': 3.21234}, {'BOS': 4.0, 'NY': -2.0, 'DET': 2.5})
    doc = page_inputs.ratings_json(rated, ['NY', 'BOS', 'DET', 'UTA', 'BOS'], '2026-11-11')
    assert doc == {'as_of': '2026-11-11', 'teams': [
        {'team': 'BOS', 'point': 3.2123, 'efficiency': 4.0}, {'team': 'DET', 'point': 3.2123, 'efficiency': 2.5},
        {'team': 'UTA', 'point': 0.0, 'efficiency': 0.0}, {'team': 'NY', 'point': -1.5, 'efficiency': -2.0}]}
