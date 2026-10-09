"""What the NBA's board reads that the picks themselves do not carry (Stage 65).

The daily run writes `results/nba/schedule_<season>.json` every run: every
game of the season as ESPN lists it now (date, start, clubs, status and,
once final, the score). The board shows each day's games from it,
including those whose pick is not saved yet. It is not a model output and
is rewritten every run; the page says as of when.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

SCHEDULE_FIELDS = ('game_id', 'slate', 'start_utc', 'home', 'away', 'status', 'game_type',
                   'home_score', 'away_score', 'neutral_site')


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


def write(path: Path, doc: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(doc, indent=1) + '\n', encoding='utf-8')
    tmp.replace(path)
    return path
