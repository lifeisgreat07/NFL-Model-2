"""The NBA's nightly canary (Stage 65): each source judged on its own, a
failure named by source, and a dependent check skipped, not failed twice.

Payloads are synthetic, shaped like the reads saved on 2026-10-09.

Run with: pytest tests/test_nba_canary.py -v
"""
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from src.sports.nba import canary

ROOT = Path(__file__).resolve().parents[1]
REG = json.loads((ROOT / 'experiments/nba/stage65/registry.json').read_text(encoding='utf-8'))
NOW = datetime(2026, 10, 21, 6, 50, tzinfo=UTC)


def sched(*rows):
    df = pd.DataFrame([{'game_id': g, 'season': 2026, 'slate': '2026-10-21', 'home': h, 'away': a,
                        'status': st, 'start_utc': pd.Timestamp(t, tz='UTC')} for g, h, a, st, t in rows])
    return df


def state(schedule=None, pages=None):
    pages = pages or {}

    def get(url):
        for key, body in pages.items():
            if key in url:
                if isinstance(body, Exception):
                    raise body
                return json.dumps(body).encode()
        raise OSError(f'no fixture for {url}')
    return {'now': NOW, 'get': get, 'schedule': schedule}


ODDS_OK = {'items': [{'provider': {'name': 'DraftKings'}, 'homeTeamOdds': {'moneyLine': -130},
                      'awayTeamOdds': {'moneyLine': 110}}]}
INJ_OK = {'injuries': [{'injuries': [{'status': 'Out', 'athlete': {
    'displayName': 'A', 'links': [{'href': 'https://www.espn.com/nba/player/_/id/11/a'}],
    'team': {'abbreviation': 'ORL'}}}]}]}


def test_it_checks_every_source_the_registration_names():
    names = [n for n, _ in canary.CHECKS]
    assert names == ['ESPN scoreboard', 'ESPN box score', 'ESPN odds', 'ESPN injuries', 'Kalshi']
    for word in ('scoreboard', 'box score', 'odds', 'injury report', 'Kalshi'):
        assert word in REG['canary']
    assert "'NBA: nightly canary failing'" in REG['canary']


def test_odds_pass_when_one_upcoming_game_is_priced():
    s = sched(('1', 'ORL', 'ATL', 'scheduled', '2026-10-21 23:00'))
    assert canary.check_odds(state(s, {'events/1/': ODDS_OK})) == '1 of the next 1 games priced'


def test_odds_fail_when_none_of_the_upcoming_games_is_priced():
    s = sched(('1', 'ORL', 'ATL', 'scheduled', '2026-10-21 23:00'), ('2', 'MIA', 'MIN', 'scheduled', '2026-10-21 23:30'))
    try:
        canary.check_odds(state(s, {'events/': {'items': []}}))
    except ValueError as exc:
        assert 'ESPN priced none of the next 2 games' in str(exc)
    else:
        raise AssertionError('an unpriced slate passed')


def test_no_game_in_the_next_week_is_not_an_error():
    s = sched(('1', 'ORL', 'ATL', 'final', '2026-10-20 23:00'))
    assert 'not an error' in canary.check_odds(state(s))


def test_injuries_are_parsed_strictly():
    s = sched(('1', 'ORL', 'ATL', 'scheduled', '2026-10-21 23:00'))
    assert canary.check_injuries(state(s, {'injuries': INJ_OK})) == '1 players listed, 1 Out'


def test_kalshi_with_no_quoted_game_is_noted_not_failed():
    assert canary.check_kalshi(state(pages={'kalshi': {'markets': []}})).startswith('0 games quoted')


def test_kalshi_without_a_market_list_fails():
    try:
        canary.check_kalshi(state(pages={'kalshi': {'error': 'x'}}))
    except ValueError as exc:
        assert 'no market list' in str(exc)
    else:
        raise AssertionError('a broken Kalshi feed passed')


def test_a_failure_is_named_by_source_and_the_dependent_checks_are_skipped(monkeypatch):
    def boom(st):
        raise OSError('HTTP Error 403: Forbidden')
    checks = [('ESPN scoreboard', boom), ('ESPN odds', canary.check_odds), ('Kalshi', lambda st: 'fine')]
    failed, notes = canary.run(NOW, get=lambda u: b'{}', checks=checks)
    assert failed == ['ESPN scoreboard']
    assert notes[1] == 'ESPN odds: not checked, the schedule could not be read tonight'
    assert notes[2] == 'Kalshi: fine'


def test_main_writes_the_failing_sources_one_per_line(tmp_path, monkeypatch):
    monkeypatch.setattr(canary, 'CHECKS', [('ESPN odds', lambda st: (_ for _ in ()).throw(ValueError('x'))),
                                           ('Kalshi', lambda st: (_ for _ in ()).throw(OSError('y')))])
    report, failed = tmp_path / 'r.md', tmp_path / 'f.txt'
    code = canary.main(['--report', str(report), '--failed', str(failed)], now=NOW, get=lambda u: b'{}')
    assert code == 1
    assert failed.read_text(encoding='utf-8') == 'ESPN odds\nKalshi\n'
    assert report.read_text(encoding='utf-8').startswith('# NBA nightly canary')


def test_a_clean_night_exits_zero_and_names_no_source(tmp_path, monkeypatch):
    monkeypatch.setattr(canary, 'CHECKS', [('Kalshi', lambda st: 'ok')])
    failed = tmp_path / 'f.txt'
    assert canary.main(['--failed', str(failed)], now=NOW, get=lambda u: b'{}') == 0
    assert failed.read_text(encoding='utf-8') == ''
