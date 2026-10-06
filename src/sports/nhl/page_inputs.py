"""What the NHL's pages read that the picks themselves do not carry (Stage 57).

The daily run writes two files each run, beside the grades:

- `results/nhl/schedule_<season>.json`: every game of the season, as the
  league lists it now (date, start, clubs, status and, once final, the
  score and how it ended). The board shows the week's games by day,
  including those whose pick is not saved yet.
- `results/nhl/ratings_<season>.json`: the ratings Model A reads, as they
  stand before today: each club's goal and shot ratings and the goalie
  rating of every goalie who has started this season or last, with his
  name where a saved pick has named him.

Neither is a model output that is graded, and both are rewritten every
run: they describe today, and a page that shows them says as of when.
"""
from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from src.sports.nhl import ratings

SCHEDULE_FIELDS = ('game_id', 'slate', 'start_utc', 'home', 'away', 'status', 'game_type',
                   'home_score', 'away_score', 'last_period', 'neutral_site')


def _plain(value: Any) -> Any:
    if value is None or (isinstance(value, float) and pd.isna(value)) or value is pd.NA:
        return None
    if isinstance(value, pd.Timestamp):
        return value.strftime('%Y-%m-%dT%H:%M:%SZ')
    if hasattr(value, 'item'):
        return value.item()
    return value


def schedule_json(sched: pd.DataFrame, as_of: str) -> dict[str, Any]:
    rows = [{f: _plain(g.get(f)) for f in SCHEDULE_FIELDS} for g in sched.to_dict('records')]
    return {'as_of': as_of, 'games': rows}


def goalie_names(picks: Iterable[Mapping[str, Any]]) -> dict[str, str]:
    """Each goalie's name by league id, from the goalies saved picks named."""
    out: dict[str, str] = {}
    for p in picks:
        for side in ((p.get('goalies') or {}).get('home'), (p.get('goalies') or {}).get('away')):
            if side and side.get('player_id') is not None and side.get('name'):
                out[str(side['player_id'])] = str(side['name'])
    return out


def ratings_json(rated: ratings.DayRatings, k: float, clubs: Iterable[str], recent_goalies: Iterable[Any],
                 names: Mapping[str, str], as_of: str) -> dict[str, Any]:
    """Clubs by franchise, best first by goal rating; goalies with any shots
    this season or last, best first."""
    teams: list[dict[str, Any]] = []
    for club in sorted(set(clubs)):
        f = ratings.franchise(club)
        teams.append({'team': club, 'goal': round(rated.goal.get(f, 0.0), 4), 'shot': round(rated.shot.get(f, 0.0), 4)})
    teams.sort(key=lambda t: (-float(t['goal']), str(t['team'])))
    goalies: list[dict[str, Any]] = []
    for gid in sorted({str(g) for g in recent_goalies}):
        key = next((x for x in rated.goalies.index if str(x) == gid), None)
        if key is None:
            continue
        shots = float(rated.goalies.loc[key, 'shots'])
        goalies.append({'player_id': gid, 'name': names.get(gid), 'rating': round(ratings.goalie_rating(rated.goalies, key, k), 5),
                        'weighted_shots': round(shots, 1)})
    goalies.sort(key=lambda g: (-float(g['rating']), str(g['player_id'])))
    return {'as_of': as_of, 'K_shots': k, 'teams': teams, 'goalies': goalies}


def write(path: Path, doc: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(doc, indent=1) + '\n', encoding='utf-8')
    tmp.replace(path)
    return path
