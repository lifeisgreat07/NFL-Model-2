"""Men's college basketball results, collected through the season (Stage 103 item 1).

The bracket's ratings read the whole season's games, so they are collected as they finish: ESPN's men's
college scoreboard (`site.api.espn.com`, Division I, `groups=50`, and the NCAA tournament's board, `groups=100`,
which holds tournament games the first can leave out), one day at a time. The season's games are the
ratings' input only; no season picks are published.

Each final game is one row in `data/ncaam/history/games_<season>.csv` (`GAME_FIELDS`): ESPN's event id, the Eastern
date, the UTC start, both clubs (ESPN's team ids, with their abbreviations for reading), both scores, whether the
site is neutral, ESPN's tournament id and note (22 is the NCAA tournament; a conference tournament has its own),
whether it is a conference game, and when the row was read (`read_utc`). A stored row is never rewritten: a game
already in the file is skipped, so a run reads only what is new. A final ESPN gives no winner for, or without both
scores, is never guessed at: the day's other finals are still stored (audit 8, finding S5), the game is listed in
`data/ncaam/unread.json` with the day and the reason, and the run fails while anything is listed there, so the alert
stays open after the day leaves the three-day window. A listed game leaves the list once it is stored.

`season` is the year the season starts: 2026 for 2026-27, which begins in November and ends with the title game in
April.

Run by hand (the days run backwards from yesterday, Eastern, by default the last three):
    python -m src.sports.ncaam.collector [--from 2026-11-03] [--to 2026-11-12]
"""
from __future__ import annotations

import argparse
import csv
import json
import time
import urllib.request
from collections.abc import Callable, Iterable
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from src.core.sport import sport_paths

PATHS = sport_paths('ncaam')
HISTORY = PATHS.data / 'history'
SCOREBOARD = ('https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard'
              '?dates={day}&groups=50&limit=500')
#: ESPN's NCAA-tournament group. Its Division I board can leave a tournament game out (two of 2017's First Four), so
#: each day is read from both, and a game on both is one row.
TOURNAMENT_BOARD = SCOREBOARD.replace('groups=50', 'groups=100')
GAME_FIELDS = ('game_id', 'season', 'day', 'start_utc', 'home_id', 'away_id', 'home', 'away', 'home_score',
               'away_score', 'neutral_site', 'tournament_id', 'note', 'conference_game', 'read_utc')
ET = 'America/New_York'
DEFAULT_DAYS = 3

Json = Any


class CollectorError(ValueError):
    """ESPN answered with something this file will not guess about."""


def season_of(day: date) -> int:
    """The season a date belongs to, labelled by the year it starts: from August on, the season starting that
    year; before August, the one that started the year before."""
    return day.year if day.month >= 8 else day.year - 1


def fetch(url: str, timeout: int = 30, tries: int = 3) -> bytes:
    req = urllib.request.Request(url, headers={'User-Agent': 'NFL-Model-2 NCAAM collector'})
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body: bytes = r.read()
                return body
        except OSError:
            if attempt == tries - 1:
                raise
            time.sleep(2 ** attempt)
    raise AssertionError('unreachable')


def _int(v: Any) -> int | None:
    try:
        return int(str(v))
    except (TypeError, ValueError):
        return None


def finals(board: Json, day: date, read_at: datetime) -> list[dict[str, Any]]:
    """Every completed game on one day's scoreboard as a row. Raises naming every final without two clubs, both
    scores and a winner."""
    rows, problems = read_finals(board, day, read_at)
    if problems:
        raise CollectorError('; '.join(problems))
    return rows


def read_finals(board: Json, day: date, read_at: datetime) -> tuple[list[dict[str, Any]], list[str]]:
    """(every usable final on one day's scoreboard as a row, a line naming each final that is not usable)."""
    rows, problems = [], []
    stamp = read_at.astimezone(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')
    for e in board.get('events') or []:
        comp = (e.get('competitions') or [{}])[0]
        if not ((comp.get('status') or {}).get('type') or {}).get('completed'):
            continue
        gid = str(e.get('id'))
        sides = {c.get('homeAway'): c for c in comp.get('competitors') or []}
        if set(sides) != {'home', 'away'}:
            problems.append(f'game {gid}: not a home and an away club')
            continue
        hs, as_ = _int(sides['home'].get('score')), _int(sides['away'].get('score'))
        if hs is None or as_ is None or hs == as_:
            problems.append(f'game {gid}: final without two different scores ({hs}-{as_})')
            continue
        h, a = sides['home'].get('team') or {}, sides['away'].get('team') or {}
        if not h.get('id') or not a.get('id') or h.get('id') == a.get('id'):
            problems.append(f'game {gid}: not two clubs')
            continue
        note = '; '.join(str(n.get('headline')) for n in comp.get('notes') or [] if n.get('headline'))
        rows.append({'game_id': gid, 'season': season_of(day), 'day': day.isoformat(),
                     'start_utc': str(e.get('date') or ''), 'home_id': str(h['id']), 'away_id': str(a['id']),
                     'home': str(h.get('abbreviation') or ''), 'away': str(a.get('abbreviation') or ''),
                     'home_score': hs, 'away_score': as_, 'neutral_site': bool(comp.get('neutralSite')),
                     'tournament_id': str(comp.get('tournamentId') or ''), 'note': note,
                     'conference_game': bool(comp.get('conferenceCompetition')), 'read_utc': stamp})
    return rows, problems


def stored(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=list(GAME_FIELDS))
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def add(rows: Iterable[dict[str, Any]], folder: Path = HISTORY) -> int:
    """Append each row whose game is not stored yet to its season's file; returns how many were added."""
    added = 0
    by_season: dict[int, list[dict[str, Any]]] = {}
    for r in rows:
        by_season.setdefault(int(r['season']), []).append(r)
    for season, new in by_season.items():
        path = folder / f'games_{season}.csv'
        have = set(stored(path)['game_id'])
        fresh = [r for r in new if r['game_id'] not in have]
        if not fresh:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('a', encoding='utf-8', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(GAME_FIELDS), lineterminator='\n')
            if path.stat().st_size == 0:
                w.writeheader()
            w.writerows(fresh)
        added += len(fresh)
    return added


def days_between(first: date, last: date) -> list[date]:
    return [first + timedelta(days=i) for i in range((last - first).days + 1)]


def day_board(day: date, get: Callable[[str], bytes] = fetch) -> Json:
    """One day's events from the Division I board and the tournament board, each event once."""
    events: dict[str, Any] = {}
    for url in (SCOREBOARD, TOURNAMENT_BOARD):
        for e in json.loads(get(url.format(day=day.strftime('%Y%m%d')))).get('events') or []:
            events.setdefault(str(e.get('id')), e)
    return {'events': list(events.values())}


def unread_path(folder: Path) -> Path:
    return folder.parent / 'unread.json'


def collect(days: Iterable[date], now: datetime, get: Callable[[str], bytes] = fetch,
            folder: Path = HISTORY, pause: float = 0.2) -> int:
    """Store every usable final of `days`; list each unusable one in unread.json, drop from that list every game
    now stored, and raise while the list is not empty."""
    added = 0
    path = unread_path(folder)
    unread: dict[str, dict[str, str]] = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    stamp = now.astimezone(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')
    for d in days:
        rows, problems = read_finals(day_board(d, get), d, now)
        added += add(rows, folder)
        for line in problems:
            gid = line.split(':')[0].removeprefix('game ')
            unread.setdefault(gid, {'day': d.isoformat(), 'reason': line, 'first_seen': stamp})
        if pause:
            time.sleep(pause)
    have = set().union(*(set(stored(p)['game_id']) for p in folder.glob('games_*.csv'))) if folder.exists() else set()
    unread = {gid: v for gid, v in sorted(unread.items()) if gid not in have}
    if unread or path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(unread, indent=1) + '\n', encoding='utf-8')
    if unread:
        raise CollectorError(f'{len(unread)} final(s) not stored, listed in {path.name}: '
                             + '; '.join(v['reason'] for v in unread.values()))
    return added


def main(argv: Iterable[str] | None = None, now: datetime | None = None,
         get: Callable[[str], bytes] = fetch) -> int:
    now = now or datetime.now(UTC)
    yesterday = pd.Timestamp(now).tz_convert(ET).date() - timedelta(days=1)
    ap = argparse.ArgumentParser(description=(__doc__ or '').split('\n')[0])
    ap.add_argument('--from', dest='first', type=date.fromisoformat,
                    default=yesterday - timedelta(days=DEFAULT_DAYS - 1))
    ap.add_argument('--to', dest='last', type=date.fromisoformat, default=yesterday)
    args = ap.parse_args(list(argv) if argv is not None else None)
    n = collect(days_between(args.first, args.last), now, get)
    print(f'{n} new games from {args.first} to {args.last}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
