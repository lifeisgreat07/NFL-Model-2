"""Stage 85 item 5: this season's market prices reach live Model B's training
rows, from the lines the daily runs recorded: each game's last read before it
started.

Run with: pytest tests/test_season_prices.py -v
"""
import json
from pathlib import Path

import pytest

from src.core import season_prices as sp

ROOT = Path(__file__).resolve().parents[1]


def line(gid, read, prob, start='2026-11-01T23:00:00Z'):
    return {'game_id': gid, 'start_utc': start, 'read_utc': read, 'home_prob': prob}


def test_the_last_read_before_the_start_is_the_price():
    lines = [line('1', '2026-11-01T14:00:00Z', 0.55), line('1', '2026-11-01T21:00:00Z', 0.58),
             line('2', '2026-11-01T21:00:00Z', 0.40)]
    assert sp.pre_game(lines) == {'1': 0.58, '2': 0.40}


def test_a_read_at_or_after_the_start_is_never_used():
    lines = [line('1', '2026-11-01T21:00:00Z', 0.58), line('1', '2026-11-01T23:00:00Z', 0.70),
             line('1', '2026-11-01T23:30:00Z', 0.90), line('2', '2026-11-02T00:00:00Z', 0.30)]
    assert sp.pre_game(lines) == {'1': 0.58}, 'game 2 has no pre-game read'


def test_a_line_without_a_price_or_a_time_is_skipped():
    lines = [line('1', '2026-11-01T21:00:00Z', None), {'game_id': '2', 'home_prob': 0.5, 'read_utc': None,
                                                       'start_utc': '2026-11-01T23:00:00Z'}]
    assert sp.pre_game(lines) == {}


def test_no_file_no_prices(tmp_path):
    assert sp.read(tmp_path / 'missing.json') == {}
    (tmp_path / 'l.json').write_text(json.dumps([line(7, '2026-11-01T21:00:00Z', 0.6)]), encoding='utf-8')
    assert sp.read(tmp_path / 'l.json') == {'7': 0.6}, 'game ids are matched as text'


@pytest.mark.parametrize('sport', ['nhl', 'nba'])
def test_the_committed_lines_give_a_price_to_most_saved_picks(sport):
    """A postcondition over committed data: the runs' own record prices the
    games they saved priced picks for, so this is not an empty join."""
    prices = sp.read(ROOT / 'data' / sport / 'lines' / '2026.json')
    picks = [json.loads(p.read_text(encoding='utf-8')) for p in (ROOT / 'predictions' / sport / '2026').glob('*.json')]
    priced = [p for p in picks if p.get('model_b') is not None]
    assert priced and sum(str(p['game_id']) in prices for p in priced) >= 0.9 * len(priced)


@pytest.mark.parametrize('sport', ['nhl', 'nba'])
def test_both_daily_runs_put_the_prices_on_this_seasons_games(sport):
    src = (ROOT / 'src' / 'sports' / sport / 'daily.py').read_text(encoding='utf-8')
    assert "recorded = season_prices.read(PATHS.data / 'lines' / f'{season}.json')" in src
    frame = 'current' if sport == 'nhl' else 'cur_games'
    assert f"{frame} = {frame}.assign(home_prob={frame}['game_id'].astype(str).map(recorded))" in src
    assert 'home_prob=np.nan' not in src
