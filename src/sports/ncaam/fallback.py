"""The checked fallback for the college history (Stage 103 item 2): hoopR's schedule file.

`experiments/ncaam/stage103/registry.json` (data.fallback_check): before a season is used, its stored finals are
compared with SportsDataverse's hoopR men's college schedule file by ESPN event id. At least 99% of the stored
finals must be in hoopR's file with both scores equal, and every NCAA tournament game that is missing there or
differs is named. hoopR mirrors ESPN, so this guards against a dropped or garbled game, not against ESPN itself.

Each season's result is one entry of `data/ncaam/history/checks.json`; the backtest refuses a season with no
passing entry.

Run by hand: python -m src.sports.ncaam.fallback 2014 2025
"""
from __future__ import annotations

import io
import json
import sys
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

import pandas as pd

from src.sports.ncaam.collector import HISTORY, fetch

#: hoopR names a season's file by the year the season ends.
HOOPR = ('https://raw.githubusercontent.com/sportsdataverse/hoopR-mbb-data/main/mbb/schedules/parquet/'
         'mbb_schedule_{year}.parquet')
NCAA = '22'
NEEDED = 0.99


def compare(stored: pd.DataFrame, other: pd.DataFrame) -> dict[str, Any]:
    """One season's entry: how many stored finals the fallback has with both scores equal, and the tournament
    games it lacks or scores differently. `other` has `id`, `home_score` and `away_score`."""
    o = other.assign(id=other['id'].astype(str)).drop_duplicates('id').set_index('id')
    there = stored['game_id'].isin(o.index)
    both = stored[there]
    theirs = o.loc[both['game_id']]
    equal = ((pd.to_numeric(theirs['home_score'], errors='coerce').to_numpy()
              == both['home_score'].astype(int).to_numpy())
             & (pd.to_numeric(theirs['away_score'], errors='coerce').to_numpy()
                == both['away_score'].astype(int).to_numpy()))
    agreeing = set(both['game_id'][equal])
    tournament = stored[stored['tournament_id'] == NCAA]
    named = [{'game_id': gid, 'problem': 'missing' if gid not in o.index else 'scores differ'}
             for gid in tournament['game_id'] if gid not in agreeing]
    share = len(agreeing) / len(stored) if len(stored) else 0.0
    return {'stored': int(len(stored)), 'in_fallback': int(there.sum()), 'scores_equal': len(agreeing),
            'share': round(share, 6), 'needed': NEEDED, 'checked': bool(share >= NEEDED),
            'tournament_games_named': named}


def check(season: int, get: Callable[[str], bytes] = fetch, folder: Path = HISTORY) -> dict[str, Any]:
    stored = pd.read_csv(folder / f'games_{season}.csv', dtype=str, keep_default_na=False)
    other = pd.read_parquet(io.BytesIO(get(HOOPR.format(year=season + 1))),
                            columns=['id', 'home_score', 'away_score'])
    return {**compare(stored, other), 'source': HOOPR.format(year=season + 1)}


def main(argv: Iterable[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    first, last = int(args[0]), int(args[1] if len(args) > 1 else args[0])
    path = HISTORY / 'checks.json'
    doc: dict[str, Any] = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    for season in range(first, last + 1):
        doc[str(season)] = entry = check(season)
        print(f"{season}: {entry['scores_equal']} of {entry['stored']} agree ({entry['share']:.4f}), "
              f"{len(entry['tournament_games_named'])} tournament games named, checked {entry['checked']}")
    path.write_text(json.dumps(dict(sorted(doc.items())), indent=1) + '\n', encoding='utf-8')
    return 0 if all(doc[str(s)]['checked'] for s in range(first, last + 1)) else 1


if __name__ == '__main__':
    raise SystemExit(main())
