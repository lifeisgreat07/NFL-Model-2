"""Each day sport's daily run, end to end, with no network (Stage 68 item 15, E29).

`daily.main` had never run whole in a test for either sport: every piece
was tested alone, and the join between them only ran in the workflow. Here
each runs over the committed history and schedule, with every outside
source answered by a stub: no price (so Model A makes the pick), no
projected goalie, no injury report. Everything it writes goes to a
temporary folder. The run must save a pick for each game it locks, grade,
write the drift check and the page inputs, and, run again at the same
moment, save nothing twice.

Run with: pytest tests/test_daily_end_to_end.py -v
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def committed_schedule(sport: str, season: int) -> pd.DataFrame:
    """The schedule the daily run last wrote, as load_schedule returns it."""
    doc = json.loads((ROOT / 'results' / sport / f'schedule_{season}.json').read_text(encoding='utf-8'))
    df = pd.DataFrame(doc['games'])
    df['start_utc'] = pd.to_datetime(df['start_utc'], utc=True)
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


def test_the_nhl_daily_run_end_to_end(tmp_path, monkeypatch, capsys):
    from src.sports.nhl import daily, goalies, history, injuries, market

    season = 2026
    sched = committed_schedule('nhl', season)
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

    now = datetime(2026, 10, 10, 16, 30, tzinfo=UTC)
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
    assert (tmp_path / 'results' / f'drift_{season}.json').exists()
    assert (tmp_path / 'results' / f'standings_{season}.json').exists()


def test_the_nba_daily_run_end_to_end(tmp_path, monkeypatch, capsys):
    from src.sports.nba import daily, history

    season = 2026
    sched = committed_schedule('nba', season)
    monkeypatch.setattr(daily, 'PATHS', temp_paths(tmp_path, 'nba'))
    monkeypatch.setattr(daily.nba_schedule, 'load_schedule', lambda s, *a, **k: sched.copy())
    real_refresh = daily.refresh_season
    monkeypatch.setattr(daily, 'refresh_season',
                        lambda s, sc, *a, **k: real_refresh(s, sc, folder=history.HISTORY, get=k.get('get')))

    def get(url: str) -> bytes:
        raise OSError(f'offline: {url}')

    now = datetime(2026, 10, 20, 16, 5, tzinfo=UTC)
    first, second = run_twice(daily, now, get, capsys)
    picks = sorted((tmp_path / 'predictions' / str(season)).glob('*.json'))
    assert picks, first[-2000:]
    for p in picks:
        rec = json.loads(p.read_text(encoding='utf-8'))
        assert rec['market_source'] is None and rec['pick'] in (rec['home'], rec['away'])
        assert rec['start_utc'] > rec['saved_utc']
    assert not [ln for ln in second.splitlines() if ln.startswith('saved ')]
    assert (tmp_path / 'results' / f'graded_{season}.json').exists()


def test_the_nba_page_inputs_write_every_field_plainly(tmp_path):
    """src/sports/nba/page_inputs.py had no test at all (E30)."""
    from src.sports.nba import page_inputs
    sched = pd.DataFrame([
        {'game_id': '1', 'slate': '2026-10-20', 'start_utc': pd.Timestamp('2026-10-20T19:00:00Z'), 'home': 'DET',
         'away': 'BOS', 'status': 'final', 'game_type': 'regular', 'home_score': np.int64(101),
         'away_score': np.int64(99), 'neutral_site': False, 'extra': 'dropped'},
        {'game_id': '2', 'slate': '2026-10-20', 'start_utc': pd.Timestamp('2026-10-20T23:30:00Z'), 'home': 'NY',
         'away': 'PHI', 'status': 'scheduled', 'game_type': 'regular', 'home_score': np.nan,
         'away_score': pd.NA, 'neutral_site': None},
    ])
    doc = page_inputs.schedule_json(sched, '2026-10-20T16:00:00Z')
    assert doc['as_of'] == '2026-10-20T16:00:00Z'
    assert doc['games'][0] == {'game_id': '1', 'slate': '2026-10-20', 'start_utc': '2026-10-20T19:00:00Z',
                               'home': 'DET', 'away': 'BOS', 'status': 'final', 'game_type': 'regular',
                               'home_score': 101, 'away_score': 99, 'neutral_site': False}
    assert doc['games'][1]['home_score'] is None and doc['games'][1]['away_score'] is None
    out = page_inputs.write(tmp_path / 'a' / 'schedule_2026.json', doc)
    assert json.loads(out.read_text(encoding='utf-8')) == doc and not out.with_suffix('.tmp').exists()