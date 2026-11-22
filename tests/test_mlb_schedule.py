"""MLB's schedule (Stage 98 item 2): the Stats API's games in the core's shape, as the registration reads them.

Every game here is built by hand in the Stats API's shape, so nothing is fetched.

Run with: pytest tests/test_mlb_schedule.py -v
"""
from datetime import UTC, datetime

import pandas as pd
import pytest

from src.core.sport import SCHEDULE_COLUMNS
from src.sports.mlb import schedule as s

HOME_VENUES = {147: 3313, 111: 3, 141: 14}


def game(pk=1, home=147, away=111, day='2025-07-04', start='2025-07-04T23:05:00Z', coded='F',
         gtype='R', hs=5, as_=3, venue=3313, number=1, dh='N', season='2025', **extra):
    g = {'gamePk': pk, 'gameType': gtype, 'season': season, 'gameDate': start, 'officialDate': day,
         'gameNumber': number, 'doubleHeader': dh, 'venue': {'id': venue, 'name': f'venue {venue}'},
         'status': {'codedGameState': coded},
         'teams': {'home': {'team': {'id': home}, 'score': hs}, 'away': {'team': {'id': away}, 'score': as_}}}
    g.update(extra)
    return g


def frame(*games):
    return s.to_schedule(list(games), 2025, HOME_VENUES)


def test_a_final_game_in_the_cores_shape():
    df = frame(game())
    assert list(df.columns[:len(SCHEDULE_COLUMNS)]) == list(SCHEDULE_COLUMNS)
    row = df.iloc[0]
    assert (row['game_id'], row['slate'], row['home'], row['away'], row['status']) == (
        '1', '2025-07-04', '147', '111', 'final')
    assert (row['home_score'], row['away_score'], row['home_win']) == (5, 3, 1)
    assert str(df['start_utc'].dt.tz) == 'UTC'


def test_a_relisted_game_is_one_row_and_the_last_listing_wins():
    """A postponed game keeps its gamePk and is listed again on the day it is played."""
    first = game(pk=7, day='2025-05-01', start='2025-05-01T23:05:00Z', coded='D', hs=None, as_=None)
    played = game(pk=7, day='2025-05-02', start='2025-05-02T17:05:00Z', coded='F', hs=2, as_=4)
    df = frame(played, first)
    assert len(df) == 1
    assert (df.iloc[0]['slate'], df.iloc[0]['status'], df.iloc[0]['home_win']) == ('2025-05-02', 'final', 0)


def test_a_doubleheader_is_two_games_told_apart_by_gamepk():
    df = frame(game(pk=1, number=1, dh='S'), game(pk=2, number=2, dh='S', start='2025-07-05T03:05:00Z'))
    assert list(df['game_id']) == ['1', '2'] and list(df['game_number']) == [1, 2]


def test_each_game_keeps_its_place_in_its_series():
    """The board's series line ("game 2 of 4") reads these; a doubleheader is two places in one series."""
    df = frame(game(pk=1, number=1, dh='Y', seriesGameNumber=2, gamesInSeries=4),
               game(pk=2, number=2, dh='Y', start='2025-07-05T03:05:00Z', seriesGameNumber=3, gamesInSeries=4))
    assert list(df['series_game']) == [2, 3] and list(df['series_games']) == [4, 4]
    assert str(df['series_game'].dtype) == 'Int64' and str(df['series_games'].dtype) == 'Int64'


@pytest.mark.parametrize('place', [{}, {'seriesGameNumber': 1, 'gamesInSeries': 0},
                                   {'seriesGameNumber': 4, 'gamesInSeries': 3},
                                   {'seriesGameNumber': 0, 'gamesInSeries': 3},
                                   {'seriesGameNumber': '2', 'gamesInSeries': 3},
                                   {'seriesGameNumber': True, 'gamesInSeries': 3},
                                   {'seriesGameNumber': 2}],
                         ids=['missing', 'one-of-none', 'past-the-end', 'game-zero', 'text', 'boolean', 'no-length'])
def test_a_place_that_makes_no_sense_is_left_empty_and_the_game_still_loads(place):
    """2023's 716404 reads 1 of 0 and 2025's 776907 reads 4 of 3: shown as no series line, never a stopped load."""
    df = frame(game(pk=9, **place))
    assert len(df) == 1 and df.iloc[0]['status'] == 'final'
    assert pd.isna(df.iloc[0]['series_game']) and pd.isna(df.iloc[0]['series_games'])


def test_the_last_game_of_a_series_is_kept():
    df = frame(game(seriesGameNumber=3, gamesInSeries=3))
    assert (df.iloc[0]['series_game'], df.iloc[0]['series_games']) == (3, 3)


def test_a_start_the_league_has_not_set_is_marked():
    """Opening Day 2027's CLE at CHC is listed at 08:33 UTC with startTimeTBD: a placeholder, not a time."""
    df = frame(game(pk=1, coded='S', hs=None, as_=None, status={'codedGameState': 'S', 'startTimeTBD': True}),
               game(pk=2, coded='S', hs=None, as_=None, status={'codedGameState': 'S', 'startTimeTBD': False}))
    assert list(df['start_time_tbd']) == [True, False]


@pytest.mark.parametrize('flag', ['missing', 'true-as-text', 'one'])
def test_only_an_explicit_true_marks_a_start_as_not_set(flag):
    status = {'codedGameState': 'F'} | ({} if flag == 'missing' else {'startTimeTBD': 'true' if flag == 'true-as-text' else 1})
    df = frame(game(pk=3, status=status))
    assert list(df['start_time_tbd']) == [False]


def test_spring_training_exhibition_and_all_star_games_are_left_out():
    df = frame(game(pk=1), game(pk=2, gtype='S'), game(pk=3, gtype='E'), game(pk=4, gtype='A'),
               game(pk=5, gtype='W'))
    assert list(df['game_id']) == ['1', '5'] and list(df['game_type']) == ['regular', 'world_series']


def test_an_unknown_game_type_or_state_stops_the_load():
    with pytest.raises(s.MLBScheduleError, match="unknown gameType 'Z'"):
        frame(game(gtype='Z'))
    with pytest.raises(s.MLBScheduleError, match="unknown codedGameState 'Q'"):
        frame(game(coded='Q'))


def test_completed_early_is_final_and_game_over_waits():
    """'Completed Early' is coded F; 'Game Over' (O) has its score but is not final yet."""
    df = frame(game(pk=1, coded='F'), game(pk=2, coded='O', start='2025-07-05T01:00:00Z'))
    assert list(df['status']) == ['final', 'in_progress']
    assert pd.isna(df.iloc[1]['home_win'])


def test_postponed_suspended_and_cancelled_games_have_no_result():
    df = frame(game(pk=1, coded='D', hs=None, as_=None), game(pk=2, coded='U', hs=1, as_=1),
               game(pk=3, coded='C', hs=None, as_=None))
    assert set(df['status']) == {'postponed', 'suspended', 'cancelled'}
    assert df['home_win'].isna().all()


def test_a_tied_or_scoreless_final_stops_the_load():
    with pytest.raises(s.MLBScheduleError, match='tied score 2-2 and no isTie'):
        frame(game(hs=2, as_=2))
    with pytest.raises(s.MLBScheduleError, match='final without both scores'):
        frame(game(hs=None))


def test_an_official_tie_is_final_with_no_winner():
    df = frame(game(hs=1, as_=1, isTie=True))
    assert df.iloc[0]['status'] == 'final' and pd.isna(df.iloc[0]['home_win'])
    assert (df.iloc[0]['home_score'], df.iloc[0]['away_score']) == (1, 1)


def test_a_game_away_from_the_home_clubs_own_venue_is_neutral_and_keeps_its_home_club():
    df = frame(game(pk=1), game(pk=2, venue=999, start='2025-07-05T01:00:00Z'))
    assert list(df['neutral_site']) == [False, True]
    assert list(df['home']) == ['147', '147']


def test_a_home_club_with_no_venue_for_the_season_stops_the_load():
    with pytest.raises(s.MLBScheduleError, match='no home venue for 2025'):
        frame(game(home=999))


def test_a_game_from_another_season_or_not_in_utc_stops_the_load():
    with pytest.raises(s.MLBScheduleError, match='another season'):
        frame(game(season='2024'))
    with pytest.raises(s.MLBScheduleError, match='is not UTC'):
        frame(game(start='2025-07-04T19:05:00-04:00'))


def test_home_venues_read_each_clubs_venue_for_the_season():
    data = {'teams': [{'id': 147, 'venue': {'id': 3313}}, {'id': 111, 'venue': {'id': 3}}, {'id': 5}]}
    assert s.home_venues(data) == {147: 3313, 111: 3}


def test_the_season_runs_february_to_january():
    assert s.current_season(datetime(2027, 1, 20, tzinfo=UTC)) == 2026
    assert s.current_season(datetime(2027, 2, 15, tzinfo=UTC)) == 2027
    assert s.current_season(datetime(2026, 11, 12, tzinfo=UTC)) == 2026


def fake_get(games):
    def get(url):
        if '/teams?' in url:
            return {'teams': [{'id': k, 'venue': {'id': v}} for k, v in HOME_VENUES.items()]}
        assert 'season=2025' in url and 'gameType=R,F,D,L,W' in url
        return {'dates': [{'games': games}]}
    return get


def test_a_finished_past_season_is_cached_and_read_back(tmp_path):
    now = datetime(2026, 11, 12, tzinfo=UTC)
    first = s.load_schedule(2025, get=fake_get([game()]), cache=tmp_path, now=now)
    assert (tmp_path / 'schedule_2025.parquet').exists()

    def refuse(url):
        raise AssertionError('read from the network, not the cache')
    again = s.load_schedule(2025, get=refuse, cache=tmp_path, now=now)
    assert again['game_id'].tolist() == first['game_id'].tolist()


def test_the_current_season_and_an_unfinished_one_are_never_cached(tmp_path):
    s.load_schedule(2025, get=fake_get([game()]), cache=tmp_path, now=datetime(2025, 8, 1, tzinfo=UTC))
    s.load_schedule(2025, get=fake_get([game(coded='S', hs=None, as_=None)]), cache=tmp_path,
                    now=datetime(2026, 11, 12, tzinfo=UTC))
    assert not list(tmp_path.iterdir())


def test_a_slate_is_one_official_date():
    df = frame(game(pk=1), game(pk=2, day='2025-07-05', start='2025-07-05T23:05:00Z'))
    assert s.slate(df, '2025-07-05')['game_id'].tolist() == ['2']


def test_probables_name_each_clubs_pitcher_or_none():
    g = game(pk=9, coded='S', hs=None, as_=None)
    g['teams']['home']['probablePitcher'] = {'id': 500}
    assert s.probables({'dates': [{'games': [g]}]}) == {'9': (500, None)}
