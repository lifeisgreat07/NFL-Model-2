"""What the NBA's board reads that the picks themselves do not carry (Stage 65).

The daily run writes `results/nba/schedule_<season>.json` every run: every
game of the season as ESPN lists it now (date, start, clubs, status and,
once final, the score). The board shows each day's games from it,
including those whose pick is not saved yet. It is not a model output and
is rewritten every run; the page says as of when.

Since Stage 104 item 3 it also writes `results/nba/ratings_<season>.json`:
each club's point and efficiency ratings as they stand before the run's
day, the two Model A reads, for the Power Ratings and Teams pages.
"""
from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pandas as pd

from src.sports.nba import ratings

SCHEDULE_FIELDS = ('game_id', 'slate', 'start_utc', 'home', 'away', 'status', 'game_type',
                   'home_score', 'away_score', 'neutral_site', 'time_valid')


def _plain(value: Any) -> Any:
    if value is None or value is pd.NA or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, pd.Timestamp):
        return value.strftime('%Y-%m-%dT%H:%M:%SZ')
    if hasattr(value, 'item'):
        return value.item()
    return value


def schedule_json(sched: pd.DataFrame, as_of: str) -> dict[str, Any]:
    rows = [{f: _plain(g.get(f)) for f in SCHEDULE_FIELDS} for g in sched.to_dict('records')]
    return {'as_of': as_of, 'games': rows}



def ratings_json(rated: ratings.DayRatings, clubs: Iterable[str], as_of: str) -> dict[str, Any]:
    """Every club, best first by point rating: points a game better than an
    average club, and the same per 100 possessions (Stage 104 item 3)."""
    teams: list[dict[str, Any]] = [
        {'team': c, 'point': round(rated.point.get(c, 0.0), 4), 'efficiency': round(rated.efficiency.get(c, 0.0), 4)}
        for c in sorted(set(clubs))]
    teams.sort(key=lambda t: (-float(t['point']), str(t['team'])))
    return {'as_of': as_of, 'teams': teams}


def write(path: Path, doc: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(doc, indent=1) + '\n', encoding='utf-8')
    tmp.replace(path)
    return path
