"""Who starts in goal, before the game and after it.

Stage 55 item 3. The goalie is the NHL's quarterback: the one player whose
late news moves the pick (`docs/nhl-data.md` section 4).

- **Before the game**, the league publishes no projected starter. Daily
  Faceoff's starting-goalie page does, labelled `Confirmed`, `Likely` or
  `Unconfirmed`, with its data in the page's `__NEXT_DATA__` payload. Days
  ahead it names a goalie with no label at all (read 2026-10-05); that is
  kept as a status of None, "no report yet", not given a label it lacks.
  `parse_faceoff` reads only the names, the label, and the link to the
  report the label rests on; the page's own prose is not kept.
- **After the game**, every box score flags exactly one starting goalie per
  team. `starters_from_boxscore` reads those: the backtest uses the actual
  starter, as the NFL's backtest uses the actual quarterback, and the
  grading can say whether the projection was right.

`record` keeps the projection's history per game: a row is added when the
goalie or the label changes, never once the game has started. A club the
page names that `teams.abbr_for` does not know stops the parse with the
name, rather than dropping the game.
"""
from __future__ import annotations

import json
import re
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Any

from src.sports.nhl.teams import abbr_for

SOURCE = 'https://www.dailyfaceoff.com/starting-goalies'
LABELS = ('Confirmed', 'Likely', 'Unconfirmed', None)
_NEXT_DATA = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)

Json = Any


class GoalieSourceError(ValueError):
    """The page answered in a shape this file will not guess about."""


def parse_faceoff(page: str, read_utc: datetime) -> list[dict[str, Any]]:
    """One row per game on the page: the date, both clubs, each side's
    projected goalie, its label and the report's link."""
    m = _NEXT_DATA.search(page)
    if not m:
        raise GoalieSourceError('no __NEXT_DATA__ payload on the page')
    props = json.loads(m.group(1)).get('props', {}).get('pageProps', {})
    games = props.get('data')
    day = props.get('date')
    if not isinstance(games, list) or not day:
        raise GoalieSourceError('the payload has no games list or no date')
    rows, problems = [], []
    for g in games:
        row: dict[str, Any] = {'date': day}
        for side in ('home', 'away'):
            club = abbr_for(g.get(f'{side}TeamName') or '')
            if club is None:
                problems.append(f'unknown club {g.get(f"{side}TeamName")!r}')
            label = g.get(f'{side}NewsStrengthName')
            if label not in LABELS:
                problems.append(f'{g.get(f"{side}TeamName")}: unknown label {label!r}')
            row[side] = club
            row[f'{side}_goalie'] = g.get(f'{side}GoalieName')
            row[f'{side}_status'] = label
            row[f'{side}_report'] = g.get(f'{side}NewsSourceUrl')
        row['read_utc'] = read_utc.strftime('%Y-%m-%dT%H:%M:%SZ')
        row['source'] = SOURCE
        rows.append(row)
    if problems:
        raise GoalieSourceError('; '.join(problems))
    return rows


def starters_from_boxscore(box: Json) -> dict[str, dict[str, Any]]:
    """{'home': {...}, 'away': {...}}: each side's one flagged starter, with
    the league's player id. Raises unless each side flags exactly one."""
    stats = box.get('playerByGameStats') or {}
    out = {}
    for side in ('home', 'away'):
        starters = [g for g in (stats.get(f'{side}Team') or {}).get('goalies', []) if g.get('starter')]
        if len(starters) != 1:
            raise GoalieSourceError(f'game {box.get("id", "?")} {side}: {len(starters)} starters flagged, not 1')
        s = starters[0]
        out[side] = {'player_id': s.get('playerId'), 'name': (s.get('name') or {}).get('default')}
    return out


def _utc(value: Any) -> str:
    """A start as 'YYYY-MM-DDTHH:MM:SSZ', the form read_utc is compared in."""
    if hasattr(value, 'strftime'):
        return str(value.strftime('%Y-%m-%dT%H:%M:%SZ'))
    return str(value)


def attach_games(rows: Iterable[dict[str, Any]], slate: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Give each projection the league's game_id and start, matched on the
    date and both clubs. A projection with no game on the league's slate is
    an error: it means the page and the league disagree about the day."""
    by_key = {(str(g['slate']), g['home'], g['away']): g for g in slate}
    out, unmatched = [], []
    for r in rows:
        g = by_key.get((r['date'], r['home'], r['away']))
        if g is None:
            unmatched.append(f"{r['away']} at {r['home']} on {r['date']}")
            continue
        out.append({**r, 'game_id': str(g['game_id']), 'start_utc': _utc(g['start_utc'])})
    if unmatched:
        raise GoalieSourceError('no league game for: ' + ', '.join(unmatched))
    return out


def record(rows: Iterable[dict[str, Any]], path: Path) -> int:
    """Add each projection whose goalies or labels differ from that game's
    last stored one, skipping games that have started (each row needs
    `game_id` and `start_utc`, from `attach_games`). Returns rows added."""
    history: list[dict[str, Any]] = json.loads(path.read_text(encoding='utf-8')) if path.exists() else []
    last = {r['game_id']: r for r in history}
    fields = ('home_goalie', 'home_status', 'away_goalie', 'away_status')
    added = 0
    for r in rows:
        if r['read_utc'] >= r['start_utc']:
            continue
        prev = last.get(r['game_id'])
        if prev and all(prev[f] == r[f] for f in fields):
            continue
        history.append(r)
        last[r['game_id']] = r
        added += 1
    if added:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix('.tmp')
        tmp.write_text(json.dumps(history, indent=1) + '\n', encoding='utf-8')
        tmp.replace(path)
    return added
