"""The NHL's v3 shadow in the daily run (experiments/nhl/stage105_v3/registry.json, forward_test.shadow).

The run that saves a game's registered pick also saves v3's Model A and Model B forecasts for it, at the same moment,
from the same price and the same goalies, in `predictions/nhl/<season>-v3/<game_id>.json`, written once and never
rewritten. Like v2's, a v3 record carries no `pick`, and nothing that grades, draws or tests the registered picks,
or decides v2, reads this folder. Nothing is backfilled: the daily run passes only the games whose pick it saved
itself (audit 8, finding B2).

v3 is v2 (src/sports/nhl/v2_shadow.py: the same history, H and K, price band and goalies) with `b2b_matchup` added
to both models' features (src/sports/nhl/v3.py). Neutral site: Model A loses the fitted intercept; Model B keeps it.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.core.day_picks import save_once
from src.core.provenance import training

from . import ratings, v2, v2_shadow, v3
from .backtest import estimator

CODE = 'nhl-day-sport-v3'


def forecast(model: Any, x: pd.DataFrame, neutral: bool, drop_intercept: bool) -> float:
    z = float(model.decision_function(x)[0])
    if neutral and drop_intercept:
        z -= float(model[-1].intercept_[0])
    return float(1.0 / (1.0 + np.exp(-z)))


def save(locking: pd.DataFrame, lines: Mapping[str, Mapping[str, Any]], goalie_ids: Mapping[str, tuple[Any, Any]],
         raw: pd.DataFrame, market: pd.DataFrame, sched: pd.DataFrame, folder: Path, now: datetime,
         first: int) -> list[str]:
    """v3's forecasts for the games the registered run just saved; the arguments are v2_shadow.save's. Returns the
    ids written now."""
    doc = v2_shadow.backtest_doc()
    h, k = v2_shadow.chosen(doc)
    neutral = set(doc['touched']['neutral_games']) | set(
        sched.loc[sched['neutral_site'].fillna(False).astype(bool), 'game_id'].astype(str))
    games, unusable, _ = v2.build(raw, market, neutral)
    ks = [] if k is None else [k]
    table = v2.table_for(games, h, ks, unusable)
    played = v3.played_days(games)
    table[v3.B2B] = v3.b2b_matchup(table, played)
    table['market_logit'] = np.log(table['home_prob'] / (1 - table['home_prob']))
    a_cols = v3.model_a_columns(v2.model_a_columns(k))
    usable = games[~games['game_id'].astype(str).isin(unusable)]
    written = []
    fits: dict[pd.Timestamp, tuple[Any, Any, dict[str, Any]]] = {}
    for _, g in locking.iterrows():
        gid, day = str(g['game_id']), pd.Timestamp(str(g['slate']))
        if day not in fits:
            before = table[pd.to_datetime(table['day']) < day]
            priced = before.dropna(subset=['home_prob'])
            fits[day] = (estimator().fit(before[a_cols], before['home_win']),
                         estimator().fit(priced[[*a_cols, 'market_logit']], priced['home_win']),
                         training(before, first))
        model_a, model_b, trained = fits[day]
        rated = ratings.day_ratings(usable[usable['day'] < day], day, h)
        home_goalie, away_goalie = (None if v is None else int(v) for v in goalie_ids.get(gid, (None, None)))
        feats = dict(rated.matchup(g['home'], g['away'], home_goalie, away_goalie, ks))
        feats[v3.B2B] = float(v3.b2b_matchup(pd.DataFrame([{'day': day, 'home': g['home'], 'away': g['away']}]),
                                             played).iloc[0])
        is_neutral = gid in neutral
        x = pd.DataFrame([feats])[a_cols]
        p_a = forecast(model_a, x, is_neutral, drop_intercept=True)
        line = lines.get(gid)
        use = v2_shadow.price_ok(line)
        p_b = forecast(model_b, x.assign(market_logit=np.log(line['home_prob'] / (1 - line['home_prob']))),
                       is_neutral, drop_intercept=False) if use and line is not None else None
        record = {
            'game_id': gid, 'season': int(g['season']), 'slate': str(g['slate']),
            'start_utc': pd.Timestamp(g['start_utc']).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'home': g['home'], 'away': g['away'], 'model_a': round(p_a, 4),
            'model_b': None if p_b is None else round(p_b, 4), 'neutral_site': is_neutral, 'price_used': use,
            'price_note': None if use else ('no price' if line is None else "outside item 29's band, so no Model B"),
            'features': {key: round(float(v), 6) for key, v in feats.items()},
            'goalies': {'home': home_goalie, 'away': away_goalie, 'used': k is not None},
            'market': None if line is None else {key: line.get(key) for key in
                                                 ('home_price', 'away_price', 'home_prob', 'read_utc')},
            'saved_utc': now.strftime('%Y-%m-%dT%H:%M:%SZ'), 'code': CODE,
            'registry': 'experiments/nhl/stage105_v3/registry.json', 'H_days': h, 'K_shots': k,
            'never_a_pick': True,
        } | trained
        if save_once(record, folder):
            written.append(gid)
    return written
