"""Every step the canaries name is executed here on payloads in the sources'
shapes (Stage 92 item 9, audit 7 T7: a trace over the suite found five of
the NHL's six steps and three of the NBA's functions run by no test, so a
step could break and only the real night would say so).

The NHL's night runs all six steps end to end through one fake `get` that
serves each source's URL; the NBA's scoreboard, last-final and box-score reads
run on the same synthetic shapes as their own modules' tests. The payload
builders are those tests' own, so a change of shape there reaches here.

Run with: pytest tests/test_canary_steps.py -v
"""
import json
from datetime import UTC, datetime

import pandas as pd
import pytest

from src.sports.nba import canary as nba_canary
from src.sports.nba import history as nba_history
from src.sports.nba import schedule as nba_schedule
from src.sports.nhl import canary, goalies, history, market, roster
from src.sports.nhl import schedule as nhl_schedule
from tests import test_nba_history as nba_h
from tests import test_nba_schedule as nba_s
from tests import test_nhl_canary as nhl_c
from tests import test_nhl_inputs as nhl_i
from tests import test_nhl_schedule as nhl_s
from tests.test_nhl_daily import ROSTER

NOW = datetime(2026, 10, 5, 18, 0, tzinfo=UTC)
TONIGHT = nhl_s.game(gid=2026020040, home='TBL', away='PHI', start='2026-10-05T23:00:00Z', day='2026-10-05')
EARLIER = nhl_s.final(gid=2026020001, home='TBL', away='PHI', start='2026-10-03T23:00:00Z', day='2026-10-03')


def nhl_get(odds=None, games=(TONIGHT, EARLIER), projected=(nhl_i.fo_game(),)):
    """One fake internet for the NHL's night: the URL picks the payload."""
    odds = nhl_i.feed(nhl_i.odds_game()) if odds is None else odds
    by_club = {club: [g for g in games if club in (g['homeTeam']['abbrev'], g['awayTeam']['abbrev'])]
               for club in ('TBL', 'PHI')}
    pages = {market.SOURCE: odds, roster.ROSTER.format(club='TOR'): ROSTER}
    for gid in (2026020001,):
        pages[history.BOX.format(gid=gid)] = nhl_c.box(gid)

    def get(url):
        if url == f'{goalies.SOURCE}/2026-10-05':
            return nhl_i.page(*projected).encode()
        if url in pages:
            return json.dumps(pages[url]).encode()
        for club in nhl_schedule.CLUBS:
            if url == nhl_schedule.CLUB_SEASON.format(club=club, season_id=nhl_schedule.season_id(2026)):
                return json.dumps({'games': by_club.get(club, [])}).encode()
        raise OSError(f'no fixture for {url}')
    return get


def test_the_nhl_night_runs_every_step_and_each_reads_its_source():
    errors, notes = canary.run(NOW, nhl_get())
    assert errors == []
    assert [n.split(':')[0] for n in notes] == [name for name, _ in canary.STEPS]
    by = {n.split(':')[0]: n for n in notes}
    assert by['schedule'] == 'schedule: 2 games in 2026'
    assert by['lock'] == 'lock: today: lock 0, hold 1, started 0'
    assert by['box score'].startswith('box score: game 2026020001')
    assert by['market'] == 'market: 1 games priced'
    assert by['goalies'] == 'goalies: 1 games with projected goalies'
    assert by['roster'] == 'roster: 2 goalies on a roster'


@pytest.mark.parametrize('odds', [nhl_i.feed(), {'bettingPartner': {'name': 'DraftKings'}, 'gameList': [nhl_i.odds_game()]}],
                         ids=['empty-games-list', 'renamed-key'])
def test_an_odds_feed_that_prices_nothing_fails_the_night_with_a_game_due(odds):
    errors, notes = canary.run(NOW, nhl_get(odds=odds))
    assert len(errors) == 1 and errors[0].startswith('market raised ValueError: the odds feed priced no game, with 1 due')


def test_an_odds_feed_with_nothing_to_price_passes():
    """No game due in the next day and a half (an off-day, the break): nothing to price is not a failure."""
    errors, notes = canary.run(NOW, nhl_get(odds=nhl_i.feed(), games=(EARLIER,), projected=()))
    assert errors == [] and 'market: 0 games priced' in notes


def nba_board_get(events, days=('2026-10-21T07:00Z',)):
    def get(url):
        if url.startswith(nba_schedule.SCOREBOARD.split('?')[0]):
            return json.dumps(nba_s.board(events, days)).encode()
        if url == nba_history.SUMMARY.format(gid='401800002'):
            return json.dumps(nba_h.RAW).encode()
        raise OSError(f'no fixture for {url}')
    return get


NBA_NOW = datetime(2026, 10, 22, 6, 50, tzinfo=UTC)


def test_the_nba_scoreboard_last_final_and_box_score_reads_run():
    get = nba_board_get([nba_s.event(gid='401800001', start='2026-10-22T23:30Z'),
                         nba_s.final(gid='401800000', home='NY', away='MIA', scores=(99, 90),
                                     start='2026-10-21T00:00Z'),
                         nba_s.final(gid='401800002', home='BOS', away='ATL', scores=(116, 117),
                                     start='2026-10-21T23:30Z')])
    state = {'now': NBA_NOW, 'get': get}
    assert nba_canary.check_scoreboard(state) == '3 games in 2026'
    g = nba_canary._last_final(state)
    assert g['game_id'] == '401800002'
    note = nba_canary.check_box_score(state)
    assert note.startswith('game 401800002 (') and 'possessions' in note and note.endswith('3 players')


def test_before_a_final_this_season_the_box_score_check_reads_last_seasons_last_game():
    state = {'now': NBA_NOW, 'get': None,
             'schedule': pd.DataFrame([{'game_id': '401800001', 'season': 2026, 'status': 'scheduled'}])}
    g = nba_canary._last_final(state)
    past = pd.read_csv(nba_history.HISTORY / 'games_2025.csv', dtype={'game_id': str})
    assert g['game_id'] == past.iloc[-1]['game_id'] and g['season'] == 2025
