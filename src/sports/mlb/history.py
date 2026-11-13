"""MLB's history for the backtest (Stage 99 item 1), as experiments/mlb/stage98/registry.json fixes it.

For each season: the Stats API's schedule (`schedule.load_schedule`, its own checks) and, for every final game it
keeps, the box score's pitchers: each club's pitchers in the order they appeared, the first the starter, with the
outs each recorded and the runs each allowed. Two files a season under `data/mlb/history/`:

- `games_<season>.csv`: one row per final game (`GAME_FIELDS`), with each club's starter;
- `pitchers_<season>.csv`: one row per pitcher per game (`PITCHER_FIELDS`), `order` 0 being the starter.

A box score that lists no pitcher for a club, or a pitcher without outs and runs, stops the season with every such
game named (`HistoryError`): the registration's starter term cannot be read from a guess.

Before a season is used, `fallback_check` compares its finals with Retrosheet's game log, game by game (date, game
number, the two clubs, both scores), as the registration's fallback_check says: at least 99% must agree, and every
disagreement is listed. Retrosheet's club codes are mapped to Stats API ids from the season's own games, never typed
by hand. A season whose log Retrosheet has not posted is not checked, and so not used, until it has.

Each run writes what it found to `data/mlb/history/checks.json` (per season: games compared, how many agree,
every disagreement, and whether the season is checked); the backtest reads only checked seasons.

Run by hand (MLB_CACHE caches finished seasons' schedules; box scores are read once and stored):
    python -m src.sports.mlb.history 2010 2025
"""
from __future__ import annotations

import argparse
import io
import json
import time
import urllib.request
import zipfile
from collections import Counter
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from src.core.sport import GameStatus, sport_paths
from src.sports.mlb import schedule

PATHS = sport_paths('mlb')
HISTORY = PATHS.data / 'history'
#: Only what the starter term reads, so a box is about 13 KB instead of 170.
BOX = (schedule.STATS + '/game/{gid}/boxscore?fields=teams,home,away,team,id,pitchers,players,person,stats,'
       'pitching,runs,outs')
RETRO = 'https://www.retrosheet.org/gamelogs/gl{season}.zip'
GAME_FIELDS = ('game_id', 'season', 'slate', 'game_type', 'start_utc', 'home', 'away', 'home_score', 'away_score',
               'neutral_site', 'venue_id', 'home_starter', 'away_starter')
PITCHER_FIELDS = ('game_id', 'club', 'order', 'pitcher_id', 'outs', 'runs')
#: The registration's agreement floor against Retrosheet.
AGREEMENT = 0.99

Json = Any


class HistoryError(ValueError):
    """A season that cannot be written without guessing."""


def fetch(url: str, timeout: int = 60, tries: int = 3) -> bytes:
    req = urllib.request.Request(url, headers={'User-Agent': 'NFL-Model-2 MLB history'})
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


def pitcher_rows(box: Json, game_id: str) -> list[dict[str, Any]]:
    """Each club's pitchers in the order they appeared, with outs and runs. Raises when a club lists none, or a
    pitcher's line lacks either figure."""
    rows = []
    problems = []
    for side in ('home', 'away'):
        t = ((box or {}).get('teams') or {}).get(side) or {}
        club = (t.get('team') or {}).get('id')
        pitchers = t.get('pitchers') or []
        if not isinstance(club, int) or not pitchers:
            problems.append(f'game {game_id}: the {side} box lists no club or no pitcher')
            continue
        for order, pid in enumerate(pitchers):
            line = (((t.get('players') or {}).get(f'ID{pid}') or {}).get('stats') or {}).get('pitching') or {}
            outs, runs = line.get('outs'), line.get('runs')
            if not isinstance(outs, int) or not isinstance(runs, int):
                problems.append(f'game {game_id}: pitcher {pid} has no outs or runs')
                continue
            rows.append({'game_id': str(game_id), 'club': str(club), 'order': order, 'pitcher_id': str(pid),
                         'outs': outs, 'runs': runs})
    if problems:
        raise HistoryError('; '.join(problems))
    return rows


def game_rows(sched: pd.DataFrame, pitchers: pd.DataFrame) -> pd.DataFrame:
    """The season's final games with each club's starter (order 0)."""
    finals = sched[sched['status'] == GameStatus.FINAL.value].copy()
    starters = pitchers[pitchers['order'] == 0].set_index(['game_id', 'club'])['pitcher_id']
    finals['home_starter'] = [starters.get((g, h)) for g, h in zip(finals['game_id'], finals['home'])]
    finals['away_starter'] = [starters.get((g, a)) for g, a in zip(finals['game_id'], finals['away'])]
    finals['start_utc'] = pd.to_datetime(finals['start_utc'], utc=True).dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    return finals[list(GAME_FIELDS)].reset_index(drop=True)


def read_season(season: int, sched: pd.DataFrame, get: Callable[[str], bytes] = fetch,
                pause: float = 0.05) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(games, pitchers) for one season's final games. Every box is read before anything is decided, so one run
    names every unusable game."""
    rows: list[dict[str, Any]] = []
    problems: list[str] = []
    for gid in sched.loc[sched['status'] == GameStatus.FINAL.value, 'game_id']:
        try:
            rows.extend(pitcher_rows(json.loads(get(BOX.format(gid=gid))), str(gid)))
        except HistoryError as exc:
            problems.append(str(exc))
        if pause:
            time.sleep(pause)
    if problems:
        raise HistoryError(f'{season}: ' + '; '.join(problems[:30]) + (f' (and {len(problems) - 30} more)'
                                                                        if len(problems) > 30 else ''))
    pitchers = pd.DataFrame(rows, columns=list(PITCHER_FIELDS))
    return game_rows(sched, pitchers), pitchers


def retro_games(data: bytes) -> pd.DataFrame:
    """Retrosheet's game log: date, game number, visiting and home club codes, and both scores."""
    z = zipfile.ZipFile(io.BytesIO(data))
    text = z.read(z.namelist()[0]).decode('latin-1')
    rows = []
    for line in text.splitlines():
        f = [x.strip('"') for x in line.split(',')]
        rows.append({'slate': f'{f[0][:4]}-{f[0][4:6]}-{f[0][6:8]}', 'number': int(f[1] or 0),
                     'away': f[3], 'home': f[6], 'away_score': int(f[9]), 'home_score': int(f[10])})
    return pd.DataFrame(rows)


def code_map(retro: pd.DataFrame, games: pd.DataFrame) -> dict[str, str]:
    """Each Retrosheet code's Stats API id, learned from the season's own games: a Retrosheet game and a Stats API
    final on the same date with the same two scores, the only such pair that day, vote for its clubs' codes."""
    votes: dict[str, Counter[str]] = {}
    sa = games.assign(key=[(s, frozenset((h, a))) for s, h, a in
                           zip(games['slate'], games['home_score'], games['away_score'])])
    by_key = sa.groupby('key')
    keyed = {k: v for k, v in by_key}
    for r in retro.itertuples():
        match = keyed.get((r.slate, frozenset((r.home_score, r.away_score))))
        if match is None or len(match) != 1:
            continue
        m = match.iloc[0]
        if m['home_score'] == r.home_score and m['away_score'] == r.away_score and r.home_score != r.away_score:
            votes.setdefault(r.home, Counter())[str(m['home'])] += 1
            votes.setdefault(r.away, Counter())[str(m['away'])] += 1
    return {code: c.most_common(1)[0][0] for code, c in votes.items()}


def fallback_check(games: pd.DataFrame, retro: pd.DataFrame, venues: Mapping[str, int]) -> tuple[int, list[str]]:
    """(regular-season games compared, the disagreements). A game matches by date, game number and the two clubs.
    It agrees when both scores agree; one whose home and away are swapped agrees only if the Stats API's venue is
    the home club's own venue for the season, or the game is neutral."""
    codes = code_map(retro, games)
    reg = games[games['game_type'] == 'regular']
    index: dict[tuple[str, frozenset[str]], list[Mapping[str, Any]]] = {}
    for g in reg.to_dict('records'):
        index.setdefault((str(g['slate']), frozenset((str(g['home']), str(g['away'])))), []).append(g)
    bad = []
    for r in retro.itertuples():
        home, away = codes.get(r.home), codes.get(r.away)
        where = f'{r.slate} game {r.number} {r.away} at {r.home}'
        if home is None or away is None:
            bad.append(f'{where}: a club code not mapped')
            continue
        found = index.get((r.slate, frozenset((home, away))), [])
        if len(found) > 1:
            found = [g for g in found if int(g['game_number']) == max(r.number, 1)] if 'game_number' in reg else found
        if len(found) != 1:
            bad.append(f'{where}: {len(found)} Stats API finals that day between the two clubs')
            continue
        g = found[0]
        if str(g['home']) == home and (g['home_score'], g['away_score']) == (r.home_score, r.away_score):
            continue
        swapped = str(g['home']) == away and (g['home_score'], g['away_score']) == (r.away_score, r.home_score)
        own = venues.get(str(g['home'])) == g['venue_id']
        if swapped and (own or bool(g['neutral_site'])):
            continue
        bad.append(f"{where}: Stats API {g['game_id']} says {g['away']} {g['away_score']} at {g['home']} "
                   f"{g['home_score']}")
    return len(retro), bad


def write(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    df.to_csv(tmp, index=False, lineterminator='\n')
    tmp.replace(path)


def checked(n: int, bad: Iterable[str]) -> bool:
    bad = list(bad)
    return n > 0 and (n - len(bad)) / n >= AGREEMENT


def main(argv: Iterable[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('first', type=int)
    ap.add_argument('last', type=int)
    args = ap.parse_args(list(argv) if argv is not None else None)
    checks_path = HISTORY / 'checks.json'
    checks: dict[str, Any] = json.loads(checks_path.read_text(encoding='utf-8')) if checks_path.exists() else {}
    for season in range(args.first, args.last + 1):
        sched = schedule.load_schedule(season)
        gpath, ppath = HISTORY / f'games_{season}.csv', HISTORY / f'pitchers_{season}.csv'
        if not gpath.exists():
            games, pitchers = read_season(season, sched)
            write(pitchers, ppath)
            write(games, gpath)
        games = pd.read_csv(gpath, dtype={'game_id': str, 'home': str, 'away': str})
        games = games.merge(sched[['game_id', 'game_number']], on='game_id', how='left')
        venues = {str(k): v for k, v in schedule.home_venues(schedule.fetch_json(
            schedule.CLUBS.format(season=season))).items()}
        try:
            retro = retro_games(fetch(RETRO.format(season=season)))
        except OSError as exc:
            print(f'{season}: {len(games)} games; Retrosheet log not read ({exc}), so not checked and not used yet',
                  flush=True)
            checks[str(season)] = {'games': len(games), 'compared': 0, 'agree': 0, 'disagreements': [],
                                   'checked': False, 'note': 'Retrosheet log not read'}
            continue
        n, bad = fallback_check(games, retro, venues)
        checks[str(season)] = {'games': len(games), 'compared': n, 'agree': n - len(bad), 'disagreements': bad,
                               'checked': checked(n, bad)}
        print(f'{season}: {len(games)} games; Retrosheet agrees on {n - len(bad)} of {n}'
              f" ({'checked' if checked(n, bad) else 'BELOW 99%, not used'})", flush=True)
        for line in bad:
            print(f'  {line}', flush=True)
    HISTORY.mkdir(parents=True, exist_ok=True)
    checks_path.write_text(json.dumps(dict(sorted(checks.items())), indent=1) + '\n', encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
