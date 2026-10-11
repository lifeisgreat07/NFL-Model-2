"""No optional source stops the NHL's picks being saved (2026-10-11).

On 2026-10-10 the 21:00 UTC daily run read the league's odds feed, the
read timed out three times, and the exception ended the run before it saved
anything. The next run came after puck drop, so nine games started with no
pick (issues #423 and #424), and a pick can never be made after its game
starts. The NBA's run already read its prices this way; the NHL's did not.

The run is driven whole, as `tests/test_daily_end_to_end.py` drives it, over
the committed history and schedule, with each outside source answered by a
stub. Here the odds feed times out, or answers with something that is not
JSON, or every club's roster cannot be read, and every locked game must
still get its pick, saying why it has no price or which goalie it fell back
to.

Run with: pytest tests/test_nhl_sources_down.py -v
"""
from __future__ import annotations

import json
from datetime import UTC, datetime

import pandas as pd
import pytest

from tests.test_daily_end_to_end import committed_schedule, temp_paths

SEASON = 2026
NOW = datetime(2026, 10, 10, 16, 30, tzinfo=UTC)


def drive(tmp_path, monkeypatch, capsys, market_answer=None, roster_down=False, projected=False):
    """Run the NHL's daily run once; return (stdout, saved picks)."""
    from src.sports.nhl import daily, goalies, history, injuries, market

    sched = committed_schedule('nhl', SEASON, NOW)
    monkeypatch.setattr(daily, 'PATHS', temp_paths(tmp_path, 'nhl'))
    monkeypatch.setattr(daily.nhl_schedule, 'load_schedule', lambda s, *a, **k: sched.copy())
    have = history.HISTORY / f'boxscores_{SEASON}.csv'
    stored = pd.read_csv(have, dtype={'game_id': str}) if have.exists() else None
    monkeypatch.setattr(daily, 'refresh_season', lambda s, sc, *a, **k: stored.copy())
    if projected:
        monkeypatch.setattr(daily.goalies, 'parse_faceoff', lambda text, now: [])
        monkeypatch.setattr(daily.goalies, 'attach_games', lambda rows, games: [
            {'game_id': str(g['game_id']), 'home_goalie': 'Home Keeper', 'home_status': 'Confirmed',
             'away_goalie': 'Away Keeper', 'away_status': 'Likely'} for g in games])
        monkeypatch.setattr(daily.goalies, 'record', lambda rows, path: 0)

    def get(url: str) -> bytes:
        if url == market.SOURCE:
            if isinstance(market_answer, Exception):
                raise market_answer
            return market_answer if market_answer is not None else b'{"games": []}'
        if url.startswith(goalies.SOURCE):
            return b'<html></html>'
        if 'roster' in url:
            if roster_down:
                raise TimeoutError('The read operation timed out')
            return b'{"goalies": []}'
        if url == injuries.source(SEASON):
            raise OSError('no injury report in this test')
        raise AssertionError(f'unexpected fetch: {url}')

    assert daily.main(now=NOW, get=get) == 0
    out = capsys.readouterr().out
    folder = tmp_path / 'predictions' / str(SEASON)
    picks = [json.loads(p.read_text(encoding='utf-8')) for p in sorted(folder.glob('*.json'))]
    locked = [ln for ln in out.splitlines() if ln.startswith('saved ')]
    assert picks and len(picks) == len(locked), 'every locked game gets its pick'
    return out, picks


@pytest.mark.parametrize('answer', [TimeoutError('The read operation timed out'), b'<html>Bad gateway</html>'],
                         ids=['timed-out', 'not-json'])
def test_an_odds_feed_that_cannot_be_read_still_saves_every_pick(tmp_path, monkeypatch, capsys, answer):
    out, picks = drive(tmp_path, monkeypatch, capsys, market_answer=answer)
    assert 'market: odds feed not read, every pick made without a price' in out
    for rec in picks:
        assert rec['market'] is None and rec['model_b'] is None and rec['pick_model'] == 'model_a'


def test_a_roster_that_cannot_be_read_still_saves_every_pick(tmp_path, monkeypatch, capsys):
    out, picks = drive(tmp_path, monkeypatch, capsys, roster_down=True)
    assert 'not read, its last starter is used' in out
    for rec in picks:
        for side in ('home', 'away'):
            assert rec['goalies'][side]['basis'] == 'last_start'


def test_a_projected_goalie_with_no_roster_says_the_roster_was_not_read(tmp_path, monkeypatch, capsys):
    """The reason on the pick is the true one: not 'not a goalie on the
    current roster', which would accuse a goalie of not being on a roster
    nobody read."""
    _, picks = drive(tmp_path, monkeypatch, capsys, roster_down=True, projected=True)
    for rec in picks:
        assert rec['goalies']['home']['note'] == 'Home Keeper is projected, but the roster was not read'
        assert rec['goalies']['away']['note'] == 'Away Keeper is projected, but the roster was not read'


def test_a_projected_goalie_on_a_read_roster_keeps_the_roster_reason(tmp_path, monkeypatch, capsys):
    """With the rosters read (and empty), the old reason stands."""
    _, picks = drive(tmp_path, monkeypatch, capsys, projected=True)
    for rec in picks:
        assert rec['goalies']['home']['note'] == 'Home Keeper is not a goalie on the current roster'
