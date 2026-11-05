"""
The ratings snapshot is the latest week of its history.

Stage 86 item 5 (the 2026-11-02 review). Each weekly run writes
data/nfl/current_ratings.json (the snapshot, overwritten) and appends the same
ratings to data/nfl/team_history_<season>.json (one point per team per week,
never overwritten). Power Ratings' rank change rests on the latest history
week being that snapshot (generate_dashboard.previous_ranks). Until now only a
test over the committed files checked it, so a run that broke it was found at
the next suite run, if at all. `check` is now a postcondition of the run that
writes both: a mismatch prints a DEGRADED line, and the Weekly update raises
an issue on it. It does not stop the run: reporting must never cost a pick.

Standard library only.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

#: How far a snapshot rating may sit from the history's latest week and still be the same week. Both are
#: rounded to four decimals, and the Thursday run recomputes the snapshot, so a rating can land on the other
#: side of a rounding step (WAS -0.073 in the history, -0.0731 in the snapshot, 2026-10-29) and the rank
#: change disappeared from the page for days. One step is 0.0001; a different week moves ratings by far more.
TOL = 1.5e-4

#: What the run prints when the check passed (or had nothing to check): the
#: workflow closes an open alert on it, and only on it, so a run that never
#: reached the check closes nothing.
OK = 'RATINGS SNAPSHOT OK: data/nfl/current_ratings.json is the latest week of its history (or there is none yet)'


def mismatches(ratings: list[dict[str, Any]], history: dict[str, list[dict[str, Any]]]) -> list[str]:
    """Each team whose snapshot net rating is not the history's latest week's, within TOL."""
    weeks = {p['week'] for points in history.values() for p in points}
    if not weeks:
        return ['the season history has no week']
    latest = max(weeks)
    out = []
    for r in ratings:
        point = [p for p in history.get(r['team'], []) if p['week'] == latest]
        if not point:
            out.append(f"{r['team']}: not in week {latest} of the history")
        elif abs(point[0]['net'] - r['net']) > TOL:
            out.append(f"{r['team']}: {r['net']} in the snapshot, {point[0]['net']} in week {latest}")
    return out


def check(data_dir: Path, season: int) -> list[str]:
    """The DEGRADED lines for this season's files, or [] when they agree. A
    season with no history file yet (no completed week) has nothing to check."""
    history_path = data_dir / f'team_history_{season}.json'
    if not history_path.exists():
        return []
    ratings = json.loads((data_dir / 'current_ratings.json').read_text(encoding='utf-8'))
    history = json.loads(history_path.read_text(encoding='utf-8'))
    found = mismatches(ratings, history)
    if not found:
        return []
    return [f'DEGRADED: ratings snapshot: data/nfl/current_ratings.json is not the latest week of '
            f'data/nfl/team_history_{season}.json, so Power Ratings shows no rank change: '
            + '; '.join(found[:8]) + (f'; and {len(found) - 8} more' if len(found) > 8 else '')]
