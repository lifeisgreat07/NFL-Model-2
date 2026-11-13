"""The NBA's v2 shadow in the daily run (experiments/nba/stage95_v2/registry.json, forward_test.shadow).

The run that saves a game's registered pick also saves v2's Model A and Model B forecasts for the same game, at the
same moment, from the same price, in `predictions/nba/<season>-v2/<game_id>.json`, written once and never rewritten.
v2's forecast is never the board's pick: the record carries no `pick`, and nothing that grades, draws or tests the
registered picks reads this folder (each reads `predictions/nba/<season>/`). Nothing is backfilled.

v2 as the registration fixes it, with the half-life and ridge strength its backtest chose
(`experiments/nba/stage95_v2/results/backtest.json`):

- the history is `v2.build`'s: items 27, 29 and 30. A doubled slate is placed where the backtest's own record placed
  it; one the record does not know is read from ESPN, as the backtest did;
- this season's games carry the price the runs recorded (`data/nba/lines/<season>.json`, the last read before each
  start), with item 29's band applied to it as to every earlier price;
- availability (item 24) is who played in the team's previous game, never the injury report: the game being saved is
  put in the availability walk with no box of its own;
- the price item 29 rejects gives no Model B (the record says so); a neutral-site game (item 28, the schedule's
  `neutral_site`) loses the fitted intercept;
- both models are fitted on every final game strictly before the pick's slate day.

`save` is called by `daily.main` after the registered picks are saved, through `after_save.guarded`, so a failure
here prints a DEGRADED line and never costs a registered pick.
"""
from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.core.day_picks import save_once
from src.core.provenance import training

from . import backtest, history, ratings, v2

CODE = 'nba-day-sport-v2'
A_COLUMNS = list(v2.A_COLUMNS)


def backtest_doc() -> dict[str, Any]:
    doc: dict[str, Any] = json.loads((v2.RESULTS / 'backtest.json').read_text(encoding='utf-8'))
    return doc


def chosen(doc: Mapping[str, Any]) -> tuple[float, float]:
    c = doc['tuning']['chosen']
    return float(c['H_days']), float(c['lambda'])


def season_market(lines: Iterable[Mapping[str, Any]]) -> pd.DataFrame:
    """Each game's last recorded price read before its start, with both prices, as the history's market rows."""
    best: dict[str, Mapping[str, Any]] = {}
    for r in lines:
        read, start = r.get('read_utc'), r.get('start_utc')
        if r.get('home_prob') is None or r.get('home_price') is None or not read or not start or read >= start:
            continue
        gid = str(r['game_id'])
        if gid not in best or str(read) > str(best[gid]['read_utc']):
            best[gid] = r
    return pd.DataFrame([{'game_id': g, 'home_price': float(r['home_price']), 'away_price': float(r['away_price']),
                          'home_prob': float(r['home_prob']), 'source': r.get('source')} for g, r in best.items()],
                        columns=['game_id', 'home_price', 'away_price', 'home_prob', 'source'])


def history_market(first: int, last: int, lines: Path) -> pd.DataFrame:
    """Every stored season's prices with both sides (`data/nba/history/market_<s>.csv`), then this season's recorded
    ones (`season_market`)."""
    frames = [pd.read_csv(p, dtype={'game_id': str})[['game_id', 'home_price', 'away_price', 'home_prob']]
              for s in range(first, last + 1) if (p := history.HISTORY / f'market_{s}.csv').exists()]
    recorded = json.loads(lines.read_text(encoding='utf-8')) if lines.exists() else []
    return pd.concat([*frames, season_market(recorded)], ignore_index=True)


def price_ok(price: Mapping[str, Any]) -> bool:
    """Item 29 on one live price: its two implied probabilities sum inside v2.PRICE_SUM. ESPN's prices are American
    odds; Kalshi's are already probabilities (each side's mid)."""
    if price.get('home_prob') is None or price.get('home_price') is None or price.get('away_price') is None:
        return False
    h, a = float(price['home_price']), float(price['away_price'])
    total = h + a if price.get('source') == 'kalshi' else history.implied(h) + history.implied(a)
    return v2.PRICE_SUM[0] <= total <= v2.PRICE_SUM[1]


def slate_of(doc: Mapping[str, Any], get: Callable[[str], bytes]) -> Callable[[str], str]:
    placed = dict(doc['touched']['slates_placed'])
    return lambda gid: placed[gid] if gid in placed else v2.espn_slate(gid, get)


def save(locking: pd.DataFrame, prices: Iterable[Mapping[str, Any]], raw: pd.DataFrame, minutes: pd.DataFrame,
         market: pd.DataFrame, folder: Path, now: datetime, first: int,
         get: Callable[[str], bytes] = history.fetch) -> list[str]:
    """v2's forecasts for the games the registered run just saved. `raw` is the history's games (earlier seasons
    and this one's finals), `market` every earlier price with both sides plus `season_market`'s. Returns the ids
    written now."""
    doc = backtest_doc()
    h, lam = chosen(doc)
    games, unusable, _ = v2.build(raw, minutes, market, slate_of(doc, get))
    upcoming = locking.assign(game_id=locking['game_id'].astype(str), day=pd.to_datetime(locking['slate']))
    walk = pd.concat([games[['game_id', 'day', 'home', 'away']], upcoming[['game_id', 'day', 'home', 'away']]],
                     ignore_index=True)
    avail = v2.availability_table(walk, minutes, h, unusable)
    table = v2.features(games, minutes, h, lam, unusable, avail)
    table['market_logit'] = np.log(table['home_prob'] / (1 - table['home_prob']))
    by_game = {str(p['game_id']): p for p in prices}
    written = []
    fits: dict[pd.Timestamp, tuple[Any, Any, dict[str, Any]]] = {}
    for _, g in upcoming.iterrows():
        day = pd.Timestamp(g['day'])
        if day not in fits:
            before = table[pd.to_datetime(table['day']) < day]
            priced = before.dropna(subset=['home_prob'])
            fits[day] = (backtest.estimator().fit(before[A_COLUMNS], before['home_win']),
                         backtest.estimator().fit(priced[[*A_COLUMNS, 'market_logit']], priced['home_win']),
                         training(before, first))
        model_a, model_b, trained = fits[day]
        rated = ratings.day_ratings(games[games['day'] < day], day, h, lam)
        feats = dict(rated.matchup(g['home'], g['away'])) | {'availability_matchup': float(avail[g['game_id']])}
        neutral = bool(g.get('neutral_site') or False)
        x = pd.DataFrame([feats])[A_COLUMNS]
        p_a = forecast(model_a, x, neutral)
        price = by_game.get(g['game_id'], {})
        use = price_ok(price)
        p_b = forecast(model_b, x.assign(market_logit=np.log(price['home_prob'] / (1 - price['home_prob']))),
                       False) if use else None
        record = {
            'game_id': g['game_id'], 'season': int(g['season']), 'slate': str(g['slate']),
            'start_utc': pd.Timestamp(g['start_utc']).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'home': g['home'], 'away': g['away'], 'model_a': round(p_a, 4),
            'model_b': None if p_b is None else round(p_b, 4), 'neutral_site': neutral,
            'market_source': price.get('source'), 'price_used': use,
            'price_note': None if use else ('no price' if price.get('source') is None
                                            else 'outside item 29\'s band, so no Model B'),
            'features': {k: round(float(v), 6) for k, v in feats.items()},
            'market': {k: price.get(k) for k in ('source', 'home_price', 'away_price', 'home_prob', 'read_utc')},
            'saved_utc': now.strftime('%Y-%m-%dT%H:%M:%SZ'), 'code': CODE,
            'registry': 'experiments/nba/stage95_v2/registry.json', 'H_days': h, 'lambda': lam,
            'never_a_pick': True,
        } | trained
        if save_once(record, folder):
            written.append(record['game_id'])
    return written


def forecast(model: Any, x: pd.DataFrame, neutral: bool) -> float:
    """The model's home-win probability; item 28 takes the fitted intercept off a neutral-site game. Model B is
    called with `neutral` False: its market price already carries the site (audit 8, finding S1)."""
    z = float(model.decision_function(x)[0])
    if neutral:
        z -= float(model[-1].intercept_[0])
    return float(1.0 / (1.0 + np.exp(-z)))
