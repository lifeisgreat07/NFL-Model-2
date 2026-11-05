"""Stage 92 item 7 (audit 7, R4 and R6): a silent loss of prices or projected
starters prints DEGRADED, which the daily workflows raise an issue on.

Run with: pytest tests/test_priced.py -v
"""
from pathlib import Path

import pytest

from src.core import priced
from tests.test_nhl_sources_down import drive

ROOT = Path(__file__).resolve().parents[1]


def test_no_price_for_any_locking_game_is_degraded():
    line = priced.unpriced_line(['1', '2', '3'], [])
    assert line.startswith('DEGRADED: odds feed: priced none of the 3 games locking')


def test_one_priced_game_is_enough_and_nothing_locking_says_nothing():
    assert priced.unpriced_line(['1', '2'], ['2']) is None
    assert priced.unpriced_line([], []) is None
    assert priced.unpriced_line([1, 2], ['1']) is None, 'game ids are compared as text'


@pytest.mark.slow
def test_an_empty_or_renamed_nhl_odds_feed_says_so(tmp_path, monkeypatch, capsys):
    """Audit 7's injection: the feed answers, with no games or under a renamed key."""
    out, picks = drive(tmp_path, monkeypatch, capsys, market_answer=b'{"matchups": [{"id": 1}]}')
    assert f'DEGRADED: odds feed: priced none of the {len(picks)} games locking' in out
    assert all(p['market'] is None for p in picks)


def test_both_runs_print_it_and_kalshi_and_goalies_say_degraded():
    nhl = (ROOT / 'src' / 'sports' / 'nhl' / 'daily.py').read_text(encoding='utf-8')
    nba = (ROOT / 'src' / 'sports' / 'nba' / 'daily.py').read_text(encoding='utf-8')
    assert "unpriced = priced.unpriced_line(locking['game_id'], (r['game_id'] for r in lines))" in nhl
    assert "print(f\"{'DEGRADED: ' if day in locking_days else ''}goalies for {day}: {exc}\")" in nhl
    assert 'unpriced = priced.unpriced_line(locking' in nba and "print(f'DEGRADED: Kalshi: not read: {exc}')" in nba
