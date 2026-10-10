"""Team codes from the NHL's and ESPN's feeds never reach a page as markup (Stage 68 item 8).

The NHL and NBA pages draw `g.home`/`g.away` into HTML in many places,
unescaped. The codes come from the league's feed (NHL) and ESPN's (NBA).
The schedule build now refuses a code that is not two to four capital
letters, and each page checks again before drawing one.

Run with: pytest tests/test_team_codes.py -v
"""
from pathlib import Path

import pytest

from src.sports.nba import schedule as nba_schedule
from src.sports.nhl import schedule as nhl_schedule

ROOT = Path(__file__).resolve().parents[1]
BAD = ('<img src=x onerror=alert(1)>', 'bos', 'B', 'BOSTON')


def nhl_game(home, away='BOS'):
    return {'id': 1, 'season': 20262027, 'gameType': 2, 'gameDate': '2026-10-10',
            'startTimeUTC': '2026-10-10T23:00:00Z', 'gameState': 'FUT', 'gameScheduleState': 'OK',
            'homeTeam': {'abbrev': home}, 'awayTeam': {'abbrev': away}}


def nba_game(home, away='BOS'):
    return {'id': '1', 'date': '2026-10-20T23:00Z', 'competitions': [{
        'type': {'abbreviation': 'STD'}, 'status': {'type': {'name': 'STATUS_SCHEDULED'}},
        'competitors': [{'homeAway': 'home', 'team': {'abbreviation': home}},
                        {'homeAway': 'away', 'team': {'abbreviation': away}}]}]}


@pytest.mark.parametrize('code', BAD)
def test_the_nhl_schedule_refuses_a_code_that_is_not_one(code):
    assert any('team code' in p for p in nhl_schedule.raw_problems(nhl_game(code)))


@pytest.mark.parametrize('code', BAD)
def test_the_nba_schedule_refuses_a_code_that_is_not_one(code):
    assert any('team code' in p for p in nba_schedule.raw_problems(nba_game(code)))


@pytest.mark.parametrize('code', ('NY', 'BOS', 'UTAH'))
def test_real_codes_pass(code):
    assert not any('team code' in p for p in nhl_schedule.raw_problems(nhl_game(code, 'TOR')))
    assert not any('team code' in p for p in nba_schedule.raw_problems(nba_game(code, 'TOR')))


@pytest.mark.parametrize('rel, data', [('src/sports/nhl/pages/nhl.js', 'DATA'), ('src/sports/nba/pages/nba.js', 'BD')])
def test_each_page_cleans_the_codes_before_it_draws_any(rel, data):
    js = (ROOT / rel).read_text(encoding='utf-8')
    assert 'const TEAM_CODE = /^[A-Z]{2,4}$/;' in js
    clean = f'{data}.games.forEach(g => {{ g.home = cleanCode(g.home); g.away = cleanCode(g.away); }});'
    assert clean in js
    assert js.index(clean) < js.index(f'{data}.games.forEach(g => {{ (WEEKS[mondayOf(g.day)]')
    assert "function cleanCode(c){ return TEAM_CODE.test(String(c)) ? c : '?'; }" in js
