"""The NHL's v2 shadow in the daily run (experiments/nhl/stage95_v2/registry.json, forward_test.shadow).

The run that saves a game's registered pick also saves v2's Model A and Model B forecasts for the same game, at the
same moment, from the same price and the same goalies, in `predictions/nhl/<season>-v2/<game_id>.json`, written once
and never rewritten. v2's forecast is never the board's pick: the record carries no `pick`, and nothing that grades,
draws or tests the registered picks reads this folder (each reads `predictions/nhl/<season>/`). Nothing is
backfilled.

v2 as the registration fixes it, with the half-life and K its backtest chose
(`experiments/nhl/stage95_v2/results/backtest.json`; K None is the goalie term removed):

- the history is `v2.build`'s: item 29 on every price and box score, earlier seasons' and this season's recorded
  ones (`data/nhl/lines/<season>.json`, the last read before each start);
- a neutral-site game (item 28) is one the league's schedule flags: the backtest's own list for earlier seasons, the
  schedule this run read for this one. Its forecast loses the fitted intercept;
- the live price is held to item 29's two-way band; a price outside it gives no Model B, and the record says so;
- both models are fitted on every final game strictly before the pick's slate day.

`save` is called by `daily.main` after the registered picks are saved, through `after_save.guarded`, so a failure
here prints a DEGRADED line and never costs a registered pick.
"""
from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.core.day_picks import save_once
from src.core.provenance import training

from . import history, ratings, v2
from .backtest import estimator
from .market import implied

CODE = 'nhl-day-sport-v2'


def backtest_doc() -> dict[str, Any]:
    doc: dict[str, Any] = json.loads((v2.RESULTS / 'backtest.json').read_text(encoding='utf-8'))
    return doc


def chosen(doc: Mapping[str, Any]) -> tuple[float, float | None]:
    c = doc['tuning']['chosen']
    return float(c['H_days']), None if c['K_shots'] is None else float(c['K_shots'])


def season_market(lines: Iterable[Mapping[str, Any]]) -> pd.DataFrame:
    """Each game's last recorded price read before its start, as the history's market rows (two-way, native)."""
    best: dict[str, Mapping[str, Any]] = {}
    for r in lines:
        read, start = r.get('read_utc'), r.get('start_utc')
        if r.get('home_prob') is None or r.get('home_price') is None or not read or not start or read >= start:
            continue
        gid = str(r['game_id'])
        if gid not in best or str(read) > str(best[gid]['read_utc']):
            best[gid] = r
    return pd.DataFrame([{'game_id': g, 'home_price': float(r['home_price']), 'away_price': float(r['away_price']),
                          'home_prob': float(r['home_prob']), 'converted': False} for g, r in best.items()],
                        columns=['game_id', 'home_price', 'away_price', 'home_prob', 'converted'])


def history_market(first: int, last: int, lines: Path) -> pd.DataFrame:
    """Every stored season's prices (`data/nhl/history/market_<s>.csv`), then this season's recorded ones."""
    frames = [pd.read_csv(p, dtype={'game_id': str})[['game_id', 'home_price', 'away_price', 'home_prob', 'converted']]
              for s in range(first, last + 1) if (p := history.HISTORY / f'market_{s}.csv').exists()]
    recorded = json.loads(lines.read_text(encoding='utf-8')) if lines.exists() else []
    return pd.concat([*frames, season_market(recorded)], ignore_index=True)


def price_ok(line: Mapping[str, Any] | None) -> bool:
    """Item 29 on one live price: the two-way line's implied probabilities sum inside v2.TWO_WAY_SUM."""
    if not line or line.get('home_prob') is None or line.get('home_price') is None or line.get('away_price') is None:
        return False
    total = implied(float(line['home_price'])) + implied(float(line['away_price']))
    return v2.TWO_WAY_SUM[0] <= total <= v2.TWO_WAY_SUM[1]


def forecast(model: Any, x: pd.DataFrame, neutral: bool) -> float:
    """The model's home-win probability; item 28 takes the fitted intercept off a neutral-site game. Model B is
    called with `neutral` False: its market price already carries the site (audit 8, finding S1)."""
    z = float(model.decision_function(x)[0])
    if neutral:
        z -= float(model[-1].intercept_[0])
    return float(1.0 / (1.0 + np.exp(-z)))


def save(locking: pd.DataFrame, lines: Mapping[str, Mapping[str, Any]], goalie_ids: Mapping[str, tuple[Any, Any]],
         raw: pd.DataFrame, market: pd.DataFrame, sched: pd.DataFrame, folder: Path, now: datetime,
         first: int) -> list[str]:
    """v2's forecasts for the games the registered run just saved. `raw` is the history's box scores (earlier
    seasons and this one's finals), `market` every price with both sides, `goalie_ids` the goalies the registered
    pick used. Returns the ids written now."""
    doc = backtest_doc()
    h, k = chosen(doc)
    neutral = set(doc['touched']['neutral_games']) | set(
        sched.loc[sched['neutral_site'].fillna(False).astype(bool), 'game_id'].astype(str))
    games, unusable, _ = v2.build(raw, market, neutral)
    ks = [] if k is None else [k]
    table = v2.table_for(games, h, ks, unusable)
    table['market_logit'] = np.log(table['home_prob'] / (1 - table['home_prob']))
    a_cols = v2.model_a_columns(k)
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
        feats = rated.matchup(g['home'], g['away'], home_goalie, away_goalie, ks)
        is_neutral = gid in neutral
        x = pd.DataFrame([feats])[a_cols]
        p_a = forecast(model_a, x, is_neutral)
        line = lines.get(gid)
        use = price_ok(line)
        p_b = forecast(model_b, x.assign(market_logit=np.log(line['home_prob'] / (1 - line['home_prob']))),
                       False) if use and line is not None else None
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
            'registry': 'experiments/nhl/stage95_v2/registry.json', 'H_days': h, 'K_shots': k,
            'never_a_pick': True,
        } | trained
        if save_once(record, folder):
            written.append(gid)
    return written
