"""
A QB override is checked against the team's roster and its source against an allowlist.

Stage 88 item 4 (the 2026-11-02 review). `weekly_update.load_qb_overrides`
refuses an override with no link or no valid GSIS id, but nothing checked
that the player is a quarterback on that team, or that the link is a site
anyone would cite. An override is a claim about who plays, and the lock
predicts on it.

Two checks, on every override:

- **Roster.** The player is on the team's current nflverse roster
  (`nflreadpy.load_rosters`) at quarterback, with a status that can play
  (`PLAYABLE`). A player cut, retired, on reserve, or on another team is
  refused.
- **Source.** The link's host is a team's own site or an outlet in
  `data/nfl/qb_override_sources.json`, or a subdomain of one.

Where they run:

- On a pull request that changes an override file, as a check
  (`python -m src.sports.nfl.override_check <file>...`, exit 1 on a problem),
  so the problem is found before the PR is merged, not at the lock.
- At the lock (`weekly_update.plan_week`). An override that fails either
  check is NOT used: the pick falls back to the schedule's starter, and the
  run logs a `DEGRADED: QB overrides:` line, on which the Weekly update raises
  an issue. A roster that cannot be read leaves the overrides unchecked and
  used, and says so the same way. Neither stops the run: a whole week's
  picks are not traded for one override.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from src.sports.nfl.paths import DATA_DIR

SOURCES = DATA_DIR / 'qb_override_sources.json'

#: nflverse roster statuses a player can start from: active, inactive for the
#: last game, practice squad (who can be elevated). Not cut, released,
#: retired, traded, or on a reserve list.
PLAYABLE = frozenset({'ACT', 'INA', 'DEV'})

Roster = dict[str, dict[str, str]]  # gsis_id -> {'team', 'position', 'status', 'name'}


def allowed_domains(path: Path = SOURCES) -> set[str]:
    spec = json.loads(path.read_text(encoding='utf-8'))
    return set(spec['outlets']) | set(spec['teams'].values())


def source_allowed(url: str, domains: Iterable[str]) -> bool:
    """True when the link is https or http and its host is a listed domain or a subdomain of one."""
    parts = urlsplit(str(url))
    host = (parts.hostname or '').lower()
    if parts.scheme not in ('http', 'https') or not host:
        return False
    return any(host == d or host.endswith('.' + d) for d in domains)


def roster_problem(entry: dict[str, Any], roster: Roster) -> str | None:
    """Why the roster says this player cannot be the team's starter, or None."""
    who = f"{entry['team']}: {entry['player_name']} ({entry['player_id']})"
    row = roster.get(entry['player_id'])
    if row is None:
        return f'{who} is not on any current roster'
    if row['team'] != entry['team']:
        return f"{who} is on {row['team']}'s roster, not {entry['team']}'s"
    if row['position'] != 'QB':
        return f"{who} is listed at {row['position']}, not quarterback"
    if row['status'] not in PLAYABLE:
        return f"{who} has roster status {row['status']}, which cannot start"
    return None


def problems(entries: Iterable[dict[str, Any]], roster: Roster | None, domains: Iterable[str]) -> dict[str, list[str]]:
    """{team: [what is wrong with its override]} for every override with a
    problem. `roster` None means it could not be read: the roster is not checked."""
    domains = set(domains)
    out: dict[str, list[str]] = {}
    for e in entries:
        found = []
        if not source_allowed(e['source'], domains):
            found.append(f"{e['team']}: the source {e['source']} is not a team site or a listed outlet "
                         f"(data/nfl/qb_override_sources.json)")
        if roster is not None and (why := roster_problem(e, roster)) is not None:
            found.append(why)
        if found:
            out[e['team']] = found
    return out


def load_roster(season: int) -> Roster:
    """The season's current nflverse roster, by GSIS id."""
    import nflreadpy as nfl
    frame = nfl.load_rosters(season).to_pandas()
    out: Roster = {}
    for r in frame.itertuples(index=False):
        if isinstance(r.gsis_id, str) and r.gsis_id:
            out[r.gsis_id] = {'team': str(r.team), 'position': str(r.position), 'status': str(r.status),
                              'name': str(r.full_name)}
    return out


def read_roster(season: int, loader: Callable[[int], Roster] | None = None) -> tuple[Roster | None, str | None]:
    """(roster, None), or (None, why) when it cannot be read. The loader is
    looked up at the call, so a test can replace `load_roster`."""
    try:
        roster = (loader or load_roster)(season)
    except Exception as exc:  # any failure to read is reported, never fatal here
        return None, f'{type(exc).__name__}: {exc}'
    if not roster:
        return None, 'the roster came back empty'
    return roster, None


def screen(overrides: dict[str, dict[str, Any]], season: int,
           loader: Callable[[int], Roster] | None = None,
           domains: Iterable[str] | None = None) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """At the lock: (the overrides to use, the DEGRADED lines to log). An
    override with a problem is dropped; an unreadable roster drops none."""
    if not overrides:
        return overrides, []
    roster, why = read_roster(season, loader)
    found = problems(overrides.values(), roster, allowed_domains() if domains is None else domains)
    lines = [f'DEGRADED: QB overrides: not used, {msg}; the pick uses the schedule\'s starter'
             for team in sorted(found) for msg in found[team]]
    if why is not None:
        lines.append(f'DEGRADED: QB overrides: the roster could not be read ({why}), so the overrides '
                     f'were used without the roster check')
    return {t: o for t, o in overrides.items() if t not in found}, lines


def main(argv: list[str] | None = None, loader: Callable[[int], Roster] | None = None) -> int:
    """Check override files as a pull request's check. Exit 1 on any problem,
    including a roster that cannot be read: a check that did not run is not a pass."""
    from src.sports.nfl.paths import parse_week
    from src.sports.nfl.weekly_update import QBOverrideError, load_qb_overrides

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1] if __doc__ else None)
    ap.add_argument('files', nargs='+', type=Path)
    args = ap.parse_args(argv)
    bad = 0
    rosters: dict[int, Roster] = {}
    for path in args.files:
        parsed = parse_week(path.stem)
        if parsed is None:
            print(f'{path}: not a <season>_week<N>.json override file')
            bad += 1
            continue
        season, week = parsed
        try:
            overrides = load_qb_overrides(season, week, path.parent)
        except QBOverrideError as exc:
            print(f'{path}: {exc}')
            bad += 1
            continue
        if season not in rosters:
            roster, why = read_roster(season, loader)
            if roster is None:
                print(f'{path}: the {season} roster could not be read ({why}); not checked')
                bad += 1
                continue
            rosters[season] = roster
        found = problems(overrides.values(), rosters[season], allowed_domains())
        for team in sorted(found):
            for msg in found[team]:
                print(f'{path}: {msg}')
        bad += len(found)
        if not found:
            print(f'{path}: {len(overrides)} override(s), each a quarterback on its team\'s roster with a listed source')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
