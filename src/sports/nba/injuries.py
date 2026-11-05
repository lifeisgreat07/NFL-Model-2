"""The NBA's injury report, read at the run that saves each pick (Stage 65).

Unlike the NHL's, this list is an input: Model A's availability term
(`experiments/nba/stage61/registry.json`) counts every expected player not
listed Out as playing, and `experiments/nba/stage65/registry.json` says the
live run reads that from ESPN's injury report. So the parse is strict
about what it keeps, and says what it could not read:

- A report not shaped as registered, or a team the schedule does not know,
  stops the whole read (`InjurySourceError`): a team code that changed would
  leave the real team with no rows at all, which reads as fully healthy.
  So does a report that lists teams but yields no player, read or unread
  (Stage 92 item 8): every team "fully healthy" is the same silent failure.
  Every pick is then made without the availability term, and says so.
- A player row it cannot read (an unknown status, or no athlete id) is not
  kept, and its team is listed in `Report.unread` with the reason. Only that
  team's games are picked without availability, since the row could be a
  player who is out; every other game uses the report (Stage 83 item 5, the
  2026-11-02 review; the registry's `availability.amended_2026_11_04`).
Nothing is filled in either way.

A player is matched to the minutes history by ESPN's athlete id, which the
report carries only inside the player's link
(`https://www.espn.com/nba/player/_/id/4585618/...`).
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import datetime
from typing import Any, NamedTuple

SOURCE = 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries'
NAME = 'espn_nba_injuries'
#: ESPN's statuses. Only Out removes a player; the others count as playing.
STATUSES = frozenset({'Out', 'Suspension', 'Day-To-Day', 'Questionable', 'Doubtful', 'Probable'})
OUT = 'Out'
#: Statuses that remove a player: Out, and Suspension (ESPN began listing one on 2026-11-02, and a
#: suspended player cannot play). Mark's call, 2026-11-02; the registry's `availability.amended` says so.
UNAVAILABLE = frozenset({OUT, 'Suspension'})
ATHLETE_ID = re.compile(r'/id/(\d+)')

Json = Any


class InjurySourceError(ValueError):
    """The report is not the list this reads."""


class Report(NamedTuple):
    """The rows read, and for each team with a row that could not be, why."""
    rows: list[dict[str, str]]
    unread: dict[str, list[str]]


def athlete_id(athlete: Json) -> str | None:
    for link in athlete.get('links') or []:
        m = ATHLETE_ID.search(str(link.get('href') or ''))
        if m:
            return m.group(1)
    return None


def parse(report: Json, teams: Iterable[str]) -> Report:
    """One row per listed player it can read: team, athlete_id, name, status.
    `teams` is the set of ESPN codes the schedule uses. A team outside it
    refuses the whole report, every such team named at once; a player without
    an id or with an unknown status is left out and its team listed in
    `unread`, so that team's games are picked without availability."""
    known = set(teams)
    lists = report.get('injuries')
    if not isinstance(lists, list) or not lists:
        raise InjurySourceError('no injury list')
    rows: list[dict[str, str]] = []
    unread: dict[str, list[str]] = {}
    strangers = []
    for team in lists:
        for p in team.get('injuries') or []:
            athlete = p.get('athlete') or {}
            code = (athlete.get('team') or {}).get('abbreviation')
            pid = athlete_id(athlete)
            status = p.get('status')
            name = athlete.get('displayName')
            if code not in known:
                strangers.append(f'{name}: team {code!r} not on the schedule')
                continue
            problems = ([] if pid is not None else [f'{name}: no athlete id']) + (
                [] if status in STATUSES else [f'{name}: unknown status {status!r}'])
            if problems:
                unread.setdefault(str(code), []).extend(problems)
                continue
            rows.append({'team': str(code), 'athlete_id': str(pid), 'name': str(name), 'status': str(status)})
    if strangers:
        raise InjurySourceError('; '.join(strangers))
    # Stage 92 item 8 (audit 7, R5): a report that lists teams but yields no
    # player at all, read or unread, is not shaped as registered (a renamed
    # per-team key reads exactly so). Kept, it would say every player plays.
    if not rows and not unread:
        raise InjurySourceError(f'{len(lists)} teams listed and not one player read')
    return Report(rows, unread)


def out_ids(rows: Iterable[dict[str, str]], team: str) -> set[str]:
    """The athlete ids listed Out, or suspended, for one team."""
    return {r['athlete_id'] for r in rows if r['team'] == team and r['status'] in UNAVAILABLE}


def for_game(rows: list[dict[str, str]], home: str, away: str, read: datetime) -> dict[str, Any]:
    """What the pick stores: the source, when it was read, and each side's
    listed players sorted by name."""
    def side(team: str) -> list[dict[str, str]]:
        own = sorted((r for r in rows if r['team'] == team), key=lambda r: r['name'])
        return [{'athlete_id': r['athlete_id'], 'name': r['name'], 'status': r['status']} for r in own]
    return {'source': NAME, 'read_utc': read.strftime('%Y-%m-%dT%H:%M:%SZ'), 'home': side(home), 'away': side(away)}
