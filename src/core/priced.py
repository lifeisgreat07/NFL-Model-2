"""
Say so when a slate is locked with no price at all.

Stage 92 item 7 (audit 7, 2026-11-04, finding R4). A day sport's run reports
an odds feed that fails to answer (DEGRADED, which raises an issue), but a
feed that answers with an empty games list, or renames its top-level key,
reads as "no game has a price yet": every pick is saved by Model A with no
market, and nothing is said. Audit 7 injected both into the NHL's run and an
NBA odds payload with renamed keys: every pick unpriced, no DEGRADED line.

`unpriced_line` is the line each run prints when it is locking games and the
feed priced none of them. A slate where some games are priced and some are
not is normal (a late line), and says nothing here. Standard library only.
"""
from __future__ import annotations

from collections.abc import Iterable


def unpriced_line(locking: Iterable[str], priced: Iterable[str]) -> str | None:
    """The DEGRADED line when games are locking and none of them has a price, else None."""
    lock = {str(g) for g in locking}
    if not lock or lock & {str(g) for g in priced}:
        return None
    return (f'DEGRADED: odds feed: priced none of the {len(lock)} games locking; '
            'every pick made without a price (an empty or changed payload reads as no prices)')
