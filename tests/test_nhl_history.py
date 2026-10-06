"""The NHL's stored history: box-score rows, the fallback check, and the
market's two-way probability (Stage 56, as registered).

Payloads are small and synthetic, in the shapes the league's box score,
SportsDataverse's team_box and ESPN's scoreboard and odds had on
2026-10-05.

Run with: pytest tests/test_nhl_history.py -v
"""
import json
import math

import pandas as pd
import pytest

from src.sports.nhl import history


def box(gid=2025020672, home_sog=23, away_sog=33, starters=(1, 1), period='REG'):
    def goalies(n, first):
        return [{'playerId': first + i, 'starter': i < n, 'shotsAgainst': 30 if i < n else 0,
                 'goalsAgainst': 2 if i < n else 0} for i in range(max(n, 1) + 1)]
    return {'id': gid, 'season': 20252026, 'gameDate': '2026-01-06', 'gameOutcome': {'lastPeriodType': period},
            'homeTeam': {'abbrev': 'TOR', 'score': 4, 'sog': home_sog},
            'awayTeam': {'abbrev': 'FLA', 'score': 1, 'sog': away_sog},
            'playerByGameStats': {'homeTeam': {'goalies': goalies(starters[0], 100)},
                                  'awayTeam': {'goalies': goalies(starters[1], 200)}}}


def test_a_box_score_becomes_one_row_with_each_starters_own_shots_and_goals():
    row = history.box_row(box(), 'regular')
    assert row['game_id'] == '2025020672' and row['season'] == 2025 and row['game_type'] == 'regular'
    assert (row['home_sog'], row['away_sog']) == (23, 33)
    assert (row['home_goalie_id'], row['home_goalie_sa'], row['home_goalie_ga']) == (100, 30, 2)
    assert row['away_goalie_id'] == 200 and row['last_period'] == 'REG'
    assert list(row) == list(history.BOX_FIELDS)


@pytest.mark.parametrize('starters', [(0, 1), (2, 1)])
def test_a_side_without_exactly_one_starter_stops_the_season(starters):
    with pytest.raises(history.HistoryError, match='starting goalies flagged, not 1'):
        history.box_row(box(starters=starters), 'regular')


def test_a_box_score_without_shots_on_goal_stops_the_season():
    b = box()
    del b['homeTeam']['sog']
    with pytest.raises(history.HistoryError, match='no shots on goal for TOR'):
        history.box_row(b, 'regular')


def team_box(rows):
    out = []
    for gid, h, a in rows:
        out += [{'game_id': int(gid), 'home_away': 'home', 'shots_on_goal': h},
                {'game_id': int(gid), 'home_away': 'away', 'shots_on_goal': a}]
    return pd.DataFrame(out)


def ours(rows):
    return pd.DataFrame([{'game_id': gid, 'home_sog': h, 'away_sog': a} for gid, h, a in rows])


def test_the_fallback_agreeing_passes_and_one_disagreement_in_a_hundred_is_listed_not_fatal():
    games = [(str(i), 30, 25) for i in range(100)]
    fb = [(g, h, a) for g, h, a in games]
    fb[0] = ('0', 31, 25)
    assert history.check_against_fallback(ours(games), team_box(fb)) == []
    n, bad = history.fallback_disagreements(ours(games), team_box(fb))
    assert n == 100 and bad == ['game 0: league 30-25, fallback 31-25']


def test_the_fallback_disagreeing_on_more_than_one_game_in_a_hundred_stops_the_season():
    games = [(str(i), 30, 25) for i in range(100)]
    fb = [(g, h + (1 if int(g) < 2 else 0), a) for g, h, a in games]
    problems = history.check_against_fallback(ours(games), team_box(fb))
    assert problems[0] == 'shots on goal agree on 98 of 100 games, under 99%'
    assert len(problems) == 3


def test_a_fallback_with_none_of_the_seasons_games_stops_it():
    assert history.check_against_fallback(ours([('1', 30, 25)]), team_box([('2', 30, 25)])) == [
        "the fallback has none of this season's games"]


def test_a_native_season_takes_the_margin_out_and_an_earlier_one_is_converted():
    p, converted = history.two_way(-150, 130, 2024)
    h, a = 150 / 250, 100 / 230
    assert not converted and p == pytest.approx(h / (h + a))
    q, converted = history.two_way(-150, 130, 2023)
    a0, b0 = history.CONVERSION
    z = a0 + b0 * math.log(p / (1 - p))
    assert converted and q == pytest.approx(1 / (1 + math.exp(-z)))
    assert q < p  # the slope under 1 pulls a three-way favourite toward a half


def scoreboard(events):
    return json.dumps({'events': events}).encode()


def event(eid, home, away, completed=True, season_type=2):
    return {'id': eid, 'season': {'type': season_type},
            'competitions': [{'status': {'type': {'completed': completed}},
                              'competitors': [{'homeAway': 'home', 'team': {'abbreviation': home}},
                                              {'homeAway': 'away', 'team': {'abbreviation': away}}]}]}


def odds(home, away, provider='DraftKings'):
    return json.dumps({'items': [{'provider': {'name': provider}, 'homeTeamOdds': {'moneyLine': home},
                                  'awayTeamOdds': {'moneyLine': away}}]}).encode()


SCHED = pd.DataFrame([
    {'game_id': '2025020001', 'slate': '2025-10-07', 'home': 'NJD', 'away': 'TBL', 'game_type': 'regular', 'status': 'final'},
    {'game_id': '2025020002', 'slate': '2025-10-07', 'home': 'BOS', 'away': 'LAK', 'game_type': 'regular', 'status': 'final'},
])


def espn(pages):
    def get(url):
        for key, body in pages.items():
            if key in url:
                return body
        raise AssertionError(url)
    return get


def test_espn_games_are_matched_to_the_league_through_its_own_abbreviations():
    get = espn({'dates=20251007': scoreboard([event('1', 'NJ', 'TB'), event('2', 'BOS', 'LA'),
                                              event('3', 'NYR', 'PIT', completed=False),
                                              event('4', 'CHI', 'DET', season_type=1)]),
                'events/1/': odds('-120', '+100'), 'events/2/': odds('+110', '-130')})
    df = history.espn_season(2025, SCHED, get, pause=0)
    assert df['game_id'].tolist() == ['2025020001', '2025020002']
    assert df.loc[0, 'home'] == 'NJD' and df.loc[0, 'home_price'] == -120.0
    assert not df['converted'].any()


def test_an_espn_game_the_league_does_not_have_stops_the_season():
    get = espn({'dates=20251007': scoreboard([event('9', 'SEA', 'VAN')])})
    with pytest.raises(history.HistoryError, match='VAN at SEA on 2025-10-07'):
        history.espn_season(2025, SCHED, get, pause=0)
