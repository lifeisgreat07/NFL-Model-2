"""The market's price for each MLB game at the run that saves its pick (Stage 101 item 3).

`experiments/mlb/stage101/registry.json` (`market`) fixes the order, and this file carries it out:

1. **ESPN** (`espn_price`): the game's odds from ESPN's core API, the backtest's own source. The first listed
   provider that is not marked live and is not one Stage 98's market rules leave out (`EXCLUDED`: ESPN's projections
   and AccuScore, which publish a model's output) and that has both moneylines, at its current price, the margin
   taken out evenly. It is used only when the two implied probabilities sum to between 1.00 and 1.20 (`SUM_RANGE`),
   as the backtest's market is. ESPN writes 0 for a price it does not have, and no American price lies between
   -100 and +100, so such a side is no price.
2. **Kalshi** (`kalshi_price`), only for a game ESPN gave no usable price: the game-winner market (series
   KXMLBGAME). Each side's price is the midpoint of its yes bid and ask; the home probability is the home midpoint
   over the two. Used only when both sides have a bid and an ask. Unlike the NBA's registration, MLB's sets no
   widest spread.
3. **None**: Model B is not run for the game, the pick is Model A's, and the page says "no price".

Whichever it is, `price_for` returns the source by name, so a pick can never be priced from somewhere it does not
say. `record` keeps every read in `data/mlb/lines/<season>.json`: a row only when the price moves, and nothing once
the game has started.

Matching a game. Every table here keys on the Stats API's club id. ESPN's scoreboard lists its events with its own
club codes, mapped by `ESPN_CODES`; that map was learned from 2026's finals by `market_history.code_map` (the same
date and two scores) on 2026-11-24, and differs from the Stats API's abbreviations only for Arizona (ARI) and the
White Sox (CHW). An ESPN event is the game's when its date and pair of clubs match. For a doubleheader, the two ESPN
events and the two games are paired in order, ESPN's by start and the Stats API's by game number. Any other count
leaves the game unmatched, never guessed. Where ESPN's home is the Stats API's away (a relocated game), the prices
are swapped back, so `home_prob` is always the Stats API home club's.

Kalshi names a game by its Eastern date, its start (HHMM), the two clubs' codes and, in a doubleheader, `G1` or `G2`
(`KXMLBGAME-26SEP221305TBNYYG1`), and a side by the code after the last dash. Its codes are the Stats API's own
abbreviations (`teams.NAMES`), all thirty, as the settled 2026 markets read on 2026-11-24 show. A game is matched by
date, the pair of clubs and, in a doubleheader, its game number.
"""
from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.sports.mlb.teams import NAMES

SCOREBOARD = 'https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard?dates={day}&limit=100'
ESPN_ODDS = 'https://sports.core.api.espn.com/v2/sports/baseball/leagues/mlb/events/{e}/competitions/{e}/odds'
KALSHI = 'https://api.elections.kalshi.com/trade-api/v2/markets?series_ticker=KXMLBGAME&status=open&limit=1000'
#: Providers whose price is a model's output, not a book's (Stage 98's market rules, audit 8 S3).
EXCLUDED = frozenset({'espn bet - projections', 'numberfire', 'teamrankings', 'accuscore'})
#: A two-way price is used only when its implied probabilities sum inside this range.
SUM_RANGE = (1.00, 1.20)
#: ESPN's club code -> Stats API club id, learned from 2026's finals on 2026-11-24.
ESPN_CODES: Mapping[str, str] = {
    'ARI': '109', 'ATH': '133', 'ATL': '144', 'BAL': '110', 'BOS': '111', 'CHC': '112', 'CHW': '145', 'CIN': '113',
    'CLE': '114', 'COL': '115', 'DET': '116', 'HOU': '117', 'KC': '118', 'LAA': '108', 'LAD': '119', 'MIA': '146',
    'MIL': '158', 'MIN': '142', 'NYM': '121', 'NYY': '147', 'PHI': '143', 'PIT': '134', 'SD': '135', 'SEA': '136',
    'SF': '137', 'STL': '138', 'TB': '139', 'TEX': '140', 'TOR': '141', 'WSH': '120'}
#: Kalshi's club code -> Stats API club id: the Stats API's own abbreviations.
KALSHI_CODES: Mapping[str, str] = {abbr: club for club, (abbr, _) in NAMES.items()}
MONTHS = {m: i + 1 for i, m in enumerate(('JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN',
                                          'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'))}
EVENT = re.compile(r'^KXMLBGAME-(\d{2})([A-Z]{3})(\d{2})\d{4}[A-Z]+?(?:G([12]))?$')

Json = Any


def implied(price: float) -> float:
    """The probability an American price implies, the margin still in it."""
    if price == 0 or -100 < price < 100:
        raise ValueError(f'not an American price: {price}')
    return -price / (-price + 100) if price < 0 else 100 / (price + 100)


def _num(value: Any) -> float | None:
    try:
        return float(str(value).replace('+', ''))
    except (TypeError, ValueError):
        return None


def espn_events(board: Json) -> list[dict[str, Any]]:
    """Each event on one ESPN scoreboard, played or not: its id, start, and each side's Stats API club id (None for
    a code `ESPN_CODES` does not know)."""
    out = []
    for e in board.get('events') or []:
        comp = (e.get('competitions') or [{}])[0]
        sides = {c.get('homeAway'): c for c in comp.get('competitors') or []}
        if set(sides) != {'home', 'away'}:
            continue
        code = {k: str((v.get('team') or {}).get('abbreviation')) for k, v in sides.items()}
        out.append({'espn_id': str(e.get('id')), 'start': str(e.get('date') or ''),
                    'home': ESPN_CODES.get(code['home']), 'away': ESPN_CODES.get(code['away'])})
    return out


def espn_match(games: pd.DataFrame, events: Iterable[Mapping[str, Any]]) -> tuple[dict[str, tuple[str, bool]],
                                                                                 list[str]]:
    """Each game's ESPN event and whether ESPN's home is the Stats API's away; and a line for each game left
    unmatched. `games` is one official date's games; `events` that date's ESPN scoreboard."""
    by_pair: dict[frozenset[str], list[Mapping[str, Any]]] = {}
    for e in events:
        if e['home'] and e['away']:
            by_pair.setdefault(frozenset((e['home'], e['away'])), []).append(e)
    out: dict[str, tuple[str, bool]] = {}
    missing = []
    for pair, group in games.groupby(games.apply(lambda g: frozenset((str(g['home']), str(g['away']))), axis=1),
                                 sort=False):
        cands = sorted(by_pair.get(pair, []), key=lambda e: e['start'])
        ordered = group.sort_values('game_number', kind='stable')
        if len(cands) != len(ordered):
            missing.extend(f'game {g.game_id}: {len(cands)} ESPN events for {len(ordered)} games'
                           for g in ordered.itertuples())
            continue
        for g, e in zip(ordered.itertuples(), cands, strict=True):
            out[str(g.game_id)] = (str(e['espn_id']), e['home'] != str(g.home))
    return out, missing


def espn_price(odds: Json, swapped: bool = False) -> dict[str, Any] | None:
    """(provider, home price, away price, home probability) from ESPN's odds for one game, the Stats API's home
    first, or None when ESPN has no usable pre-game price."""
    for it in odds.get('items') or []:
        provider = str((it.get('provider') or {}).get('name') or '')
        if 'live' in provider.lower() or provider.lower() in EXCLUDED:
            continue
        hp = _num((it.get('homeTeamOdds') or {}).get('moneyLine'))
        ap = _num((it.get('awayTeamOdds') or {}).get('moneyLine'))
        if hp is None or ap is None or abs(hp) < 100 or abs(ap) < 100:
            continue
        if swapped:
            hp, ap = ap, hp
        h, a = implied(hp), implied(ap)
        if not SUM_RANGE[0] <= h + a <= SUM_RANGE[1]:
            return None
        return {'source': 'espn', 'provider': provider, 'home_price': hp, 'away_price': ap,
                'home_prob': round(h / (h + a), 4)}
    return None


def kalshi_date(event_ticker: str) -> tuple[str, int | None] | None:
    """(the Eastern date '2027-04-01', the doubleheader game number or None) a Kalshi game is listed under."""
    m = EVENT.match(event_ticker)
    if not m or m.group(2) not in MONTHS:
        return None
    return f'20{m.group(1)}-{MONTHS[m.group(2)]:02d}-{m.group(3)}', int(m.group(4)) if m.group(4) else None


def _quote(m: Json, key: str) -> float | None:
    v = _num(m.get(key))
    return v if v is not None and 0 < v < 1 else None


Key = tuple[str, frozenset[str], int | None]


def kalshi_prices(feed: Json) -> dict[Key, dict[str, dict[str, float]]]:
    """Every quoted side, keyed by (date, the pair of Stats API club ids, the doubleheader game number or None),
    then by the side's club id: {'bid', 'ask', 'mid'}. Sides without both a bid and an ask inside (0, 1) are left
    out, and so is a game with fewer than two."""
    sides: dict[str, dict[str, dict[str, float]]] = {}
    for m in feed.get('markets') or []:
        event, ticker = str(m.get('event_ticker') or ''), str(m.get('ticker') or '')
        if not event.startswith('KXMLBGAME-') or not ticker.startswith(event + '-'):
            continue
        club = KALSHI_CODES.get(ticker.rsplit('-', 1)[1])
        bid, ask = _quote(m, 'yes_bid_dollars'), _quote(m, 'yes_ask_dollars')
        if club is None or bid is None or ask is None or ask < bid:
            continue
        sides.setdefault(event, {})[club] = {'bid': bid, 'ask': ask, 'mid': round((bid + ask) / 2, 4)}
    out: dict[Key, dict[str, dict[str, float]]] = {}
    for event, by_club in sides.items():
        listed = kalshi_date(event)
        if listed is not None and len(by_club) == 2:
            out[(listed[0], frozenset(by_club), listed[1])] = by_club
    return out


def kalshi_price(prices: Mapping[Key, Mapping[str, Mapping[str, float]]], game: Mapping[str, Any]
                 ) -> tuple[dict[str, Any] | None, str | None]:
    """(the fallback price, None) or (None, why there is none). A doubleheader game is looked up by its game
    number; a single game by none."""
    home, away = str(game['home']), str(game['away'])
    number = int(game['game_number']) if str(game.get('double_header') or 'N') != 'N' else None
    by_club = prices.get((str(game['slate']), frozenset((home, away)), number))
    if by_club is None:
        return None, 'Kalshi lists no quoted market for the game'
    h, a = by_club[home], by_club[away]
    return {'source': 'kalshi', 'provider': 'Kalshi', 'home_price': h['mid'], 'away_price': a['mid'],
            'home_prob': round(h['mid'] / (h['mid'] + a['mid']), 4)}, None


def price_for(game: Mapping[str, Any], espn_odds: Json | None, swapped: bool,
              kalshi: Mapping[Key, Any] | None, read_utc: datetime) -> dict[str, Any]:
    """The game's price by the registered order, always naming its source: 'espn', 'kalshi', or None with the
    reasons there is no price. `espn_odds` is None when the game has no matched ESPN event or its odds could not be
    read; `kalshi` is None when Kalshi could not be read."""
    start = game.get('start_utc')
    base = {'game_id': str(game['game_id']), 'home': str(game['home']), 'away': str(game['away']),
            'start_utc': pd.Timestamp(start).strftime('%Y-%m-%dT%H:%M:%SZ') if start is not None else None,
            'read_utc': read_utc.strftime('%Y-%m-%dT%H:%M:%SZ')}
    reasons = []
    found = espn_price(espn_odds, swapped) if espn_odds is not None else None
    if found is not None:
        return {**base, **found}
    reasons.append('ESPN has no usable pre-game price' if espn_odds is not None else 'ESPN odds not read')
    if kalshi is None:
        reasons.append('Kalshi not read')
    else:
        found, why = kalshi_price(kalshi, game)
        if found is not None:
            return {**base, **found}
        reasons.append(str(why))
    return {**base, 'source': None, 'home_prob': None, 'why': '; '.join(reasons)}


def _started(row: Mapping[str, Any]) -> bool:
    start = row.get('start_utc')
    return bool(start) and str(row['read_utc']) >= str(start)


def record(rows: Iterable[Mapping[str, Any]], path: Path) -> int:
    """Add each priced row whose source or prices differ from that game's last stored row, skipping games that have
    started. Returns the count added. The file is a JSON list, oldest first, written whole and swapped in."""
    history: list[dict[str, Any]] = json.loads(path.read_text(encoding='utf-8')) if path.exists() else []
    last = {r['game_id']: r for r in history}
    added = 0
    for r in rows:
        if r.get('source') is None or _started(r):
            continue
        prev = last.get(r['game_id'])
        key = (r['source'], r['home_price'], r['away_price'])
        if prev and (prev['source'], prev['home_price'], prev['away_price']) == key:
            continue
        history.append(dict(r))
        last[r['game_id']] = dict(r)
        added += 1
    if added:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix('.tmp')
        tmp.write_text(json.dumps(history, indent=1) + '\n', encoding='utf-8')
        tmp.replace(path)
    return added
