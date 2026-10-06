"""The NBA's committed history (`data/nba/history/`), held to what the
registration and `src/sports/nba/history.py` say it is.

Run with: pytest tests/test_nba_history_data.py -v
"""
import re
from pathlib import Path

import pandas as pd
import pytest

from src.sports.nba import backtest, history

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'data' / 'nba' / 'history'
REG = backtest.registry()
SEASONS = range(REG['protocol']['training_from_season'], REG['protocol']['confirmation_seasons'][-1] + 1)


def games(season):
    return pd.read_csv(FOLDER / f'games_{season}.csv', dtype={'game_id': str})


def minutes(season):
    return pd.read_csv(FOLDER / f'minutes_{season}.csv', dtype={'game_id': str, 'player_id': str})


def market(season):
    return pd.read_csv(FOLDER / f'market_{season}.csv', dtype={'game_id': str})


@pytest.mark.parametrize('season', SEASONS)
def test_every_registered_season_has_its_four_files(season):
    for name in ('games', 'minutes', 'market', 'skipped'):
        assert (FOLDER / f'{name}_{season}.csv').exists(), f'{name}_{season}.csv'


@pytest.mark.parametrize('season', SEASONS)
def test_each_season_holds_only_registered_games_once_each(season):
    g = games(season)
    assert list(g.columns) == list(history.GAME_FIELDS)
    assert g['game_id'].is_unique
    assert set(g['game_type']) <= set(backtest.GAME_TYPES)
    assert (g['season'] == season).all()
    assert (g['home_score'] != g['away_score']).all()
    assert set(g['box_source']) <= {'espn', 'hoopr'}


@pytest.mark.parametrize('season', SEASONS)
def test_possessions_are_the_registered_formula(season):
    g = games(season)
    def one(side: str) -> pd.Series:
        return g[f'{side}_fga'] + history.FTA_WEIGHT * g[f'{side}_fta'] - g[f'{side}_oreb'] + g[f'{side}_tov']
    assert ((one('home') + one('away')) / 2).round(2).equals(g['possessions'].round(2))
    # 70 to 160: the 2019-03-01 game Chicago won 168-161 in four overtimes reached 146.
    assert g['possessions'].between(70, 160).all()


@pytest.mark.parametrize('season', SEASONS)
def test_every_game_has_players_with_minutes_for_both_teams(season):
    g, m = games(season), minutes(season)
    played = m[m['minutes'] > 0].groupby('game_id')['team'].nunique()
    assert set(g['game_id']) <= set(played[played == 2].index)
    # a regulation game is 240 team minutes; overtime adds 25 a period
    per_team = m.groupby(['game_id', 'team'])['minutes'].sum()
    assert per_team.between(235, 400).mean() > 0.99


@pytest.mark.parametrize('season', SEASONS)
def test_the_market_is_two_way_with_the_margin_out_and_never_live(season):
    k = market(season)
    assert not k['provider'].str.contains('live', case=False).any()
    assert ((k['home_price'].abs() >= 100) & (k['away_price'].abs() >= 100)).all()
    assert k['home_prob'].between(0, 1, inclusive='neither').all()
    assert k['game_id'].is_unique


def test_the_empty_espn_box_scores_came_from_the_fallback_and_eight_games_are_named():
    from_fallback = {s: int((games(s)['box_source'] == 'hoopr').sum()) for s in SEASONS}
    assert from_fallback[2015] == 161 and from_fallback[2016] == 167 and from_fallback[2017] == 171
    assert sum(v for s, v in from_fallback.items() if s > 2017) == 0
    skipped = sum(len(pd.read_csv(FOLDER / f'skipped_{s}.csv')) for s in SEASONS)
    assert skipped == 8


def test_the_coverage_table_in_the_data_document_is_the_history_s():
    """docs/nba-data.md prints, per season, the games the history holds, how
    many have a price and how many a closing price; each row must be what the
    committed files say."""
    doc = (ROOT / 'docs' / 'nba-data.md').read_text(encoding='utf-8')
    rows = {int(y): (int(n), int(p), int(c)) for y, n, p, c in
            re.findall(r'^\| (\d{4})-\d\d \| (\d+) \| (\d+) \| (\d+) \|$', doc, re.M)}
    assert set(rows) == set(SEASONS)
    for s in SEASONS:
        g, k = games(s), market(s)
        priced = g['game_id'].isin(k['game_id'])
        closing = g['game_id'].isin(k.loc[k['closing'], 'game_id'])
        assert rows[s] == (len(g), int(priced.sum()), int(closing.sum())), s
