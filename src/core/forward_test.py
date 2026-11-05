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

Stage 84 item 5 adds each model's calibration intercept and slope (a
logistic recalibration of its home probability), with intervals from the
same day blocks, level and seed. Reported, not judged, like the rest.

The daily run writes results/<sport>/forward_<season>.json with `write`.

Stage 95 item 36 (audit 7 M15): the registered decision is taken once, on
the file the first daily run writes after the regular season's last game
is final. Until now nothing kept that file: the next run overwrote it with
playoff games added. `freeze` copies it, once, to
results/<sport>/forward_<season>_regular_season_final.json and writes the
registered label beside each comparison there, and only there.
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
#: The models whose calibration is reported (Stage 84 item 5).
CALIBRATED = ('model_a', 'model_b')


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


def _logit(p: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    p = np.clip(p, EPS, 1 - EPS)
    out: npt.NDArray[np.float64] = np.log(p / (1 - p))
    return out


def recalibrate(x: npt.NDArray[np.float64], y: npt.NDArray[np.float64], w: npt.NDArray[np.float64],
                slope_free: bool, iters: int = 25) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    """Weighted logistic regression of the outcome `y` on `x`, the forecast's
    log-odds, for every row of weights `w` at once (shape draws x games).

    slope_free=False fits the calibration intercept: logit P(home win) =
    a + x, the slope held at 1 (calibration in the large). slope_free=True
    fits the calibration slope: logit P(home win) = a + b * x. Perfect
    calibration is intercept 0 and slope 1; a slope below 1 means the
    forecasts are too far from 50%. Returns (a, b) per row, by Newton's method.
    """
    a = np.zeros(len(w))
    b = np.ones(len(w))
    for _ in range(iters):
        p = 1 / (1 + np.exp(-(a[:, None] + b[:, None] * x[None, :])))
        r = w * (y[None, :] - p)
        v = w * p * (1 - p)
        if not slope_free:
            a = a + r.sum(axis=1) / v.sum(axis=1)
            continue
        g0, g1 = r.sum(axis=1), (r * x).sum(axis=1)
        h00, h01, h11 = v.sum(axis=1), (v * x).sum(axis=1), (v * x * x).sum(axis=1)
        det = h00 * h11 - h01 ** 2
        a = a + (h11 * g0 - h01 * g1) / det
        b = b + (h00 * g1 - h01 * g0) / det
    return a, b


def calibration(p: npt.NDArray[np.float64], y: npt.NDArray[np.float64], days: npt.NDArray[Any], seed: int,
                level: float = LEVEL, n: int = N_RESAMPLES) -> dict[str, Any]:
    """Calibration intercept and slope of home probabilities `p`, each with a
    bootstrap interval that resamples whole game days as `interval` does:
    a draw takes len(days) days with replacement, and each game counts as
    many times as its day was drawn."""
    x = _logit(p)
    codes, uniq = pd.factorize(pd.Series(days))
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(uniq), size=(n, len(uniq)))
    per_day = np.stack([np.bincount(row, minlength=len(uniq)) for row in draws]).astype(float)
    weights = per_day[:, codes]
    one = np.ones((1, len(p)))
    tail = (1 - level) / 2
    out: dict[str, Any] = {'games': int(len(p)), 'days': int(len(uniq)), 'level': level}
    for name, free, pick in (('intercept', False, 0), ('slope', True, 1)):
        with np.errstate(all='ignore'):
            point = recalibrate(x, y, one, free)[pick][0]
            boot = recalibrate(x, y, weights, free)[pick]
        # A draw whose fit has no finite answer (every drawn game a home win,
        # say) is left out of the quantiles and counted, not hidden.
        ok = np.isfinite(boot)
        if not np.isfinite(point) or not ok.any():
            # No finite fit on the games themselves: a slope cannot be fitted
            # to forecasts that never vary, nor anything to one outcome only.
            out[name] = {'value': None, 'low': None, 'high': None, 'draws_unfit': int((~ok).sum()),
                         'note': 'no finite fit'}
            continue
        lo, hi = np.quantile(boot[ok], [tail, 1 - tail])
        out[name] = {'value': float(point), 'low': float(lo), 'high': float(hi), 'draws_unfit': int((~ok).sum())}
    return out


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
    # Stage 84 item 5: calibration intercept and slope for Models A and B,
    # each on the picks it has a number for. Reported, not judged.
    calib: dict[str, dict[str, Any]] = {}
    for name in CALIBRATED:
        have = frame[frame[name].notna()]
        if len(have) < 2 or have['day'].nunique() < 2:
            calib[name] = {'games': int(len(have)), 'days': int(have['day'].nunique()),
                           'note': 'too few games to resample'}
            continue
        calib[name] = calibration(have[name].to_numpy(float), have['home_win'].to_numpy(float),
                                  have['day'].to_numpy(), seed)
    by_source = {str(src): scores(group) for src, group in frame[frame['source'].notna()].groupby('source')}
    return {
        'sport': sport, 'season': season, 'registered': registry,
        'graded_picks': int(len(frame)),
        'through': max(frame['day']) if len(frame) else None,
        'scores': scores(frame),
        'by_market_source': by_source,
        'comparisons': comparisons,
        'calibration': calib,
        'interval_rule': {'level': LEVEL, 'resamples': N_RESAMPLES, 'seed': seed,
                          'blocks': 'whole game days, paired', 'judged': False},
    }


def label(comparison: Mapping[str, Any]) -> str:
    """The registered rule (`forward_test.decision.rule`): ACCEPT when the whole
    interval is below zero, REJECT when it is above, INCONCLUSIVE otherwise,
    and for a comparison too small to resample."""
    if 'high' not in comparison:
        return 'INCONCLUSIVE'
    if comparison['high'] < 0:
        return 'ACCEPT'
    if comparison['low'] > 0:
        return 'REJECT'
    return 'INCONCLUSIVE'


def regular_season_over(sched: pd.DataFrame) -> bool:
    """Every regular-season game on the schedule is final or cancelled."""
    regular = sched[sched['game_type'] == 'regular']
    return bool(len(regular)) and bool(regular['status'].isin(['final', 'cancelled']).all())


def freeze(path: Path, sched: pd.DataFrame, today: str) -> Path | None:
    """Once the regular season is over, copy the forward-test file at `path` to
    its `_regular_season_final` twin with each comparison's label, and return
    the twin. A twin already there is never rewritten (None is returned), so
    the deciding file is the first one written after the last game."""
    frozen = path.with_name(path.stem + '_regular_season_final.json')
    if frozen.exists() or not regular_season_over(sched):
        return None
    doc = json.loads(path.read_text(encoding='utf-8'))
    doc['frozen'] = {'on': today, 'from': path.name,
                     'rule': 'forward_test.decision in the registration this file names'}
    doc['decision'] = {name: label(c) for name, c in doc['comparisons'].items()}
    frozen.write_text(json.dumps(doc, indent=1) + '\n', encoding='utf-8')
    return frozen


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
