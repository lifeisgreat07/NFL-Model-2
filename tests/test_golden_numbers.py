"""Golden numbers: each day sport's Model A, fitted end to end on a fixed slice
of committed history, scores what it scored when this was written (Stage 96
item 41, audit 7 T3 and T4).

Every other model test runs on synthetic games and checks a property --
direction, no look-ahead, the right columns. None would notice the model
quietly scoring differently: a dependency that changes a default, a feature
computed a little differently, a refactor that moves a cut-off by a day. Here
the registered pipeline (the half-life and K or lambda the live run reads,
the features, the walk-forward refits) runs on the last 200 games of 2023-24
and the first 100 of 2024-25 from the committed history files, and its log
loss and Brier on those 100 games must match to four decimals.

The numbers were produced on 2026-11-05 with pandas 1.5.3, NumPy 1.26.4 and
the scikit-learn in requirements.txt. A change that moves them is either a
bug or a deliberate change to the model; either way it is a decision, and the
numbers are updated here with the reason in the commit.

Run with: pytest tests/test_golden_numbers.py -v
"""
import pandas as pd
import pytest

from src.sports.nba import backtest as nba_bt
from src.sports.nba import daily as nba_daily
from src.sports.nba import ratings as nba_r
from src.sports.nhl import backtest as nhl_bt
from src.sports.nhl import daily as nhl_daily
from src.sports.nhl import ratings as nhl_r

GOLDEN = {
    'nhl': {'games': 100, 'log_loss': 0.7045, 'brier': 0.2548},
    'nba': {'games': 100, 'log_loss': 0.6609, 'brier': 0.2352},
}


def slice_of(frame):
    return pd.concat([frame[frame['season'] == 2023].tail(200), frame[frame['season'] == 2024].head(100)])


def nhl_scores():
    h, k = nhl_daily.chosen()
    g = nhl_r.prepare(slice_of(nhl_bt.load_history(2023, 2024)))
    t = nhl_r.features(g, h, [k]).merge(g[['game_id', 'home_prob']], on='game_id', how='left')
    p = nhl_bt.walk_forward(t, ['goal_matchup', 'shot_matchup', nhl_bt.goalie_column(k)], [2024])
    return nhl_bt.scores(p, t)


def nba_scores():
    h, lam = nba_daily.chosen()
    games, minutes = nba_bt.load_history(2023, 2024)
    games = slice_of(games)
    minutes = minutes[minutes['game_id'].isin(set(games['game_id']))]
    games = nba_r.prepare(games)
    t = nba_r.features(games, minutes, h, lam, avail=nba_r.availability_table(games, minutes, h))
    p = nba_bt.walk_forward(t, list(nba_bt.A_COLUMNS), [2024])
    return nba_bt.scores(p, t)


@pytest.mark.parametrize('sport, run', [('nhl', nhl_scores), ('nba', nba_scores)])
def test_model_a_scores_its_golden_numbers(sport, run):
    got = run()
    want = GOLDEN[sport]
    assert got['games'] == want['games']
    assert got['log_loss'] == pytest.approx(want['log_loss'], abs=5e-5), got
    assert got['brier'] == pytest.approx(want['brier'], abs=5e-5), got


def test_the_registered_constants_are_the_ones_the_numbers_were_made_with():
    assert nhl_daily.chosen() == (120.0, 2000.0)
    assert nba_daily.chosen() == (120.0, 10.0)
