"""The NHL's schedule loader: every game the league lists, in the core's shape,
or a stop that names what it did not recognise.

Stage 55 items 1 and 2. The games here are small synthetic payloads in the
league feed's shape (`club-schedule-season/<club>/<season>`), so no league
content is committed; `docs/nhl-data.md` records what the real feed returned.

Run with: pytest tests/test_nhl_schedule.py -v
"""
import re
from datetime import UTC, datetime

import pandas as pd
import pytest

from src.core.sport import SCHEDULE_COLUMNS, check_schedule
from src.sports.nhl import schedule as nhl

SEASON = 2026


def game(gid=2026020044, home='TOR', away='NSH', state='FUT', sched='OK', game_type=2,
         start='2026-10-06T23:00:00Z', day='2026-10-06', scores=None, period=None, **over):
    g = {'id': gid, 'season': nhl.season_id(SEASON), 'gameType': game_type, 'gameDate': day,
         'startTimeUTC': start, 'gameState': state, 'gameScheduleState': sched,
         'neutralSite': False, 'venue': {'default': 'Arena'},
         'homeTeam': {'abbrev': home}, 'awayTeam': {'abbrev': away}}
    if scores is not None:
        g['homeTeam']['score'], g['awayTeam']['score'] = scores
    if period is not None:
        g['gameOutcome'] = {'lastPeriodType': period}
    g.update(over)
    return g


def final(gid=2026020001, home='TOR', away='MTL', scores=(3, 2), period='REG', state='OFF', **over):
    return game(gid=gid, home=home, away=away, state=state, scores=scores, period=period, **over)


# --- statuses ---------------------------------------------------------------

@pytest.mark.parametrize('state, sched, status', [
    ('FUT', 'OK', 'scheduled'), ('PRE', 'OK', 'scheduled'), ('FUT', 'TBD', 'scheduled'),
    ('LIVE', 'OK', 'in_progress'), ('CRIT', 'OK', 'in_progress'),
    ('FINAL', 'OK', 'final'), ('OFF', 'OK', 'final'),
    ('FUT', 'PPD', 'postponed'), ('FUT', 'SUSP', 'suspended'), ('FUT', 'CNCL', 'cancelled'),
])
def test_each_league_state_maps_to_one_core_status(state, sched, status):
    g = game(state=state, sched=sched)
    if status == 'final':
        g = final(state=state)
    assert nhl.status_of(g).value == status


def test_a_postponed_game_is_postponed_whatever_its_game_state_says():
    """The schedule state wins: a postponed game can still read FUT, and a
    lock must not treat it as a game about to start."""
    df = nhl.to_schedule([game(state='FUT', sched='PPD')], SEASON)
    assert df.loc[0, 'status'] == 'postponed'


# --- outcomes ---------------------------------------------------------------

def test_a_shootout_loss_at_home_is_a_home_loss():
    """The league adds the shootout's deciding goal to the winner's score,
    so 1-2 after a shootout is the away team's win."""
    df = nhl.to_schedule([final(scores=(1, 2), period='SO')], SEASON)
    row = df.iloc[0]
    assert row['home_win'] == 0 and row['last_period'] == 'SO'
    assert (row['home_score'], row['away_score']) == (1, 2)


def test_an_overtime_win_at_home_is_a_home_win():
    df = nhl.to_schedule([final(scores=(4, 3), period='OT')], SEASON)
    assert df.loc[0, 'home_win'] == 1 and df.loc[0, 'last_period'] == 'OT'


def test_a_game_not_yet_final_has_no_result_even_with_a_score_on_the_board():
    live = game(state='LIVE', scores=(2, 0))
    df = nhl.to_schedule([live], SEASON)
    assert df.loc[0, ['home_score', 'away_score', 'home_win', 'last_period']].isna().all()


# --- the shape ----------------------------------------------------------------

def test_the_frame_meets_the_core_contract_and_keeps_the_extras():
    df = nhl.to_schedule([final(), game(), game(gid=2026030111, game_type=3, home='BOS', away='FLA')], SEASON)
    assert list(df.columns) == [*SCHEDULE_COLUMNS, *nhl.EXTRA_COLUMNS]
    assert check_schedule('nhl', df) == []
    assert str(df['start_utc'].dt.tz) == 'UTC'
    assert df['home_win'].dtype == 'Int64'
    assert set(df['game_type']) == {'regular', 'playoff'}
    assert df['game_id'].tolist() == sorted(df['game_id'])  # same start order here: by id
    assert df.loc[0, 'season'] == SEASON and df.loc[0, 'slate'] == '2026-10-06'


def test_games_come_out_earliest_start_first():
    late = game(gid=2026020002, start='2026-10-07T02:00:00Z')
    early = game(gid=2026020003, start='2026-10-06T23:00:00Z', home='BOS', away='BUF')
    df = nhl.to_schedule([late, early], SEASON)
    assert df['game_id'].tolist() == ['2026020003', '2026020002']


def test_the_day_slate_is_one_league_date():
    df = nhl.to_schedule([game(gid=1, day='2026-10-06'), game(gid=2, day='2026-10-07',
                                                              start='2026-10-07T23:00:00Z')], SEASON)
    assert nhl.slate(df, '2026-10-07')['game_id'].tolist() == ['2']
    assert nhl.slate(df, '2026-10-08').empty


# --- what stops the load ------------------------------------------------------

@pytest.mark.parametrize('bad, words', [
    (game(state='WEIRD'), "unknown gameState 'WEIRD'"),
    (game(sched='MOVED'), "unknown gameScheduleState 'MOVED'"),
    (game(start='2026-10-06T19:00:00-04:00'), 'is not UTC'),
    (game(away='TOR'), 'not two teams'),
    (game(startTimeUTC=None), 'no startTimeUTC'),
    (game(gameDate=''), 'no gameDate'),
    (final(scores=(2, 2)), 'tied score'),
    (game(state='OFF', period='REG'), 'without both scores'),
    (final(period=None), 'without a last period'),
    (final(period='OT2'), 'without a last period'),
])
def test_anything_unrecognised_stops_the_load_and_is_named(bad, words):
    assert any(words in p for p in nhl.raw_problems(bad))
    with pytest.raises(nhl.NHLScheduleError, match=re.escape(words)):
        nhl.to_schedule([bad], SEASON)


def test_a_usable_game_has_no_problems():
    assert nhl.raw_problems(game()) == []
    assert nhl.raw_problems(final()) == []


def test_a_game_from_another_season_stops_the_load():
    with pytest.raises(nhl.NHLScheduleError, match='another season'):
        nhl.to_schedule([game(season=20252026)], SEASON)


# --- reading the league, club by club -------------------------------------------

def feed(games_by_club):
    calls = []

    def get(url):
        calls.append(url)
        club = url.split('/')[-2]
        return {'games': games_by_club.get(club, [])}
    return get, calls


def test_every_game_is_read_once_from_its_two_clubs_lists():
    g1, g2 = final(gid=1, home='TOR', away='MTL'), final(gid=2, home='MTL', away='BOS')
    get, calls = feed({'TOR': [g1], 'MTL': [g1, g2], 'BOS': [g2]})
    games = nhl.club_games(SEASON, get, clubs=('TOR', 'MTL', 'BOS'))
    assert [g['id'] for g in games] == [1, 2]
    assert calls[0].endswith('/club-schedule-season/TOR/20262027')


def test_a_game_seen_from_only_one_side_stops_the_load():
    """A club's list that came back short would otherwise leave a hole the
    model never sees."""
    g1 = final(gid=1, home='TOR', away='MTL')
    get, _ = feed({'TOR': [g1], 'MTL': []})
    with pytest.raises(nhl.NHLScheduleError, match='only one club'):
        nhl.club_games(SEASON, get, clubs=('TOR', 'MTL'))


def test_preseason_and_all_star_games_are_left_out():
    pre, star = game(gid=1, game_type=1), game(gid=2, game_type=4)
    reg = game(gid=3)
    get, _ = feed({'TOR': [pre, star, reg], 'NSH': [pre, star, reg]})
    assert [g['id'] for g in nhl.club_games(SEASON, get, clubs=('TOR', 'NSH'))] == [3]


def test_the_club_list_covers_the_current_league_and_its_old_names():
    assert len(nhl.CLUBS) == len(set(nhl.CLUBS)) == 35
    assert {'UTA', 'SEA', 'VGK', 'ARI', 'PHX', 'ATL'} <= set(nhl.CLUBS)


# --- seasons and the cache ----------------------------------------------------------

def test_season_ids_and_season_boundaries():
    assert nhl.season_id(2026) == 20262027
    assert nhl.current_season(datetime(2026, 8, 31, tzinfo=UTC)) == 2025
    assert nhl.current_season(datetime(2026, 9, 1, tzinfo=UTC)) == 2026
    assert nhl.current_season(datetime(2027, 6, 10, tzinfo=UTC)) == 2026


def season_feed(season, games):
    sid = nhl.season_id(season)
    for g in games:
        g['season'] = sid
    by_club: dict[str, list] = {}
    for g in games:
        for side in ('homeTeam', 'awayTeam'):
            by_club.setdefault(g[side]['abbrev'], []).append(g)
    return feed(by_club)


NOW = datetime(2026, 10, 5, 12, tzinfo=UTC)


def test_a_finished_past_season_is_cached_once_and_read_back(tmp_path):
    get, calls = season_feed(2024, [final(gid=1), final(gid=2, home='MTL', away='TOR', scores=(1, 4))])
    first = nhl.load_schedule(2024, get, cache=tmp_path, now=NOW)
    n = len(calls)
    assert (tmp_path / 'schedule_2024.parquet').exists()
    again = nhl.load_schedule(2024, get, cache=tmp_path, now=NOW)
    assert len(calls) == n  # read from the cache, not the league
    pd.testing.assert_frame_equal(first, again)


def test_the_current_season_is_never_cached(tmp_path):
    get, _ = season_feed(2026, [final(gid=1)])
    nhl.load_schedule(2026, get, cache=tmp_path, now=NOW)
    assert not list(tmp_path.iterdir())


def test_a_past_season_with_a_game_still_to_play_is_not_cached(tmp_path):
    get, _ = season_feed(2025, [final(gid=1), game(gid=2, home='BOS', away='FLA')])
    nhl.load_schedule(2025, get, cache=tmp_path, now=NOW)
    assert not list(tmp_path.iterdir())


def test_nothing_is_cached_when_the_cache_is_not_set(tmp_path, monkeypatch):
    monkeypatch.delenv(nhl.CACHE_ENV, raising=False)
    assert nhl.cache_dir() is None
    monkeypatch.setenv(nhl.CACHE_ENV, str(tmp_path))
    assert nhl.cache_dir() == tmp_path
