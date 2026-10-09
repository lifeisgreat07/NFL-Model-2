"""The NBA's injury report, read at the run that saves each pick (Stage 65).

Unlike the NHL's, this list is an input: Model A's availability term
(`experiments/nba/stage61/registry.json`) counts every expected player not
listed Out as playing, and `experiments/nba/stage65/registry.json` says the
live run reads that from ESPN's injury report. So the parse is strict:
a team, a player or a status this file does not recognise stops the read
(`InjurySourceError`), the daily run then makes the pick without the
availability term and says so, and nothing is filled in.

A player is matched to the minutes history by ESPN's athlete id, which the
report carries only inside the player's link
(`https://www.espn.com/nba/player/_/id/4585618/...`).
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import datetime
from typing import Any

SOURCE = 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries'
NAME = 'espn_nba_injuries'
#: ESPN's statuses. Only Out removes a player; the others count as playing.
STATUSES = frozenset({'Out', 'Day-To-Day', 'Questionable', 'Doubtful', 'Probable'})
OUT = 'Out'
ATHLETE_ID = re.compile(r'/id/(\d+)')

Json = Any


class InjurySourceError(ValueError):
    """The report is not the list this reads."""


def athlete_id(athlete: Json) -> str | None:
    for link in athlete.get('links') or []:
        m = ATHLETE_ID.search(str(link.get('href') or ''))
        if m:
            return m.group(1)
    return None


def parse(report: Json, teams: Iterable[str]) -> list[dict[str, str]]:
    """One row per listed player: team, athlete_id, name, status. `teams`
    is the set of ESPN codes the schedule uses; a team outside it, a player
    without an id, or an unknown status is refused, all named at once."""
    known = set(teams)
    lists = report.get('injuries')
    if not isinstance(lists, list) or not lists:
        raise InjurySourceError('no injury list')
    rows, problems = [], []
    for team in lists:
        for p in team.get('injuries') or []:
            athlete = p.get('athlete') or {}
            code = (athlete.get('team') or {}).get('abbreviation')
            pid = athlete_id(athlete)
            status = p.get('status')
            name = athlete.get('displayName')
            if code not in known:
                problems.append(f'{name}: team {code!r} not on the schedule')
            if pid is None:
                problems.append(f'{name}: no athlete id')
            if status not in STATUSES:
                problems.append(f'{name}: unknown status {status!r}')
            rows.append({'team': str(code), 'athlete_id': str(pid), 'name': str(name), 'status': str(status)})
    if problems:
        raise InjurySourceError('; '.join(problems))
    return rows


def out_ids(rows: Iterable[dict[str, str]], team: str) -> set[str]:
    """The athlete ids listed Out for one team."""
    return {r['athlete_id'] for r in rows if r['team'] == team and r['status'] == OUT}


def for_game(rows: list[dict[str, str]], home: str, away: str, read: datetime) -> dict[str, Any]:
    """What the pick stores: the source, when it was read, and each side's
    listed players sorted by name."""
    def side(team: str) -> list[dict[str, str]]:
        own = sorted((r for r in rows if r['team'] == team), key=lambda r: r['name'])
        return [{'athlete_id': r['athlete_id'], 'name': r['name'], 'status': r['status']} for r in own]
    return {'source': NAME, 'read_utc': read.strftime('%Y-%m-%dT%H:%M:%SZ'), 'home': side(home), 'away': side(away)}
