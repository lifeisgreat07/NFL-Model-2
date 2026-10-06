"""The NBA's Model A features and its Stage 61 backtest (src/sports/nba/ratings.py,
src/sports/nba/backtest.py), on small synthetic seasons."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.sports.nba import backtest, ratings

TEAMS = [f'T{i:02d}' for i in range(8)]


def synthetic(seasons: tuple[int, ...] = (2020, 2021), days: int = 60, seed: int = 3) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    strength = {t: s for t, s in zip(TEAMS, np.linspace(-8, 8, len(TEAMS)))}
    games, minutes, gid = [], [], 0
    for season in seasons:
        start = pd.Timestamp(f'{season}-10-20')
        for k in range(days):
            day = start + pd.Timedelta(days=k)
            order = rng.permutation(TEAMS)
            for i in range(0, len(TEAMS), 2):
                home, away = str(order[i]), str(order[i + 1])
                gid += 1
                margin = strength[home] - strength[away] + 2 + rng.normal(0, 10)
                hs, aws = 110 + int(round(margin / 2)), 110 - int(round(margin / 2))
                hs += hs == aws
                games.append({'game_id': str(gid), 'slate': str(day.date()), 'season': season,
                              'game_type': 'regular', 'home': home, 'away': away, 'home_score': hs,
                              'away_score': aws, 'possessions': 98.0 + rng.normal(0, 3),
                              'home_prob': 1 / (1 + np.exp(-(strength[home] - strength[away] + 2) / 9))})
                for team in (home, away):
                    for p in range(8):
                        mins = float(rng.integers(5, 40)) if rng.random() < 0.9 else 0.0
                        minutes.append({'game_id': str(gid), 'team': team, 'player_id': f'{team}-{p}', 'minutes': mins})
    return ratings.prepare(pd.DataFrame(games)), pd.DataFrame(minutes)


def test_prepare_adds_the_margins_and_the_outcome() -> None:
    raw = pd.DataFrame([{'game_id': 7, 'slate': '2024-01-02', 'season': 2023, 'game_type': 'regular', 'home': 'BOS',
                         'away': 'NY', 'home_score': 110, 'away_score': 100, 'possessions': 100.0}])
    g = ratings.prepare(raw).iloc[0]
    assert g['game_id'] == '7' and g['point_margin'] == 10 and g['efficiency_margin'] == pytest.approx(10.0)
    assert g['home_win'] == 1 and g['day'] == pd.Timestamp('2024-01-02')


def test_the_point_ratings_order_the_teams_by_strength() -> None:
    games, _ = synthetic(seasons=(2020,), days=80)
    w = ratings.weights(games['day'], games['day'].max() + pd.Timedelta(days=1), 60.0)
    edge, rating = ratings.ridge_ratings(games, 'point_margin', w, 1.0)
    assert rating['T07'] > rating['T00']
    assert 0 < edge < 5


def test_the_ridge_penalty_falls_on_the_teams_only() -> None:
    games, _ = synthetic(seasons=(2020,), days=40)
    w = np.ones(len(games))
    edge_small, small = ratings.ridge_ratings(games, 'point_margin', w, 0.01)
    edge_big, big = ratings.ridge_ratings(games, 'point_margin', w, 1e6)
    assert max(abs(v) for v in big.values()) < 0.01 < max(abs(v) for v in small.values())
    # with the team terms shrunk to zero, the home term is the mean margin, unpenalised
    assert edge_big == pytest.approx(games['point_margin'].mean(), abs=1e-3)


def test_availability_is_the_share_of_expected_minutes_that_plays() -> None:
    expected = {'a': 30.0, 'b': 20.0, 'c': 10.0}
    assert ratings.availability(expected, {'a', 'b', 'c'}) == pytest.approx(1.0)
    assert ratings.availability(expected, {'b', 'c'}) == pytest.approx(0.5)
    assert ratings.availability({}, set()) == 1.0


def test_the_one_pass_availability_matches_the_registered_formula() -> None:
    games, minutes = synthetic(seasons=(2020,), days=30)
    fast = ratings.availability_table(games, minutes, 30.0)
    m = minutes.assign(game_id=minutes['game_id'].astype(str), player_id=minutes['player_id'].astype(str))
    day_of = dict(zip(games['game_id'], games['day']))
    played = m[m['minutes'] > 0].groupby(['game_id', 'team'])['player_id'].apply(set).to_dict()
    for g in games.itertuples():
        sides = [ratings.availability(ratings.expected_minutes(m, day_of, team, g.day, 30.0),
                                      played.get((g.game_id, team), set())) for team in (g.home, g.away)]
        assert fast[g.game_id] == pytest.approx(sides[0] - sides[1], abs=1e-12)


def test_a_team_missing_its_main_player_is_less_available() -> None:
    games, minutes = synthetic(seasons=(2020,), days=30)
    last = games.iloc[-1]
    star = minutes[(minutes['team'] == last['home'])].groupby('player_id')['minutes'].sum().idxmax()
    before = ratings.availability_table(games, minutes, 30.0)[last['game_id']]
    out = minutes.copy()
    out.loc[(out['game_id'] == last['game_id']) & (out['player_id'] == star), 'minutes'] = 0.0
    after = ratings.availability_table(games, out, 30.0)[last['game_id']]
    assert after < before


def test_a_games_features_use_only_earlier_days() -> None:
    games, minutes = synthetic(seasons=(2020,), days=40)
    first = ratings.features(games, minutes, 60.0, 1.0)
    cut = games['day'].iloc[len(games) // 2]
    later = games['day'] >= cut
    changed = games.copy()
    changed.loc[later, 'home_score'] += 40
    changed['point_margin'] = (changed['home_score'] - changed['away_score']).astype(float)
    changed['efficiency_margin'] = 100.0 * changed['point_margin'] / changed['possessions']
    out_minutes = minutes.copy()
    out_minutes.loc[out_minutes['game_id'].isin(games.loc[later, 'game_id']), 'minutes'] = 0.0
    second = ratings.features(changed, out_minutes, 60.0, 1.0)
    cols = ['point_matchup', 'efficiency_matchup']
    a = first[first['day'] <= cut].set_index('game_id')[cols]
    b = second[second['day'] <= cut].set_index('game_id')[cols]
    pd.testing.assert_frame_equal(a, b)
    avail_a = first[first['day'] < cut].set_index('game_id')['availability_matchup']
    avail_b = second[second['day'] < cut].set_index('game_id')['availability_matchup']
    pd.testing.assert_series_equal(avail_a, avail_b)


def test_the_first_days_are_not_rated_until_there_are_enough_games() -> None:
    games, minutes = synthetic(seasons=(2020,), days=40)
    table = ratings.features(games, minutes, 60.0, 1.0)
    first_rated = table['day'].min()
    assert (games['day'] < first_rated).sum() >= ratings.MIN_TRAIN
    assert len(games[games['day'] < first_rated]) - len(games[games['day'] < first_rated - pd.Timedelta(days=1)]) > 0


def test_the_label_follows_the_registered_rule() -> None:
    assert backtest.label({'low': -0.02, 'high': -0.001}) == 'ACCEPT'
    assert backtest.label({'low': 0.001, 'high': 0.02}) == 'REJECT'
    assert backtest.label({'low': -0.01, 'high': 0.01}) == 'INCONCLUSIVE'


def test_the_interval_resamples_whole_days_and_is_seeded() -> None:
    games, _ = synthetic(seasons=(2020,), days=20)
    a = pd.Series(0.6, index=games['game_id'])
    b = pd.Series(0.5, index=games['game_id'])
    one = backtest.day_block_interval(a, b, games, 0.9833, n=500)
    two = backtest.day_block_interval(a, b, games, 0.9833, n=500)
    assert one == two
    assert one['days'] == games['day'].nunique() and one['games'] == len(games)
    assert backtest.SEED == 20261006


def test_model_b_trains_and_predicts_only_games_with_a_price() -> None:
    games, minutes = synthetic(seasons=(2020, 2021), days=30)
    table = backtest._table(games, minutes, 60.0, 1.0)
    table.loc[table.index % 3 == 0, 'home_prob'] = np.nan
    table['market_logit'] = np.log(table['home_prob'] / (1 - table['home_prob']))
    p = backtest.walk_forward(table, [*backtest.A_COLUMNS, 'market_logit'], [2021], needs_market=True)
    priced = set(table.loc[table['home_prob'].notna() & (table['season'] == 2021), 'game_id'])
    assert set(p.index) == priced


def test_the_base_rate_is_the_home_share_of_earlier_days() -> None:
    games, _ = synthetic(seasons=(2020, 2021), days=20)
    p = backtest.base_rate(games, [2021])
    g = games[games['season'] == 2021].iloc[0]
    assert p[g['game_id']] == pytest.approx(games.loc[games['day'] < g['day'], 'home_win'].mean())


def test_tuning_never_reads_a_game_after_the_validation_seasons(monkeypatch: pytest.MonkeyPatch) -> None:
    games, minutes = synthetic(seasons=(2020, 2021, 2022), days=40)
    seen: list[int] = []
    real = ratings.features

    def spy(g: pd.DataFrame, *args: object, **kwargs: object) -> pd.DataFrame:
        seen.append(int(g['season'].max()))
        return real(g, *args, **kwargs)  # type: ignore[arg-type]
    monkeypatch.setattr(ratings, 'features', spy)
    reg = {'models': {'model_a': {'grid': {'H_days': [60], 'lambda': [1.0, 3.0]}}},
           'protocol': {'validation_seasons': [2021], 'confirmation_seasons': [2022]}}
    out = backtest.tune(games, minutes, reg)
    assert seen and max(seen) == 2021
    assert out['chosen']['lambda'] in (1.0, 3.0) and len(out['grid']) == 2


def test_confirmation_answers_each_question_with_its_label() -> None:
    games, minutes = synthetic(seasons=(2020, 2021), days=30)
    reg = {'protocol': {'confirmation_seasons': [2021], 'alpha': 0.05, 'budget_m': 3}}
    out = backtest.confirm(games, minutes, reg, 60.0, 1.0)
    assert set(out['questions']) == {'H1', 'H2', 'H3', 'M1'}
    assert all('label' in q for k, q in out['questions'].items() if k != 'M1')
    assert 'label' not in out['questions']['M1']
    assert out['questions']['H1']['level'] == 0.9833
    assert out['questions']['M1']['incumbent'] == 'model_a_no_availability'


def test_the_history_is_read_with_its_market_and_only_registered_game_types(tmp_path: Path) -> None:
    games = pd.DataFrame([
        {'game_id': '1', 'slate': '2024-10-22', 'season': 2024, 'game_type': 'regular', 'home': 'BOS', 'away': 'NY',
         'home_score': 110, 'away_score': 100, 'possessions': 99.0},
        {'game_id': '2', 'slate': '2025-02-16', 'season': 2024, 'game_type': 'allstar', 'home': 'EST', 'away': 'WST',
         'home_score': 180, 'away_score': 170, 'possessions': 120.0},
    ])
    games.to_csv(tmp_path / 'games_2024.csv', index=False)
    pd.DataFrame([{'game_id': '1', 'team': 'BOS', 'player_id': '9', 'minutes': 30.0}]).to_csv(
        tmp_path / 'minutes_2024.csv', index=False)
    pd.DataFrame([{'game_id': '1', 'home_prob': 0.7}]).to_csv(tmp_path / 'market_2024.csv', index=False)
    g, m = backtest.load_history(2024, 2024, tmp_path)
    assert list(g['game_id']) == ['1'] and g['home_prob'].iloc[0] == 0.7
    assert m['player_id'].iloc[0] == '9'
