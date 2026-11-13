"""NCAA tournament seeds (Stage 103 item 2), on scoreboards built by hand.

Run with: pytest tests/test_ncaam_seeds.py -v
"""
import pandas as pd
import pytest

from src.sports.ncaam import seeds as s
from src.sports.ncaam.collector import CollectorError


def game(gid, note, home='1', away='2'):
    return {'game_id': gid, 'note': note, 'home_id': home, 'away_id': away}


def board(*games):
    return {'events': [{'id': gid, 'competitions': [{'tournamentId': t, 'competitors': [
        {'homeAway': 'home', 'curatedRank': {'current': h}}, {'homeAway': 'away', 'curatedRank': {'current': a}}]}]}
        for gid, t, h, a in games]}


def first_round(n=32, season=2024):
    games = pd.DataFrame([game(str(i), 'East Region - 1st Round', str(2 * i), str(2 * i + 1)) for i in range(n)]
                         + [game('T', 'National Championship', '900', '901')])
    found = {str(i): (1 + i % 8, 16 - i % 8) for i in range(n)}
    found['T'] = (1, 2)
    return games, found


def test_the_seed_is_the_curated_rank_and_only_tournament_games_count():
    out = s.seeds_on(board(('1', '22', 1, 16), ('2', '21', 3, 99)))
    assert out == {'1': (1, 16)}


def test_a_full_first_round_whose_pairs_add_to_seventeen_passes():
    games, found = first_round()
    rows = s.check(games, found, 2024)
    assert len(rows) == 33 and rows[0] == {'game_id': '0', 'home_seed': 1, 'away_seed': 16, 'filled': ''}


def test_a_first_round_pair_not_adding_to_seventeen_or_a_seed_outside_one_to_sixteen_stops_naming_each():
    games, found = first_round()
    found['3'], found['5'] = (4, 12), (99, 11)
    with pytest.raises(CollectorError) as e:
        s.check(games, found, 2024)
    assert 'game 3' in str(e.value) and 'game 5' in str(e.value) and 'game 4' not in str(e.value)


def test_the_round_of_64_is_named_by_its_era_and_counted():
    assert s.round_of_64("MEN'S BASKETBALL CHAMPIONSHIP - EAST REGION - 2nd ROUND", 2014)
    assert not s.round_of_64('East Region - 2nd Round', 2015)
    games, found = first_round(31)
    assert len(s.check(games.iloc[:5], found, 2024)) == 5, 'an unfinished tournament is not counted'
    with pytest.raises(CollectorError, match='31 first-round games named, not 32'):
        s.check(games, found, 2024)
    assert len(s.check(games, found, 2020)) == 32, 'the 2021 no-contest: 31 first-round games and the final'


def test_a_first_four_side_espn_leaves_unranked_takes_its_opponents_seed_and_says_so():
    games = pd.DataFrame([game('9', 'East Region - First Four')])
    [row] = s.check(games, {'9': (16, 99)}, 2019)
    assert row == {'game_id': '9', 'home_seed': 16, 'away_seed': 16, 'filled': 'away'}
    with pytest.raises(CollectorError):
        s.check(pd.DataFrame([game('8', 'East Region - Sweet 16')]), {'8': (2, 99)}, 2019)


def test_a_club_seeded_differently_in_two_games_stops_the_run():
    games = pd.DataFrame([game('1', 'East Region - Sweet 16', '10', '11'), game('2', 'East Region - Elite 8', '10', '12')])
    with pytest.raises(CollectorError, match='club 10 seeded 2 here, 1 before'):
        s.check(games, {'1': (1, 4), '2': (2, 3)}, 2019)


def test_a_tournament_game_missing_from_the_scoreboard_is_named():
    with pytest.raises(CollectorError, match='game 7: not on the scoreboard'):
        s.check(pd.DataFrame([game('7', 'East Region - Sweet 16')]), {}, 2019)
