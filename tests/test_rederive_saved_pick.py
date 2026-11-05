"""Stage 85 item 6 (the 2026-11-02 review): one saved pick per day sport is
re-derived from committed data with the registered walk-forward, outside the
daily run's code path.

For each sport: rebuild the feature table from the committed history with the
backtest's own functions and the settings validation chose, fit the backtest's
estimator on every row before the pick's slate day (Stage 85 item 4: strictly
before), and apply it to the features the pick stored. Model A must come back
to the saved probability within 5e-4 (it is saved to four places), and the training record (last day, games,
priced games) must be the pick's own.

Both picks were saved before this season's recorded prices reached the
training rows (Stage 85 item 5), so this season's games enter unpriced here,
as they did in the run that saved them. Model A does not read the price; only
the priced count depends on it.

These are postconditions over committed data, so a history file rewritten
under a saved pick fails here. Each sport takes about half a minute.

Run with: pytest tests/test_rederive_saved_pick.py -v
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.core.provenance import training

ROOT = Path(__file__).resolve().parents[1]

# A saved pick each, chosen as the first game of a recent slate whose pick has
# its training record and availability, and is not among the disclosed
# same-day fits (the registries' `deviation` amendments).
NHL_PICK = '2026020227'   # slate 2026-11-01
NBA_PICK = '401909926'    # slate 2026-11-04


def saved(sport, game_id):
    return json.loads((ROOT / 'predictions' / sport / '2026' / f'{game_id}.json').read_text(encoding='utf-8'))


def disclosed(live_registry):
    """The picks the live registration's `deviation` amendment lists as fitted
    on games of their own slate day."""
    reg = json.loads((ROOT / 'experiments' / live_registry / 'registry.json').read_text(encoding='utf-8'))
    (dev,) = [a for a in reg['amendments'] if a['entry'] == 'deviation']
    assert dev['picks'], 'the deviation amendment lists its picks'
    return set(dev['picks'])


def refit(table, cols, estimator, pick, first):
    before = table[pd.to_datetime(table['day']) < pd.Timestamp(pick['slate'])]
    model = estimator().fit(before[cols], before['home_win'])
    p = float(model.predict_proba(pd.DataFrame([pick['features']])[cols])[0, 1])
    return p, training(before, first)


#: The saved probability is rounded to four places, and audit 7 saw two picks re-derive
#: 0.0002 away in another environment; a model that differs in substance misses by far more.
TOLERANCE = 5e-4


def check(pick, got, record):
    assert abs(pick['model_a'] - got) <= TOLERANCE, f"{pick['game_id']}: re-derived {got:.6f}, saved {pick['model_a']}"
    assert record == {'training_through': pick['training_through'], 'data_provenance': pick['data_provenance']}


@pytest.mark.slow
def test_an_nhl_saved_pick_is_re_derived_by_the_registered_walk_forward(monkeypatch):
    monkeypatch.chdir(ROOT)
    from src.sports.nhl import backtest, daily, ratings
    pick = saved('nhl', NHL_PICK)
    assert NHL_PICK not in disclosed('nhl/stage58')
    first = backtest.registry()['protocol']['training_from_season']
    current = pd.read_csv(ROOT / 'data' / 'nhl' / 'history' / 'boxscores_2026.csv', dtype={'game_id': str})
    games = ratings.prepare(pd.concat([backtest.load_history(first, 2025), current.assign(home_prob=np.nan)],
                                      ignore_index=True))
    h, k = daily.chosen()
    table = ratings.features(games, h, [k]).merge(games[['game_id', 'home_prob']], on='game_id', how='left')
    cols = ['goal_matchup', 'shot_matchup', backtest.goalie_column(k)]
    got, record = refit(table, cols, backtest.estimator, pick, first)
    check(pick, got, record)


@pytest.mark.slow
def test_an_nba_saved_pick_is_re_derived_by_the_registered_walk_forward(monkeypatch):
    monkeypatch.chdir(ROOT)
    from src.sports.nba import backtest, daily, ratings
    pick = saved('nba', NBA_PICK)
    assert (pick.get('availability') or {}).get('read'), 'the pick used availability, so its fit had the term'
    assert NBA_PICK not in disclosed('nba/stage65')
    first = backtest.registry()['protocol']['training_from_season']
    past_games, past_minutes = backtest.load_history(first, 2025)
    hist = ROOT / 'data' / 'nba' / 'history'
    cur_games = pd.read_csv(hist / 'games_2026.csv', dtype={'game_id': str}).assign(home_prob=np.nan)
    cur_minutes = pd.read_csv(hist / 'minutes_2026.csv', dtype={'game_id': str, 'player_id': str})
    games = ratings.prepare(pd.concat([past_games, cur_games], ignore_index=True))
    minutes = pd.concat([past_minutes, cur_minutes], ignore_index=True)
    minutes = minutes.assign(game_id=minutes['game_id'].astype(str), player_id=minutes['player_id'].astype(str))
    h, lam = daily.chosen()
    table = ratings.features(games, minutes, h, lam, avail=ratings.availability_table(games, minutes, h))
    table = table.merge(games[['game_id', 'home_prob']], on='game_id', how='left')
    got, record = refit(table, list(daily.A_COLUMNS), backtest.estimator, pick, first)
    check(pick, got, record)
