"""The market's price for each NBA game at the run that saves its pick (Stage 65).

`experiments/nba/stage65/registry.json` fixes the order, and this file
carries it out:

1. **ESPN** (`espn_price`): the game's odds from ESPN's core API, the
   backtest's own source. The first listed provider that is not marked live
   and is not a projection site, read at its current moneyline, the margin
   taken out evenly. ESPN writes 0 for a price it does not have, and no
   American price lies between -100 and +100, so such a side is no price.
2. **Kalshi** (`kalshi_prices`), only for a game ESPN gave no price: the
   game-winner market (series KXNBAGAME). Each side's price is the midpoint
   of its yes bid and ask; the home probability is the home midpoint over
   the two. Used only when both sides are quoted (bid above 0, ask below 1)
   and each side's ask minus bid is at most `KALSHI_MAX_SPREAD`.
3. **None**: Model B is not run for the game and the pick says "no price".

Whichever it is, `price_for` returns the source by name, so a pick can
never be priced from somewhere it does not say. `record` keeps every read
in `data/nba/lines/<season>.json` the way the NHL's lines are kept: a row
only when the price moves, and nothing once the game has started.

Kalshi names a game by its Eastern date and the two clubs' codes
(`KXNBAGAME-26OCT21ATLORL`), and a side by the code after the last dash.
Its codes are the league's three-letter ones; six differ from ESPN's
(`KALSHI_TO_ESPN`). A game is matched by date and the pair of clubs, not
by the order the code lists them in.
"""
from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

ESPN_ODDS = ('https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba/'
             'events/{e}/competitions/{e}/odds')
KALSHI = 'https://api.elections.kalshi.com/trade-api/v2/markets?series_ticker=KXNBAGAME&status=open&limit=1000'
#: Providers ESPN lists that publish a projection, not a price (as in the history).
PROJECTIONS = frozenset({'numberfire', 'teamrankings'})
#: The registration's widest accepted Kalshi spread, per side, in dollars.
KALSHI_MAX_SPREAD = 0.05
KALSHI_TO_ESPN: Mapping[str, str] = {'GSW': 'GS', 'NOP': 'NO', 'NYK': 'NY', 'SAS': 'SA', 'UTA': 'UTAH', 'WAS': 'WSH'}
MONTHS = {m: i + 1 for i, m in enumerate(('JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN',
                                          'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'))}
EVENT = re.compile(r'^KXNBAGAME-(\d{2})([A-Z]{3})(\d{2})[A-Z]+$')

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


def espn_price(odds: Json) -> dict[str, Any] | None:
    """(provider, home price, away price, home probability) from ESPN's odds
    for one game, or None when ESPN has no usable pre-game price."""
    for it in odds.get('items') or []:
        provider = str((it.get('provider') or {}).get('name') or '')
        if 'live' in provider.lower() or provider.lower() in PROJECTIONS:
            continue
        hp = _num((it.get('homeTeamOdds') or {}).get('moneyLine'))
        ap = _num((it.get('awayTeamOdds') or {}).get('moneyLine'))
        if hp is None or ap is None or abs(hp) < 100 or abs(ap) < 100:
            continue
        h, a = implied(hp), implied(ap)
        return {'source': 'espn', 'provider': provider, 'home_price': hp, 'away_price': ap,
                'home_prob': round(h / (h + a), 4)}
    return None


def kalshi_date(event_ticker: str) -> str | None:
    """The Eastern date ('2026-10-21') a Kalshi game is listed under."""
    m = EVENT.match(event_ticker)
    if not m or m.group(2) not in MONTHS:
        return None
    return f'20{m.group(1)}-{MONTHS[m.group(2)]:02d}-{m.group(3)}'


def _quote(m: Json, key: str) -> float | None:
    v = _num(m.get(key))
    return v if v is not None and 0 < v < 1 else None


def kalshi_prices(feed: Json) -> dict[tuple[str, frozenset[str]], dict[str, dict[str, float]]]:
    """Every quoted side, keyed by (date, the pair of ESPN codes), then by the
    side's ESPN code: {'bid', 'ask', 'mid'}. Sides without both a bid and an
    ask inside (0, 1) are left out."""
    sides: dict[str, dict[str, dict[str, float]]] = {}
    for m in feed.get('markets') or []:
        event, ticker = str(m.get('event_ticker') or ''), str(m.get('ticker') or '')
        if not event.startswith('KXNBAGAME-') or not ticker.startswith(event + '-'):
            continue
        code = ticker.rsplit('-', 1)[1]
        bid, ask = _quote(m, 'yes_bid_dollars'), _quote(m, 'yes_ask_dollars')
        if bid is None or ask is None or ask < bid:
            continue
        sides.setdefault(event, {})[KALSHI_TO_ESPN.get(code, code)] = {
            'bid': bid, 'ask': ask, 'mid': round((bid + ask) / 2, 4)}
    out = {}
    for event, by_team in sides.items():
        day = kalshi_date(event)
        if day is not None and len(by_team) == 2:
            out[(day, frozenset(by_team))] = by_team
    return out


def kalshi_price(prices: Mapping[tuple[str, frozenset[str]], Mapping[str, Mapping[str, float]]],
                 day: str, home: str, away: str) -> tuple[dict[str, Any] | None, str | None]:
    """(the fallback price, None) or (None, why there is none)."""
    by_team = prices.get((day, frozenset((home, away))))
    if by_team is None:
        return None, 'Kalshi lists no quoted market for the game'
    h, a = by_team[home], by_team[away]
    widest = max(h['ask'] - h['bid'], a['ask'] - a['bid'])
    if widest > KALSHI_MAX_SPREAD + 1e-9:
        return None, f'Kalshi spread {widest:.2f} is wider than {KALSHI_MAX_SPREAD:.2f}'
    return {'source': 'kalshi', 'provider': 'Kalshi', 'home_price': h['mid'], 'away_price': a['mid'],
            'home_prob': round(h['mid'] / (h['mid'] + a['mid']), 4)}, None


def price_for(game: Mapping[str, Any], espn_odds: Json | None, kalshi: Mapping[Any, Any] | None,
              read_utc: datetime) -> dict[str, Any]:
    """The game's price by the registered order, always naming its source:
    'espn', 'kalshi', or None with the reasons there is no price."""
    base = {'game_id': str(game['game_id']), 'home': game['home'], 'away': game['away'],
            'start_utc': game.get('start_utc'), 'read_utc': read_utc.strftime('%Y-%m-%dT%H:%M:%SZ')}
    reasons = []
    found = espn_price(espn_odds) if espn_odds is not None else None
    if found is not None:
        return {**base, **found}
    reasons.append('ESPN has no pre-game price' if espn_odds is not None else 'ESPN odds not read')
    if kalshi is None:
        reasons.append('Kalshi not read')
    else:
        found, why = kalshi_price(kalshi, str(game['slate']), game['home'], game['away'])
        if found is not None:
            return {**base, **found}
        reasons.append(str(why))
    return {**base, 'source': None, 'home_prob': None, 'why': '; '.join(reasons)}


def _started(row: Mapping[str, Any]) -> bool:
    start = row.get('start_utc')
    return bool(start) and str(row['read_utc']) >= str(start)


def record(rows: Iterable[Mapping[str, Any]], path: Path) -> int:
    """Add each priced row whose source or prices differ from that game's
    last stored row, skipping games that have started. Returns the count
    added. The file is a JSON list, oldest first, written whole and swapped in."""
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
