"""The NBA's v2 shadow, each registered change on small synthetic games (experiments/nba/stage95_v2/registry.json).

`src/sports/nba/v2.py` is written after the registration and before any v2 fit; these tests hold each item to the
registration's words: 27 drops the exhibitions, 30 places a doubled slate by ESPN's record and refuses one still
doubled, 29 drops prices and boxes outside their bounds (allowing whole-minute rounding), 24 reads availability
from the previous game and never the game itself, and 28 takes the home edge off a neutral-site forecast.

Run with: pytest tests/test_nba_v2.py -v
"""
import json

import numpy as np
import pandas as pd
import pytest

from src.core.day_backtest import estimator
from src.sports.nba import v2


def games(rows):
    g = pd.DataFrame(rows, columns=['game_id', 'season', 'slate', 'home', 'away'])
    g['game_id'] = g['game_id'].astype(str)
    return g


def test_item_27_drops_a_game_with_a_side_that_is_not_a_club():
    g = games([('1', 2018, '2018-02-16', 'USA', 'WORLD'), ('2', 2018, '2018-02-16', 'BOS', 'NY'),
               ('3', 2018, '2018-02-17', 'BOS', 'WORLD'), ('4', 2018, '2018-02-17', 'USA', 'NY')])
    kept, dropped = v2.drop_exhibitions(g)
    assert list(kept['game_id']) == ['2'] and dropped == ['1', '3', '4'], 'either side not a club drops the game'


def test_item_30_places_a_doubled_slate_by_espns_record_and_refuses_one_still_doubled():
    g = games([('401161536', 2020, '2020-03-01', 'PHX', 'GS'), ('401161543', 2020, '2020-03-01', 'GS', 'WSH'),
               ('9', 2020, '2020-03-01', 'BOS', 'NY')])
    assert v2.doubled_slates(g) == {'2020-03-01': ['401161536', '401161543']}
    placed, moved = v2.place_slates(g, {'401161536': '2020-02-29', '401161543': '2020-03-01'}.get)
    assert moved == {'401161536': '2020-02-29', '401161543': '2020-03-01'}
    assert v2.doubled_slates(placed) == {}
    assert placed.set_index('game_id').loc['9', 'slate'] == '2020-03-01', 'a game not doubled is not moved'
    with pytest.raises(ValueError, match='still appears twice'):
        v2.place_slates(g, lambda gid: '2020-03-01')


def test_espns_start_is_read_as_an_eastern_date():
    def get(url):
        assert url.endswith('event=401161536')
        return json.dumps({'header': {'competitions': [{'date': '2020-03-01T02:00Z'}]}}).encode()
    assert v2.espn_slate('401161536', get) == '2020-02-29', '2 AM UTC is the evening before in Eastern time'


def test_item_29_drops_prices_outside_their_bounds():
    m = pd.DataFrame({'game_id': ['a', 'b', 'c'], 'home_price': [-110, -105, -300], 'away_price': [-110, 100, -300]})
    kept, dropped = v2.drop_bad_prices(m)
    # a: 0.524 + 0.524 = 1.048 (kept); b: 0.512 + 0.5 = 1.012 (kept); c: 0.75 + 0.75 = 1.50 (dropped)
    assert list(kept['game_id']) == ['a', 'b'] and dropped == ['c']
    low = pd.DataFrame({'game_id': ['d'], 'home_price': [120], 'away_price': [110]})  # 0.455 + 0.476 < 1
    assert v2.drop_bad_prices(low)[1] == ['d']


def box(gid, team, mins):
    return [{'game_id': gid, 'team': team, 'player_id': f'{team}{i}', 'minutes': m} for i, m in enumerate(mins)]


def test_item_29_allows_whole_minute_rounding_and_drops_a_box_short_beyond_it():
    rounded = box('g1', 'BOS', [36, 35, 34, 33, 30, 25, 20, 15, 10])  # 238 over 9 players: 2 short, 4.5 allowed
    short = box('g2', 'CHI', [36, 35, 34, 33, 30, 25, 20, 10])         # 223 over 8 players: 17 short, 4 allowed
    overtime = box('g3', 'NY', [45, 44, 40, 38, 35, 30, 23])           # 255
    m = pd.DataFrame(rounded + short + overtime)
    assert v2.short_boxes(m) == {('g2', 'CHI')}


def team_games(n, team='BOS', start='2024-11-01'):
    days = pd.date_range(start, periods=n, freq='2D')
    g = pd.DataFrame({'game_id': [f'g{i}' for i in range(n)], 'day': days,
                      'home': [team] * n, 'away': [f'X{i}' for i in range(n)]})
    return g


def test_item_24_reads_who_played_in_the_previous_game_not_this_one():
    g = team_games(3)
    stars = [('a', 40), ('b', 40), ('c', 40), ('d', 40), ('e', 40), ('f', 40)]
    rows = [{'game_id': 'g0', 'team': 'BOS', 'player_id': p, 'minutes': m} for p, m in stars]
    rows += [{'game_id': 'g1', 'team': 'BOS', 'player_id': p, 'minutes': m} for p, m in stars if p != 'a']
    rows += [{'game_id': 'g2', 'team': 'BOS', 'player_id': p, 'minutes': m} for p, m in stars]
    avail = v2.availability_table(g, pd.DataFrame(rows), half_life=60)
    assert avail['g0'] == pytest.approx(0.0), "a team's first game: both sides 1.0"
    assert avail['g1'] == pytest.approx(0.0), 'g1 reads g0, where everyone played: "a" sitting out g1 is not read'
    assert avail['g2'] < -0.05, '"a" missed the previous game, so he counts as out for g2 although he played it'


def test_item_24_a_box_not_used_tells_nothing_about_the_next_game():
    g = team_games(3)
    rows = [{'game_id': gid, 'team': 'BOS', 'player_id': p, 'minutes': 40}
            for gid, players in (('g0', 'abcdef'), ('g1', 'b'), ('g2', 'abcdef')) for p in players]
    m = pd.DataFrame(rows)
    assert v2.availability_table(g, m, 60)['g2'] < -0.5, 'read: only b played g1'
    assert v2.availability_table(g, m, 60, unusable={('g1', 'BOS')})['g2'] == pytest.approx(0.0)


def test_item_28_a_neutral_game_gets_no_home_edge():
    rng = np.random.default_rng(1)
    n = 400
    t = pd.DataFrame({'game_id': [str(i) for i in range(n)], 'season': [2024] * (n - 2) + [2025, 2025],
                      'day': list(pd.date_range('2024-01-01', periods=n - 2)) + [pd.Timestamp('2025-06-01')] * 2,
                      'x': rng.normal(size=n), 'neutral_site': [False] * (n - 1) + [True]})
    t['home_win'] = (rng.random(n) < 1 / (1 + np.exp(-(0.6 + t['x'])))).astype(int)
    t.loc[n - 1, 'x'] = t.loc[n - 2, 'x']
    p = v2.walk_forward(t, ['x'], [2025])
    model = estimator().fit(t.loc[: n - 3, ['x']], t.loc[: n - 3, 'home_win'])
    z = model.decision_function(t.loc[[n - 2], ['x']])[0]
    b = float(model[-1].intercept_[0])
    assert p[str(n - 2)] == pytest.approx(1 / (1 + np.exp(-z)))
    assert p[str(n - 1)] == pytest.approx(1 / (1 + np.exp(-(z - b)))), 'the neutral game loses exactly the intercept'
    assert p[str(n - 1)] < p[str(n - 2)], 'with a home edge fitted, the same matchup at a neutral site is less sure'
