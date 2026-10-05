"""The market's price for each NHL game, from the league's own odds feed.

Stage 55 item 3. `api-web.nhle.com/v1/partner-game/US/now` lists today's
games with the league's betting partner's lines (DraftKings in the US).
Model B wants the two-way moneyline: who wins, overtime and the shootout
included, which is what Models A and B predict. The feed also carries the
three-way regulation line, the puck line and the total; those are not read.
`docs/nhl-data.md` section 3 is why: before 2024-25 the history is the
three-way line, converted; from now on the pipeline records the two-way
line itself, since the feed only ever answers for "now".

Each line is stored with where and when it was read. `record` keeps a
game's history the way the NFL's line snapshots do: a row is added only
when the price moves, and nothing is added once the game has started, since
a price read after the start is an in-game price.
"""
from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Any

SOURCE = 'https://api-web.nhle.com/v1/partner-game/US/now'
TWO_WAY = 'MONEY_LINE_2_WAY'

Json = Any


def implied(price: float) -> float:
    """The probability an American price implies, the margin still in it."""
    if price == 0 or -100 < price < 100:
        raise ValueError(f'not an American price: {price}')
    return -price / (-price + 100) if price < 0 else 100 / (price + 100)


def no_vig_home(home_price: float, away_price: float) -> float:
    """The home team's win probability with the margin taken out evenly."""
    h, a = implied(home_price), implied(away_price)
    return h / (h + a)


def _two_way(side: Json) -> float | None:
    for o in side.get('odds') or []:
        if o.get('description') == TWO_WAY and o.get('value') is not None:
            return float(o['value'])
    return None


def parse(feed: Json, read_utc: datetime) -> tuple[list[dict[str, Any]], list[str]]:
    """Rows for every game with both two-way prices, and a sentence for each
    game without them (reported, never filled in)."""
    book = (feed.get('bettingPartner') or {}).get('name')
    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    for g in feed.get('games') or []:
        home, away = g.get('homeTeam') or {}, g.get('awayTeam') or {}
        hp, ap = _two_way(home), _two_way(away)
        gid = str(g.get('gameId', '?'))
        if hp is None or ap is None:
            missing.append(f'game {gid} ({away.get("abbrev")} at {home.get("abbrev")}): no two-way moneyline')
            continue
        rows.append({
            'game_id': gid,
            'start_utc': g.get('startTimeUTC'),
            'home': home.get('abbrev'),
            'away': away.get('abbrev'),
            'book': book,
            'home_price': hp,
            'away_price': ap,
            'home_prob': round(no_vig_home(hp, ap), 4),
            'read_utc': read_utc.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'source': SOURCE,
        })
    return rows, missing


def _started(row: dict[str, Any]) -> bool:
    start = row.get('start_utc')
    return bool(start) and row['read_utc'] >= start


def record(rows: Iterable[dict[str, Any]], path: Path) -> int:
    """Add each row whose prices differ from that game's last stored row,
    skipping games that have started. Returns how many rows were added.
    The file is a JSON list, oldest first, written whole and swapped in."""
    history: list[dict[str, Any]] = json.loads(path.read_text(encoding='utf-8')) if path.exists() else []
    last: dict[str, dict[str, Any]] = {}
    for r in history:
        last[r['game_id']] = r
    added = 0
    for r in rows:
        if _started(r):
            continue
        prev = last.get(r['game_id'])
        if prev and (prev['home_price'], prev['away_price']) == (r['home_price'], r['away_price']):
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
