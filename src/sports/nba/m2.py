"""Stage 61's M2 on the live season: the injury report against who played
(Stage 84 item 4, the 2026-11-02 review).

experiments/nba/stage61/registry.json registers M2 as a measurement that
spends no slot: "Over the forward test's graded games: how far the
availability read from the injury report was from the box score's, and Model
A's log loss with each", printed on the NBA's checking page once 100 games are
graded. The backtest's availability_matchup came from the box score (who
played); a live pick's comes from the injury report (who is listed Out).

For each saved pick whose game is final and whose availability was read:
- the injury-report side is rebuilt from the pick itself, the players it
  stored as Out or suspended, through the daily run's availability_for;
- the box-score side is the backtest's own availability_table for that game,
  the number Model A was fitted on;
- Model A is refitted as the pick records (its training_through) and the
  clubs rated on games before the slate day, as the daily run does, and the
  game is scored with each availability_matchup. Only availability differs.
Picks made without availability are counted and left out. How many refitted
probabilities equal the saved ones is reported. The difference in log loss
carries a paired day-block interval (src/core/forward_test.py). Reported, not
judged: M2 is a measurement.
"""
from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.core import forward_test
from src.sports.nba import injuries, ratings

MIN_GAMES = 100
REGISTERED = 'experiments/nba/stage61/registry.json'


def measure(picks: Iterable[Mapping[str, Any]], games: pd.DataFrame, minutes: pd.DataFrame,
            table: pd.DataFrame, box: pd.Series, h: float, lam: float, columns: list[str],
            fit: Callable[[pd.DataFrame], dict[str, Any]],
            report_availability: Callable[..., float]) -> dict[str, Any]:
    """M2 over every saved pick whose game is final. `games` is prepared,
    `table` the feature table with home_prob, `box` the backtest's
    availability_table (game_id -> matchup), `fit` the daily run's
    fit_models and `report_availability` its availability_for."""
    by_id = games.set_index('game_id')
    day_of = dict(zip(games['game_id'], games['day']))
    days = pd.to_datetime(table['day'])
    fits: dict[str, Any] = {}
    rows, not_read = [], 0
    for p in picks:
        gid = str(p['game_id'])
        if gid not in by_id.index or gid not in box.index:
            continue
        if not (p.get('availability') or {}).get('read'):
            not_read += 1
            continue
        day = pd.Timestamp(p['slate'])
        through = str(p['training_through'])
        if through not in fits:
            fits[through] = fit(table[days <= pd.Timestamp(through)])['a']
        rated = ratings.day_ratings(games[games['day'] < day], day, h, lam)
        base = dict(rated.matchup(p['home'], p['away']))
        side = {}
        for s in ('home', 'away'):
            out = {r['athlete_id'] for r in (p.get('injuries') or {}).get(s, []) if r['status'] in injuries.UNAVAILABLE}
            side[s] = report_availability(minutes, day_of, p[s], day, h, out)
        matchup = {'report': side['home'] - side['away'], 'box': float(box[gid])}
        prob = {k: float(fits[through].predict_proba(pd.DataFrame([base | {'availability_matchup': v}])[columns])[0, 1])
                for k, v in matchup.items()}
        rows.append({'game_id': gid, 'day': str(p['slate']), 'home_win': float(by_id.loc[gid, 'home_win']),
                     'report_matchup': matchup['report'], 'box_matchup': matchup['box'],
                     'report': prob['report'], 'box': prob['box'],
                     'reproduced': round(prob['report'], 4) == p.get('model_a')})
    return summarise(pd.DataFrame(rows), not_read)


def summarise(frame: pd.DataFrame, not_read: int) -> dict[str, Any]:
    n = int(len(frame))
    out: dict[str, Any] = {'measurement': 'M2', 'registered': REGISTERED, 'graded': n,
                           'graded_without_availability': int(not_read), 'printed_from': MIN_GAMES, 'judged': False}
    if not n:
        return out
    gap = (frame['report_matchup'] - frame['box_matchup']).to_numpy(float)
    out['availability'] = {'mean_report_minus_box': float(gap.mean()),
                           'mean_absolute_gap': float(np.abs(gap).mean()),
                           'median_absolute_gap': float(np.median(np.abs(gap)))}
    y = frame['home_win'].to_numpy(float)
    rep = forward_test.log_losses(frame['report'].to_numpy(float), y)
    box = forward_test.log_losses(frame['box'].to_numpy(float), y)
    out['model_a'] = {'log_loss_report': float(rep.mean()), 'log_loss_box': float(box.mean())}
    if n >= 2 and frame['day'].nunique() >= 2:
        out['model_a']['box_minus_report'] = forward_test.interval(box - rep, frame['day'].to_numpy(),
                                                                   forward_test.SEEDS['nba'])
    out['refit'] = {'reproduced_saved_model_a': int(frame['reproduced'].sum()), 'of': n}
    return out


def write(path: Path, **kw: Any) -> dict[str, Any]:
    out = measure(**kw)
    path.write_text(json.dumps(out, indent=1) + '\n', encoding='utf-8')
    return out
