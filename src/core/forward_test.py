"""The registered forward test, scored on the season's saved picks (Stage 84 item 1).

The NHL's and the NBA's registrations (experiments/nhl/stage58/registry.json
and experiments/nba/stage65/registry.json, `forward_test.reported`) say what
the live season reports: Model A, Model B, the market and the home-win base
rate, by log loss with Brier beside it; accuracy reported and never deciding;
intervals as in the backtests (Stages 56 and 61): paired, resampling whole game
days, 5,000 resamples. The NBA's adds that picks priced by the fallback are
reported on their own as well as in the total. Until this module nothing
computed any of it: each daily run wrote a drift check and a graded list.

What is scored: every saved pick (predictions/<sport>/<season>/<game>.json)
whose game is final. Each forecaster is scored on the picks it has a number
for: Model B and the market only on priced picks. A comparison is paired, on
the games both forecasters scored, and resamples whole game days (the league or
US Eastern date the schedule files the game under).

The base rate is the backtest's: the home-win share of every game before the
pick's day, from the run's history and the season so far. Only games with a
score count; a game not yet played is not an away win.

Intervals are at the backtests' confirmatory level, 1 - 0.05/3 (98.33%), with
each sport's backtest seed. They are reported, not judged: the season-end
decision rule is a separate registered amendment (Stage 84 item 3), so this
file carries no ACCEPT or REJECT.

The daily run writes results/<sport>/forward_<season>.json with `write`.
"""
from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt
import pandas as pd

LEVEL = 1 - 0.05 / 3
N_RESAMPLES = 5000
#: The backtests' bootstrap seeds (experiments/nhl/stage56 and nba/stage61 registries).
SEEDS = {'nhl': 20261005, 'nba': 20261006}
EPS = 1e-15
FORECASTERS = ('model_a', 'model_b', 'market', 'base_rate')
#: (name, first, second): the mean of first's per-game log loss minus second's.
COMPARISONS = (('model_a_minus_base_rate', 'model_a', 'base_rate'),
               ('model_b_minus_model_a', 'model_b', 'model_a'),
               ('model_b_minus_market', 'model_b', 'market'))


def log_losses(p: npt.NDArray[np.float64], y: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    p = np.clip(p, EPS, 1 - EPS)
    out: npt.NDArray[np.float64] = -(y * np.log(p) + (1 - y) * np.log(1 - p))
    return out


def score(p: npt.NDArray[np.float64], y: npt.NDArray[np.float64]) -> dict[str, float | int]:
    """Log loss, Brier and accuracy of home probabilities `p` against outcomes `y`."""
    return {'games': int(len(p)), 'log_loss': float(log_losses(p, y).mean()),
            'brier': float(((p - y) ** 2).mean()), 'accuracy': float(((p > 0.5) == (y == 1)).mean())}


def interval(diff: npt.NDArray[np.float64], days: npt.NDArray[Any], seed: int,
             level: float = LEVEL, n: int = N_RESAMPLES) -> dict[str, float | int]:
    """Mean of `diff` with a bootstrap interval that resamples whole days:
    each draw takes len(days) days with replacement and averages over every
    game in them, as the backtests' day_block_interval does."""
    frame = pd.DataFrame({'day': days, 'diff': diff})
    per_day = frame.groupby('day')['diff'].agg(['sum', 'count'])
    sums, counts = per_day['sum'].to_numpy(float), per_day['count'].to_numpy(float)
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(sums), size=(n, len(sums)))
    boot = sums[draws].sum(axis=1) / counts[draws].sum(axis=1)
    tail = (1 - level) / 2
    lo, hi = np.quantile(boot, [tail, 1 - tail])
    return {'games': int(len(diff)), 'days': int(len(sums)), 'diff': float(diff.mean()),
            'low': float(lo), 'high': float(hi), 'level': level}


def base_rates(pick_days: Iterable[str], played: pd.DataFrame) -> dict[str, float]:
    """The home-win share of every scored game before each day, by day."""
    known = played.dropna(subset=['home_score', 'away_score'])
    known = known.assign(day=pd.to_datetime(known['day']),
                         home_win=(known['home_score'] > known['away_score']).astype(float))
    out = {}
    for day in sorted(set(pick_days)):
        before = known.loc[known['day'] < pd.Timestamp(day), 'home_win']
        if len(before):
            out[day] = float(before.mean())
    return out


def rows(picks: Iterable[Mapping[str, Any]], finals: pd.DataFrame, rates: Mapping[str, float]) -> pd.DataFrame:
    """One row per saved pick whose game is final: its day, the outcome, each
    forecaster's home probability (NaN where it has none) and the market's source."""
    final = finals.set_index('game_id')
    out = []
    for pick in picks:
        gid = str(pick['game_id'])
        if gid not in final.index:
            continue
        day = str(final.loc[gid, 'slate'])
        market = pick.get('market') or {}
        out.append({'game_id': gid, 'day': day, 'home_win': float(final.loc[gid, 'home_win']),
                    'model_a': pick.get('model_a'), 'model_b': pick.get('model_b'),
                    'market': market.get('home_prob'), 'base_rate': rates.get(day),
                    'source': pick.get('market_source') or market.get('source')})
    frame = pd.DataFrame(out, columns=['game_id', 'day', 'home_win', *FORECASTERS, 'source'])
    for col in FORECASTERS:
        frame[col] = pd.to_numeric(frame[col], errors='coerce')
    return frame


def scores(frame: pd.DataFrame) -> dict[str, dict[str, float | int]]:
    """Each forecaster scored on the picks it has a number for."""
    out = {}
    for name in FORECASTERS:
        have = frame[frame[name].notna()]
        if len(have):
            out[name] = score(have[name].to_numpy(float), have['home_win'].to_numpy(float))
    return out


def report(frame: pd.DataFrame, sport: str, season: int, registry: str) -> dict[str, Any]:
    """The whole forward-test file for one sport's season."""
    seed = SEEDS[sport]
    comparisons: dict[str, dict[str, Any]] = {}
    for name, first, second in COMPARISONS:
        both = frame[frame[first].notna() & frame[second].notna()]
        if len(both) < 2 or both['day'].nunique() < 2:
            comparisons[name] = {'games': int(len(both)), 'days': int(both['day'].nunique()),
                                 'note': 'too few games to resample'}
            continue
        y = both['home_win'].to_numpy(float)
        diff = log_losses(both[first].to_numpy(float), y) - log_losses(both[second].to_numpy(float), y)
        comparisons[name] = interval(diff, both['day'].to_numpy(), seed)
    by_source = {str(src): scores(group) for src, group in frame[frame['source'].notna()].groupby('source')}
    return {
        'sport': sport, 'season': season, 'registered': registry,
        'graded_picks': int(len(frame)),
        'through': max(frame['day']) if len(frame) else None,
        'scores': scores(frame),
        'by_market_source': by_source,
        'comparisons': comparisons,
        'interval_rule': {'level': LEVEL, 'resamples': N_RESAMPLES, 'seed': seed,
                          'blocks': 'whole game days, paired', 'judged': False},
    }


def read_picks(folder: Path) -> list[dict[str, Any]]:
    return [json.loads(p.read_text(encoding='utf-8')) for p in sorted(folder.glob('*.json'))] \
        if folder.exists() else []


def write(path: Path, sport: str, season: int, registry: str, folder: Path,
          sched: pd.DataFrame, played: pd.DataFrame) -> dict[str, Any]:
    """Score the season's saved picks and write the file. `sched` is the
    season's schedule (game_id, slate, status, home_win); `played` every game
    the run knows (day, home_score, away_score), history and season alike."""
    picks = read_picks(folder)
    finals = sched[sched['status'] == 'final'][['game_id', 'slate', 'home_win']].dropna(subset=['home_win'])
    finals = finals.assign(game_id=finals['game_id'].astype(str))
    rates = base_rates([str(d) for d in finals['slate']], played)
    out = report(rows(picks, finals, rates), sport, season, registry)
    path.write_text(json.dumps(out, indent=1) + '\n', encoding='utf-8')
    return out
