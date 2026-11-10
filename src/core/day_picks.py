"""A day sport's saved picks (Stage 87 item 2): saving each once, naming the games that started
without one, and grading them.

One copy for both day sports; src/sports/nhl/daily.py and src/sports/nba/daily.py re-export
these names, and tests/test_core_python.py fails if a copy comes back."""
from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pandas as pd

from src.core import (
    pick_guard,
)
from src.core.atomic_write import write_json_atomic
from src.core.sport import GameStatus


def save_once(record: dict[str, Any], folder: Path) -> bool:
    """Write the pick unless one is already saved. True when written.

    Stage 91 item 6: written through write_json_atomic (fsync, a unique
    temporary name), so a killed run never leaves a truncated pick or a
    committed .tmp. Stage 91 item 5: a record that could have seen its own
    result is refused before anything is written (src/core/pick_guard.py)."""
    path = folder / f"{record['game_id']}.json"
    if path.exists():
        return False
    pick_guard.refuse_leak(record)
    folder.mkdir(parents=True, exist_ok=True)
    write_json_atomic(path, record, trailing_newline=True, indent=1)
    return True


def missed(started: tuple[str, ...] | list[str], folder: Path) -> list[str]:
    """Games of this slate that have started with no pick saved for them.

    A pick is written once, before its game, so one of these can never be
    made now; the daily workflow raises an alert on the line main prints
    (Stage 68 item 3, the 2026-10-09 audit)."""
    return sorted(str(g) for g in started if not (folder / f'{g}.json').exists())


def missed_line(started: tuple[str, ...] | list[str], folder: Path) -> str | None:
    """The line the workflow's alert step greps for, or None when nothing
    was missed."""
    lost = missed(started, folder)
    return f'MISSED PICKS: {len(lost)} started with no saved pick: {", ".join(lost)}' if lost else None


def grade(folder: Path, sched: pd.DataFrame, extra: Sequence[str] = ()) -> list[dict[str, Any]]:
    """One row per saved pick: correct, wrong, cancelled, or pending.

    Pending also covers a final game whose result is not in yet (a null
    score, which used to raise here after the picks were saved, audit 7)
    and a pick whose game has left the schedule (Stage 96 item 44). `extra`
    names the pick fields a sport's rows carry between `result` and
    `saved_utc`: the NBA's carry market_source, the NHL's none."""
    by_id = sched.set_index('game_id')
    rows = []
    for path in sorted(folder.glob('*.json')) if folder.exists() else []:
        pick = json.loads(path.read_text(encoding='utf-8'))
        g = by_id.loc[pick['game_id']] if pick['game_id'] in by_id.index else None
        status = None if g is None else g['status']
        if status == GameStatus.CANCELLED.value:
            result = 'cancelled'
        elif status == GameStatus.FINAL.value and g is not None and not pd.isna(g['home_win']):
            winner = g['home'] if int(g['home_win']) == 1 else g['away']
            result = 'correct' if pick['pick'] == winner else 'wrong'
        else:
            result = 'pending'
        rows.append({'game_id': pick['game_id'], 'pick': pick['pick'], 'result': result,
                     **{k: pick.get(k) for k in extra}, 'saved_utc': pick.get('saved_utc')})
    return rows
