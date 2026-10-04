"""
simulate_season counts regular-season games only.

nflverse lists playoff games in the same schedule frame (game_type 'WC',
'DIV', 'CON', 'SB'). simulate_season had no filter, so once the playoffs
are scheduled an unplayed playoff game would be simulated like a week-19
regular-season game, and a finished one would add a win. Found building the
synthetic-league tests (#228). Today's data has no playoff rows: 48 played
and 224 remaining make 272, so this changes nothing yet. It matters from
January.

The invariants the simulation holds on a regular season are tested in
tests/test_pipeline_chain_end_to_end.py. Here the same regular-season
schedule is simulated with and without playoff rows added, and must come out
identical. The weekly job's odds file must count only regular-season games.

Run with: pytest tests/test_simulate_season.py -v
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

from src.pipeline import simulate_season as ss
from src.pipeline import weekly_update as wu

AFC_EAST = ['BUF', 'MIA', 'NE', 'NYJ']


class Model:
    """A fitted-model stand-in: slight home edge, ratings matter."""
    coef_ = np.array([[1.0, 1.0]])
    intercept_ = np.array([0.1])


def schedule():
    rows = []
    for week, (h, a) in enumerate([('BUF', 'MIA'), ('NE', 'NYJ'), ('MIA', 'NE'), ('NYJ', 'BUF')], 1):
        played = week <= 2
        rows.append({'season': 2026, 'week': week, 'game_type': 'REG', 'home_team': h, 'away_team': a,
                     'home_score': 24.0 if played else np.nan, 'away_score': 17.0 if played else np.nan})
    return pd.DataFrame(rows)


def with_playoffs(sched):
    post = pd.DataFrame([
        {'season': 2026, 'week': 19, 'game_type': 'WC', 'home_team': 'MIA', 'away_team': 'NE',
         'home_score': 30.0, 'away_score': 3.0},
        {'season': 2026, 'week': 20, 'game_type': 'DIV', 'home_team': 'NYJ', 'away_team': 'BUF',
         'home_score': np.nan, 'away_score': np.nan},
    ])
    return pd.concat([sched, post], ignore_index=True)


RATINGS = {'BUF': (0.2, 0.0), 'MIA': (0.1, 0.0), 'NE': (0.0, 0.1), 'NYJ': (-0.1, 0.1)}


def test_playoff_rows_change_nothing_in_the_simulation():
    plain = ss.simulate_season(RATINGS, schedule(), Model(), n_sim=500, seed=7)
    mixed = ss.simulate_season(RATINGS, with_playoffs(schedule()), Model(), n_sim=500, seed=7)
    pd.testing.assert_frame_equal(plain, mixed)


def test_regular_season_keeps_a_schedule_without_the_column():
    sched = schedule().drop(columns=['game_type'])
    assert len(ss.regular_season(sched)) == 4
    assert len(ss.regular_season(with_playoffs(schedule()))) == 4


def test_the_odds_file_counts_regular_season_games_only(tmp_path, monkeypatch):
    monkeypatch.setattr(wu, 'DATA_DIR', tmp_path)
    hist = pd.DataFrame({'off_matchup': [0.1, -0.1, 0.2, -0.2] * 5, 'def_matchup': [0.0, 0.1, -0.1, 0.0] * 5,
                         'home_win': [1, 0, 1, 0] * 5})
    wu.save_playoff_odds(RATINGS, with_playoffs(schedule()), hist, 2026, n_sim=100)
    odds = json.loads((tmp_path / 'playoff_odds.json').read_text())
    assert (odds['games_played'], odds['games_remaining']) == (2, 2)
