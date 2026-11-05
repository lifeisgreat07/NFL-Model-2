"""
Refuse a schedule that has shrunk from the one last committed.

Stage 91 item 2 (audit 7, 2026-11-04, finding R2). The NHL's and NBA's
schedule parsers refuse a malformed feed, but a feed answering 200 with no
games at all passes every contract: the one-sided check needs the other club
to list the game, and nobody lists any. Audit 7 injected exactly that into the
NHL's daily run: exit 0, schedule_2026.json written with 0 games, every grade
reset to pending, the forward test emptied, committed. Green and wrong.

A season's schedule does not lose games: a postponed game stays on it with
its status. So each day sport's daily run checks the fresh schedule against
`results/<sport>/schedule_<season>.json` before it writes anything, and stops
the run (whose failure alert fires) when the fresh one is empty or has lost
more than a few games. A season with no committed schedule yet (its first
run) is not checked. Standard library only.
"""
from __future__ import annotations

import json
from pathlib import Path

#: Games a fresh schedule may lack against the committed one before the run
#: stops: a few, for a league that drops a game outright, or 2% of the season.
ALLOWED_MIN = 5
ALLOWED_SHARE = 0.02


class ScheduleShrank(RuntimeError):
    """The fresh schedule is empty, or far smaller than the committed one."""


def committed_count(path: Path) -> int | None:
    """Games in the committed schedule file, or None when there is none yet."""
    if not path.exists():
        return None
    return len(json.loads(path.read_text(encoding='utf-8'))['games'])


def check(fresh: int, path: Path) -> None:
    """Raise unless `fresh` games is a plausible schedule beside the committed file at `path`."""
    if fresh == 0:
        raise ScheduleShrank(f'the schedule feed returned no games at all; {path.name} is left as it is')
    had = committed_count(path)
    if had is None:
        return
    allowed = max(ALLOWED_MIN, int(had * ALLOWED_SHARE))
    if fresh < had - allowed:
        raise ScheduleShrank(f'the schedule feed returned {fresh} games against {had} in {path.name} '
                             f'(more than {allowed} fewer); nothing is written')
