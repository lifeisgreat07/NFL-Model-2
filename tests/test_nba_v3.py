"""The NBA's v3 (Stage 105): v2 plus the back-to-back flag and star-weighted availability, as a shadow.

Run with: pytest tests/test_nba_v3.py -v
"""
import numpy as np
import pandas as pd
import pytest

from src.core.day_backtest import estimator
from src.sports.nba import v2, v3, v3_shadow


def g(day, home, away, gid=None):
    return {'game_id': gid or f'{day}{home}', 'day': pd.Timestamp(day), 'home': home, 'away': away}


def test_the_flag_is_the_away_clubs_back_to_back_minus_the_home_clubs():
    played = v3.played_days(pd.DataFrame([g('2026-11-10', 'BOS', 'NYK'), g('2026-11-10', 'LAL', 'GS')]))
    rows = pd.DataFrame([g('2026-11-11', 'LAL', 'BOS'), g('2026-11-11', 'MIA', 'NYK'),
                         g('2026-11-11', 'GS', 'PHX'), g('2026-11-12', 'BOS', 'NYK')])
    assert list(v3.b2b_matchup(rows, played)) == [0.0, 1.0, -1.0, 0.0]


def test_a_clubs_first_game_of_a_season_is_not_a_back_to_back():
    played = v3.played_days(pd.DataFrame([g('2026-04-12', 'BOS', 'NYK')]))
    assert list(v3.b2b_matchup(pd.DataFrame([g('2026-10-21', 'BOS', 'NYK')]), played)) == [0.0]


def minutes_for(rows):
    return pd.DataFrame(rows, columns=['game_id', 'team', 'player_id', 'minutes'])


def test_star_weighting_squares_each_players_expected_minutes_and_power_one_is_v2():
    # BOS's first game: a 36-minute star and three 12-minute players (the rest of the 240 left out). In the second
    # game the star is out: availability for the third game counts who played in the second.
    games = pd.DataFrame([g('2026-11-01', 'BOS', 'NYK', '1'), g('2026-11-03', 'BOS', 'NYK', '2'),
                          g('2026-11-05', 'BOS', 'NYK', '3')])
    first = [['1', 'BOS', 'star', 36], ['1', 'BOS', 'a', 12], ['1', 'BOS', 'b', 12], ['1', 'BOS', 'c', 12],
             ['1', 'NYK', 'n', 48]]
    second = [['2', 'BOS', 'a', 24], ['2', 'BOS', 'b', 24], ['2', 'BOS', 'c', 24], ['2', 'NYK', 'n', 48]]
    m = minutes_for(first + second)
    one = v2.availability_table(games, m, 1e9)
    two = v2.availability_table(games, m, 1e9, power=2.0)
    # After two games the expected minutes are star 18, a b c 18 each: equal, so squaring changes nothing here.
    assert one['3'] == pytest.approx(two['3'])
    lopsided = minutes_for(first + [['2', 'BOS', 'a', 12], ['2', 'BOS', 'b', 12], ['2', 'BOS', 'c', 12],
                                    ['2', 'BOS', 'star', 36], ['2', 'NYK', 'n', 48]])
    games4 = pd.concat([games, pd.DataFrame([g('2026-11-07', 'BOS', 'NYK', '4')])], ignore_index=True)
    third = minutes_for([['3', 'BOS', 'a', 20], ['3', 'BOS', 'b', 20], ['3', 'BOS', 'c', 20], ['3', 'NYK', 'n', 48]])
    m4 = pd.concat([lopsided, third], ignore_index=True)
    avail1 = v2.availability_table(games4, m4, 1e9)['4']
    avail2 = v2.availability_table(games4, m4, 1e9, power=2.0)['4']
    # Game 4: expected minutes over games 1-3 are star 24 and a, b, c 44/3 each; the star sat out game 3. By minutes
    # 44/68 of BOS is there; squared, the star weighs more and less of BOS is there. NYK is whole either way.
    each = 44 / 3
    assert avail1 == pytest.approx(3 * each / (24 + 3 * each) - 1.0)
    assert avail2 == pytest.approx(3 * each ** 2 / (24 ** 2 + 3 * each ** 2) - 1.0) and avail2 < avail1


def test_model_a_adds_the_flag_to_v2s_columns():
    assert v3_shadow.A_COLUMNS == [*v2.A_COLUMNS, 'b2b_matchup'] and v3.STAR_POWER == 2.0


def test_on_a_neutral_site_model_a_loses_the_intercept_and_model_b_keeps_it():
    rng = np.random.default_rng(4)
    x = pd.DataFrame({'a': rng.normal(size=300)})
    y = (rng.random(300) < 1 / (1 + np.exp(-(0.4 + x['a'])))).astype(int)
    model = estimator().fit(x, y)
    one = x.iloc[[0]]
    z, b = float(model.decision_function(one)[0]), float(model[-1].intercept_[0])
    assert v3_shadow.forecast(model, one, True, drop_intercept=True) == pytest.approx(1 / (1 + np.exp(-(z - b))))
    assert v3_shadow.forecast(model, one, True, drop_intercept=False) == pytest.approx(1 / (1 + np.exp(-z)))


def test_the_record_names_v3s_own_registry_and_code():
    import inspect
    src = inspect.getsource(v3_shadow.save)
    assert "'registry': 'experiments/nba/stage105_v3/registry.json'" in src and 'power=v3.STAR_POWER' in src
    assert v3_shadow.CODE == 'nba-day-sport-v3' and v3.REGISTRY.exists()
