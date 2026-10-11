"""Which league player a projected goalie is.

Daily Faceoff names a goalie ("Andrei Vasilevskiy"); the box scores, and so
the goalie ratings, know him by the league's player id. The daily run
(`src/sports/nhl/daily.py`, `read_rosters`) reads each club's current roster
from the league (`ROSTER`), `goalies_of` lists its goalies, and `match` finds the one goalie on that club with that name, folding
accents, case and punctuation as `teams.abbr_for` does for clubs.

A name that matches no goalie on the club, or more than one, is reported
rather than guessed: the pick then falls back to the club's last starter,
with a note, as the NFL falls back to last game's quarterback.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any

ROSTER = 'https://api-web.nhle.com/v1/roster/{club}/current'

Json = Any


def _key(name: str) -> str:
    plain = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z]', '', plain.lower())


def goalies_of(roster: Json) -> list[tuple[int, str]]:
    """(player id, full name) for each goalie on a roster."""
    out = []
    for g in roster.get('goalies') or []:
        first = (g.get('firstName') or {}).get('default', '')
        last = (g.get('lastName') or {}).get('default', '')
        out.append((int(g['id']), f'{first} {last}'.strip()))
    return out


def match(name: str | None, goalies: list[tuple[int, str]]) -> tuple[int | None, str | None]:
    """(player id, None) for the one goalie with that name, or (None, why)."""
    if not name:
        return None, 'no goalie named'
    hits = [pid for pid, full in goalies if _key(full) == _key(name)]
    if len(hits) == 1:
        return hits[0], None
    if not hits:
        return None, f'{name} is not a goalie on the current roster'
    return None, f'{name} matches {len(hits)} goalies on the roster'
