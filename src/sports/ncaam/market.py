"""The market for NCAA tournament games (Stage 103 item 2): ESPN's odds feed, read once and stored as read.

`experiments/ncaam/stage103/registry.json` (data.market): a game's market is the median, over the books ESPN's
odds feed lists for it, of each book's two-way home-win probability with the margin taken out evenly. A book's
price is its closing price where ESPN gives one, the listed price otherwise. Never used: a provider whose name
contains 'live'; a provider in the registration's `not_books` (a model or an aggregate); a provider in neither
list, until an amendment classifies it; a price whose two implied probabilities sum outside 1.00-1.20.

`data/ncaam/history/market_<season>.csv` keeps every provider ESPN listed, as read (`MARKET_FIELDS`); the rules
are applied when the file is read, so the file never has to be read again to change one.

Run by hand: python -m src.sports.ncaam.market 2020 2025
"""
from __future__ import annotations

import csv
import json
import statistics
import sys
import time
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.sports.ncaam.collector import HISTORY, fetch

ODDS = ('https://sports.core.api.espn.com/v2/sports/basketball/leagues/mens-college-basketball/events/{e}/'
        'competitions/{e}/odds?limit=50')
MARKET_FIELDS = ('game_id', 'season', 'provider', 'home_price', 'away_price', 'close_home_price',
                 'close_away_price', 'read_utc')
NCAA = '22'
PRICE_SUM = (1.00, 1.20)


def implied(price: float) -> float:
    """The probability an American moneyline implies, margin included."""
    return 100.0 / (price + 100.0) if price > 0 else -price / (-price + 100.0)


def _num(v: Any) -> float | None:
    """An American price as a number; ESPN writes even money as 'EVEN'. Anything inside (-100, 100) is no price."""
    text = str(v).strip().upper() if v is not None else ''
    if text == 'EVEN':
        return 100.0
    try:
        n = float(text.lstrip('+'))
    except ValueError:
        return None
    return n if abs(n) >= 100 else None


def provider_rows(odds: Any, game_id: str, season: int, stamp: str) -> list[dict[str, Any]]:
    """One row per provider ESPN lists for a game, whatever it is: nothing is judged here."""
    rows = []
    for it in odds.get('items') or []:
        h, a = it.get('homeTeamOdds') or {}, it.get('awayTeamOdds') or {}
        rows.append({'game_id': game_id, 'season': season,
                     'provider': str((it.get('provider') or {}).get('name') or ''),
                     'home_price': _num(h.get('moneyLine')), 'away_price': _num(a.get('moneyLine')),
                     'close_home_price': _num(((h.get('close') or {}).get('moneyLine') or {}).get('american')),
                     'close_away_price': _num(((a.get('close') or {}).get('moneyLine') or {}).get('american')),
                     'read_utc': stamp})
    return rows


def season_market(season: int, now: datetime, get: Callable[[str], bytes] = fetch, folder: Path = HISTORY,
                  pause: float = 0.1) -> pd.DataFrame:
    games = pd.read_csv(folder / f'games_{season}.csv', dtype=str, keep_default_na=False)
    stamp = now.astimezone(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')
    rows: list[dict[str, Any]] = []
    for gid in games.loc[games['tournament_id'] == NCAA, 'game_id']:
        rows += provider_rows(json.loads(get(ODDS.format(e=gid))), gid, season, stamp)
        if pause:
            time.sleep(pause)
    return pd.DataFrame(rows, columns=list(MARKET_FIELDS))


def write(df: pd.DataFrame, path: Path) -> None:
    tmp = path.with_suffix('.tmp')
    df.to_csv(tmp, index=False, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
    tmp.replace(path)


def book_prob(row: Any) -> float | None:
    """One provider row's home-win probability with the margin out, or None when it carries no usable price."""
    closing = pd.notna(row.close_home_price) and pd.notna(row.close_away_price)
    hp, ap = (row.close_home_price, row.close_away_price) if closing else (row.home_price, row.away_price)
    if pd.isna(hp) or pd.isna(ap):
        return None
    ih, ia = implied(float(hp)), implied(float(ap))
    if not PRICE_SUM[0] <= ih + ia <= PRICE_SUM[1]:
        return None
    return ih / (ih + ia)


def home_probs(rows: pd.DataFrame, books: Iterable[str], not_books: Iterable[str]) -> tuple[pd.DataFrame, list[str]]:
    """(game_id, home_prob, books: how many books' prices the median is of; the provider names in neither list).
    A game with no usable book price has no row."""
    known, never = set(books), set(not_books)
    by_game: dict[str, list[float]] = {}
    unclassified: set[str] = set()
    for row in rows.itertuples():
        name = str(row.provider)
        if 'live' in name.lower() or name in never:
            continue
        if name not in known:
            unclassified.add(name)
            continue
        p = book_prob(row)
        if p is not None:
            by_game.setdefault(str(row.game_id), []).append(p)
    out = pd.DataFrame([{'game_id': g, 'home_prob': statistics.median(ps), 'books': len(ps)}
                        for g, ps in by_game.items()], columns=['game_id', 'home_prob', 'books'])
    return out, sorted(unclassified)


def load(seasons: Iterable[int], books: Iterable[str], not_books: Iterable[str],
         folder: Path = HISTORY) -> tuple[pd.DataFrame, list[str]]:
    """The market for `seasons`' tournament games. Raises FileNotFoundError when a season's file is missing."""
    rows = pd.concat([pd.read_csv(folder / f'market_{s}.csv', dtype={'game_id': str, 'provider': str},
                                  keep_default_na=False, na_values=['']) for s in seasons], ignore_index=True)
    return home_probs(rows, books, not_books)


def main(argv: Iterable[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    first, last = int(args[0]), int(args[1] if len(args) > 1 else args[0])
    for season in range(first, last + 1):
        path = HISTORY / f'market_{season}.csv'
        if path.exists():
            print(f'{season}: {path.name} exists, not read again')
            continue
        df = season_market(season, datetime.now(UTC))
        write(df, path)
        print(f'{season}: {df["game_id"].nunique()} games, {len(df)} provider rows')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
