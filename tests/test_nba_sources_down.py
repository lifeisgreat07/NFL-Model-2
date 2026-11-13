"""No optional source stops the NBA's picks being saved (Stage 96 item 52).

The NHL's three whole runs (tests/test_nhl_sources_down.py) hold that an odds
feed or a roster that cannot be read costs a pick its price or its goalie,
never the pick. The NBA's run reads three optional sources: the injury
report, ESPN's odds for each locking game, and Kalshi when ESPN has no
price. tests/test_daily_end_to_end.py runs it with every read failing at
once; here each source fails the way the 2026-10-10 odds feed did (a read
that times out), and the pick says which source it went without.

Each whole run is a whole daily run, so they are two and marked slow; the
ways a read can fail are checked against the three readers alone.

Run with: pytest tests/test_nba_sources_down.py -v
"""
from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from tests.shared_tables import share_nba_tables
from tests.test_daily_end_to_end import committed_schedule, temp_paths

SEASON = 2026
NOW = datetime(2026, 10, 21, 21, 30, tzinfo=UTC)
FAILURES = [TimeoutError('The read operation timed out'), ConnectionResetError('reset'), b'<html>Bad gateway</html>']
IDS = ['timeout', 'reset', 'not-json']


def reader(answer):
    def get(url):
        if isinstance(answer, Exception):
            raise answer
        return answer
    return get


@pytest.mark.parametrize('answer', FAILURES, ids=IDS)
def test_each_price_reader_answers_nothing_for_a_source_it_cannot_read(answer, capsys):
    from src.sports.nba import daily
    assert daily.read_espn_odds('401909834', reader(answer)) is None
    assert daily.read_kalshi(reader(answer)) is None
    out = capsys.readouterr().out
    assert 'DEGRADED: ESPN odds for 401909834: not read' in out and 'DEGRADED: Kalshi: not read' in out


@pytest.mark.parametrize('answer', FAILURES, ids=IDS)
def test_the_injury_reader_answers_nothing_for_a_report_it_cannot_read(answer, capsys):
    from src.sports.nba import daily
    assert daily.read_injuries(reader(answer), {'BOS', 'NY'}) is None
    assert 'DEGRADED: injuries: not read, picks made without availability' in capsys.readouterr().out


def kalshi_feed(sched):
    """A tight Kalshi market for every scheduled game, in the feed's own shape:
    one market a side under the event KXNBAGAME-<yyMONdd><away><home>."""
    markets = []
    for g in sched.to_dict('records'):
        day = datetime.strptime(str(g['slate']), '%Y-%m-%d').strftime('%y%b%d').upper()
        event = f"KXNBAGAME-{day}{g['away']}{g['home']}"
        for code, bid in ((g['home'], 0.55), (g['away'], 0.43)):
            markets.append({'event_ticker': event, 'ticker': f'{event}-{code}',
                            'yes_bid_dollars': f'{bid:.4f}', 'yes_ask_dollars': f'{bid + 0.02:.4f}'})
    return json.dumps({'markets': markets}).encode('utf-8')


def drive(tmp_path, monkeypatch, capsys, kalshi_up):
    """Run the NBA's daily run once with ESPN's odds and the injury report
    timing out; Kalshi answers or times out. Return (stdout, saved picks)."""
    from src.sports.nba import daily, history, injuries, market

    share_nba_tables(monkeypatch)
    sched = committed_schedule('nba', SEASON, NOW)
    monkeypatch.setattr(daily, 'PATHS', temp_paths(tmp_path, 'nba'))
    monkeypatch.setattr(daily.nba_schedule, 'load_schedule', lambda s, *a, **k: sched.copy())
    real_refresh = daily.refresh_season
    monkeypatch.setattr(daily, 'refresh_season',
                        lambda s, sc, *a, **k: real_refresh(s, sc, folder=history.HISTORY, get=k.get('get')))
    feed = kalshi_feed(sched)

    def get(url: str) -> bytes:
        if url == market.KALSHI and kalshi_up:
            return feed
        if url in (market.KALSHI, injuries.SOURCE) or url.startswith(market.ESPN_ODDS.split('{')[0]):
            raise TimeoutError('The read operation timed out')
        raise OSError(f'offline: {url}')

    assert daily.main(now=NOW, get=get) == 0
    out = capsys.readouterr().out
    folder = tmp_path / 'predictions' / str(SEASON)
    picks = [json.loads(p.read_text(encoding='utf-8')) for p in sorted(folder.glob('*.json'))]
    locked = [ln for ln in out.splitlines() if ln.startswith('saved ')]
    assert len(picks) > 1 and len(picks) == len(locked), 'every locked game gets its pick'
    assert 'DEGRADED: injuries: not read, picks made without availability' in out
    for rec in picks:
        assert f"DEGRADED: ESPN odds for {rec['game_id']}: not read" in out
        assert rec['availability']['read'] is False
    return out, picks


@pytest.mark.slow
def test_every_price_source_timing_out_still_saves_every_pick(tmp_path, monkeypatch, capsys):
    out, picks = drive(tmp_path, monkeypatch, capsys, kalshi_up=False)
    assert out.count('DEGRADED: Kalshi: not read') == 1, 'Kalshi is read once a run, not once a game'
    for rec in picks:
        assert rec['market_source'] is None and rec['model_b'] is None and rec['pick_model'] == 'model_a'
        assert rec['market']['why'] == 'ESPN odds not read; Kalshi not read'


@pytest.mark.slow
def test_espn_timing_out_falls_back_to_kalshi_for_every_pick(tmp_path, monkeypatch, capsys):
    out, picks = drive(tmp_path, monkeypatch, capsys, kalshi_up=True)
    assert 'DEGRADED: Kalshi' not in out
    for rec in picks:
        assert rec['market_source'] == 'kalshi' and rec['market']['home_prob'] == round(0.56 / (0.56 + 0.44), 4)
        assert rec['pick_model'] == 'model_b' and rec['model_b'] is not None
