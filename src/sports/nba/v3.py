"""The NBA's v3 (experiments/nba/stage105_v3/registry.json): v2 plus the back-to-back flag and star-weighted
availability, as a shadow.

- `b2b_matchup` = (1 if the away team played on the previous slate date, else 0) minus (the same for the home team),
  on the US Eastern slate dates, from the schedule only. A team's first game of a season is 0.
- Star-weighted availability: v2's availability share (item 24), each player weighted by his expected minutes
  squared (`STAR_POWER`, fixed by the registration, not tuned), in place of v2's term.

Everything else is v2's (src/sports/nba/v2.py): the history and its rules, the tuned H and lambda (not re-tuned),
the estimator and refit rule. Neutral site: Model A's forecast loses the fitted intercept, as v2's; Model B's keeps
it, because its market price already carries the site (audit 8, finding S1).
"""
from __future__ import annotations

import pandas as pd

from src.core.sport import sport_paths

PATHS = sport_paths('nba')
FOLDER = PATHS.experiments / 'stage105_v3'
REGISTRY = FOLDER / 'registry.json'
B2B = 'b2b_matchup'
STAR_POWER = 2.0


def played_days(games: pd.DataFrame) -> set[tuple[str, pd.Timestamp]]:
    """(club, date) for every club in every game of `games` (columns `day`, `home`, `away`)."""
    days = pd.to_datetime(games['day']).dt.normalize()
    return {(str(t), d) for col in ('home', 'away') for t, d in zip(games[col], days)}


def b2b_matchup(rows: pd.DataFrame, played: set[tuple[str, pd.Timestamp]]) -> pd.Series:
    """The away club's back-to-back flag minus the home club's, for each row (columns `day`, `home`, `away`)."""
    before = pd.to_datetime(rows['day']).dt.normalize() - pd.Timedelta(days=1)
    away = [int((str(t), d) in played) for t, d in zip(rows['away'], before)]
    home = [int((str(t), d) in played) for t, d in zip(rows['home'], before)]
    return pd.Series([a - h for a, h in zip(away, home)], index=rows.index, name=B2B, dtype=float)


def model_a_columns(v2_columns: list[str]) -> list[str]:
    """v2's Model A columns (its availability term now star-weighted) plus the flag."""
    return [*v2_columns, B2B]
