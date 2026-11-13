"""The NBA's v3 shadow in the daily run (experiments/nba/stage105_v3/registry.json, forward_test.shadow).

The run that saves a game's registered pick also saves v3's Model A and Model B forecasts for it, at the same moment,
from the same price, in `predictions/nba/<season>-v3/<game_id>.json`, written once and never rewritten. A v3 record
carries no `pick`, and nothing that grades, draws or tests the registered picks, or decides v2, reads this folder.
Nothing is backfilled: the daily run passes only the games whose pick it saved itself (audit 8, finding B2).

v3 is v2 (src/sports/nba/v2_shadow.py: the same history, H and lambda, price rules) with availability star-weighted
and `b2b_matchup` added (src/sports/nba/v3.py). Neutral site: Model A loses the fitted intercept; Model B keeps it.
"""
from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.core.day_picks import save_once
from src.core.provenance import training

from . import backtest, history, ratings, v2, v2_shadow, v3

CODE = 'nba-day-sport-v3'
A_COLUMNS = v3.model_a_columns(list(v2.A_COLUMNS))


def forecast(model: Any, x: pd.DataFrame, neutral: bool, drop_intercept: bool) -> float:
    z = float(model.decision_function(x)[0])
    if neutral and drop_intercept:
        z -= float(model[-1].intercept_[0])
    return float(1.0 / (1.0 + np.exp(-z)))


def save(locking: pd.DataFrame, prices: Iterable[Mapping[str, Any]], raw: pd.DataFrame, minutes: pd.DataFrame,
         market: pd.DataFrame, folder: Path, now: datetime, first: int,
         get: Callable[[str], bytes] = history.fetch) -> list[str]:
    """v3's forecasts for the games the registered run just saved; the arguments are v2_shadow.save's. Returns the
    ids written now."""
    doc = v2_shadow.backtest_doc()
    h, lam = v2_shadow.chosen(doc)
    games, unusable, _ = v2.build(raw, minutes, market, v2_shadow.slate_of(doc, get))
    upcoming = locking.assign(game_id=locking['game_id'].astype(str), day=pd.to_datetime(locking['slate']))
    walk = pd.concat([games[['game_id', 'day', 'home', 'away']], upcoming[['game_id', 'day', 'home', 'away']]],
                     ignore_index=True)
    avail = v2.availability_table(walk, minutes, h, unusable, power=v3.STAR_POWER)
    table = v2.features(games, minutes, h, lam, unusable, avail)
    played = v3.played_days(games)
    table[v3.B2B] = v3.b2b_matchup(table, played)
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
        feats = dict(rated.matchup(g['home'], g['away'])) | {
            'availability_matchup': float(avail[g['game_id']]),
            v3.B2B: float(v3.b2b_matchup(pd.DataFrame([{'day': day, 'home': g['home'], 'away': g['away']}]),
                                         played).iloc[0])}
        neutral = bool(g.get('neutral_site') or False)
        x = pd.DataFrame([feats])[A_COLUMNS]
        p_a = forecast(model_a, x, neutral, drop_intercept=True)
        price = by_game.get(g['game_id'], {})
        use = v2_shadow.price_ok(price)
        p_b = forecast(model_b, x.assign(market_logit=np.log(price['home_prob'] / (1 - price['home_prob']))),
                       neutral, drop_intercept=False) if use else None
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
            'registry': 'experiments/nba/stage105_v3/registry.json', 'H_days': h, 'lambda': lam,
            'star_power': v3.STAR_POWER, 'never_a_pick': True,
        } | trained
        if save_once(record, folder):
            written.append(record['game_id'])
    return written
