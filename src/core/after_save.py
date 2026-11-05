"""
Steps that run after a day sport's picks are saved must not lose them.

Stage 91 item 3 (audit 7, 2026-11-04, finding R3). The NHL's and NBA's daily
runs save a slate's picks and then go on to the standings, grading, the page
inputs, the drift check, the forward test and M2. Audit 7 made each of those
raise on a real input (a final game with no score, an unknown team code, a
duplicated game id): the picks were on disk, the run exited non-zero, the
workflow's commit step was skipped, and the slate lived only in the run's
artifact until someone committed it by hand, the 2026-10-10 incident (#423,
#424) moved one step later.

`guarded` runs one such step and, if it raises, prints
`DEGRADED: <step>: <error>` and carries on, so the run still commits the
picks; the workflow raises an issue on every DEGRADED line (Stage 83 item 4),
so the failure is still reported, now beside saved picks instead of instead
of them. Use it only for steps after the picks are saved: a failure before
them should still stop the run.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar('T')


def guarded(step: str, fn: Callable[..., T], *args: Any, **kwargs: Any) -> T | None:
    """fn(*args, **kwargs), or None after printing a DEGRADED line when it raises."""
    try:
        return fn(*args, **kwargs)
    except Exception as exc:  # any failure here must not cost the saved picks
        print(f'DEGRADED: {step}: {type(exc).__name__}: {exc}')
        return None
