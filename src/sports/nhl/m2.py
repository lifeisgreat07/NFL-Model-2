"""Stage 56's M2 on the live season: the projected starter against the actual
one (Stage 84 item 4, the 2026-11-02 review).

experiments/nhl/stage56/registry.json registers M2 as a measurement that
spends no slot: "Over the forward test's graded games: how often the
projected starter started, and Model A's log loss with each", printed on the
NHL's checking page once 50 games are graded. The backtest rated every game
with its actual starting goalie; a live pick knows only the projection. This
sizes that gap.

For each saved pick whose game is final, Model A is refitted as the pick
records it was (`training_through`: every game up to that day; the 26 picks
saved before picks recorded it are fitted on every game before the day they
were saved), the clubs are rated as of the day the pick was saved, and the
game is scored twice: with the goalies the pick used and with the two who
started (the box score's starter flags). Both probabilities come from the
same refit, so the difference is the goalies' alone. How many refitted
probabilities equal the saved ones to the four places a pick stores is
reported, so a reader can see the refit is the pick's own model.

The difference in log loss carries a paired day-block interval, as the
forward test's comparisons do (src/core/forward_test.py). Reported, not
judged: M2 is a measurement.
"""
from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from src.core import forward_test
from src.sports.nhl import backtest, ratings

MIN_GAMES = 50
REGISTERED = 'experiments/nhl/stage56/registry.json'


def run_day(pick: Mapping[str, Any]) -> pd.Timestamp:
    """The US Eastern day the pick was saved on: the day its ratings are as of."""
    return pd.Timestamp(pick['saved_utc']).tz_convert('America/New_York').normalize().tz_localize(None)


def measure(picks: Iterable[Mapping[str, Any]], games: pd.DataFrame, table: pd.DataFrame,
            box: pd.DataFrame, h: float, k: float,
            fit: Callable[[pd.DataFrame, float], tuple[Any, Any]]) -> dict[str, Any]:
    """M2 over every pick whose game has a final box score. `games` is the
    prepared history (ratings.prepare), `table` its feature table with
    home_prob, `box` this season's box scores, `fit` the daily run's fit_models."""
    cols = ['goal_matchup', 'shot_matchup', backtest.goalie_column(k)]
    by_id = box.assign(game_id=box['game_id'].astype(str)).set_index('game_id')
    days = pd.to_datetime(table['day'])
    fits: dict[pd.Timestamp, Any] = {}
    rated: dict[pd.Timestamp, Any] = {}
    rows = []
    for p in picks:
        gid = str(p['game_id'])
        if gid not in by_id.index:
            continue
        b = by_id.loc[gid]
        if pd.isna(b['home_score']) or pd.isna(b['away_score']):
            continue
        saved_on = run_day(p)
        recorded = bool(p.get('training_through'))
        through = pd.Timestamp(p['training_through']) if recorded else saved_on - pd.Timedelta(days=1)
        if through not in fits:
            fits[through] = fit(table[days <= through], k)[0]
        if saved_on not in rated:
            rated[saved_on] = ratings.day_ratings(games[games['day'] < saved_on], saved_on, h)
        used = {s: (p.get('goalies') or {}).get(s, {}).get('player_id') for s in ('home', 'away')}
        started = {'home': b['home_goalie_id'], 'away': b['away_goalie_id']}
        prob = {}
        for name, ids in (('projected', used), ('actual', started)):
            feats = rated[saved_on].matchup(p['home'], p['away'], ids['home'], ids['away'], [k])
            prob[name] = float(fits[through].predict_proba(pd.DataFrame([feats])[cols])[0, 1])
        rows.append({'game_id': gid, 'day': str(p['slate']), 'home_win': float(b['home_score'] > b['away_score']),
                     'projected': prob['projected'], 'actual': prob['actual'],
                     'home_started': bool(used['home'] == started['home']),
                     'away_started': bool(used['away'] == started['away']),
                     'reproduced': round(prob['projected'], 4) == p.get('model_a'), 'recorded': recorded})
    return summarise(pd.DataFrame(rows))


def summarise(frame: pd.DataFrame) -> dict[str, Any]:
    n = int(len(frame))
    out: dict[str, Any] = {'measurement': 'M2', 'registered': REGISTERED, 'graded': n,
                           'printed_from': MIN_GAMES, 'judged': False}
    if not n:
        return out
    y = frame['home_win'].to_numpy(float)
    proj = forward_test.log_losses(frame['projected'].to_numpy(float), y)
    act = forward_test.log_losses(frame['actual'].to_numpy(float), y)
    both = frame['home_started'] & frame['away_started']
    out['starters'] = {'sides': 2 * n, 'projected_started': int(frame['home_started'].sum() + frame['away_started'].sum()),
                       'games_both_started': int(both.sum()), 'games_a_starter_differed': int((~both).sum())}
    out['model_a'] = {'log_loss_projected': float(proj.mean()), 'log_loss_actual': float(act.mean())}
    if n >= 2 and frame['day'].nunique() >= 2:
        out['model_a']['actual_minus_projected'] = forward_test.interval(
            act - proj, frame['day'].to_numpy(), forward_test.SEEDS['nhl'])
    out['refit'] = {'reproduced_saved_model_a': int(frame['reproduced'].sum()), 'of': n,
                    'provenance_recorded': int(frame['recorded'].sum())}
    return out


def write(path: Path, picks: list[dict[str, Any]], games: pd.DataFrame, table: pd.DataFrame,
          box: pd.DataFrame, h: float, k: float,
          fit: Callable[[pd.DataFrame, float], tuple[Any, Any]]) -> dict[str, Any]:
    out = measure(picks, games, table, box, h, k, fit)
    path.write_text(json.dumps(out, indent=1) + '\n', encoding='utf-8')
    return out
