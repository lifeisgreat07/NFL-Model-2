"""The NHL's Stage 56 backtest, exactly as registered.

`experiments/nhl/stage56/registry.json` is the plan; this file carries it
out and writes what it found to `experiments/nhl/stage56/results/`:

1. **Tuning** (`tuning.json`): for each (H, K) in the registered grid,
   Model A walk-forward over the validation seasons 2022-23 and 2023-24,
   scored by log loss over all their games pooled. The lowest wins; ties go
   to the earlier grid entry.
2. **Confirmation** (`confirmation.json`): with that (H, K) fixed, Model A,
   Model A without its goalie term (M1), Model B, the market and the
   home-win base rate walk-forward over 2024-25 and 2025-26. H1 to H3 are
   decided by their registered rules: a paired bootstrap over whole game
   days, 5,000 resamples, seed 20261005, at 98.33%.

Walk-forward means: before each game day, refit on every game strictly
earlier (from 2015-16), then predict that day. Model B, and the market,
only score games with a market price, and Model B only trains on such games.

Run by hand: python -m src.sports.nhl.backtest
"""
from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.core.sport import sport_paths
from src.sports.nhl import ratings
from src.sports.nhl.history import HISTORY

PATHS = sport_paths('nhl')
FOLDER = PATHS.experiments / 'stage56'
REGISTRY = FOLDER / 'registry.json'
RESULTS = FOLDER / 'results'

EPS = 1e-15


def registry() -> dict[str, Any]:
    reg: dict[str, Any] = json.loads(REGISTRY.read_text(encoding='utf-8'))
    return reg


def load_history(first: int, last: int, folder: Path = HISTORY) -> pd.DataFrame:
    """Box scores joined to the market's home probability where there is one."""
    box = pd.concat([pd.read_csv(folder / f'boxscores_{s}.csv', dtype={'game_id': str})
                     for s in range(first, last + 1)], ignore_index=True)
    markets = [pd.read_csv(p, dtype={'game_id': str}) for s in range(first, last + 1)
               if (p := folder / f'market_{s}.csv').exists()]
    if markets:
        market = pd.concat(markets, ignore_index=True)[['game_id', 'home_prob']]
        box = box.merge(market, on='game_id', how='left')
    else:
        box['home_prob'] = np.nan
    return box


def estimator() -> Any:
    """The registered estimator: L2 logistic regression, C=1.0, after a
    StandardScaler fitted on each refit's own rows."""
    return make_pipeline(StandardScaler(), LogisticRegression(C=1.0, l1_ratio=0.0, max_iter=1000))


def walk_forward(table: pd.DataFrame, columns: Sequence[str], seasons: Sequence[int],
                 needs_market: bool = False) -> pd.Series:
    """Out-of-sample probabilities for every game of `seasons`, refitting
    before each game day on every earlier row. With `needs_market`, rows
    without a market price are neither trained on nor predicted."""
    rows = table.dropna(subset=['home_prob']) if needs_market else table
    preds: dict[str, float] = {}
    for day in sorted(rows.loc[rows['season'].isin(seasons), 'day'].unique()):
        train = rows[rows['day'] < day]
        today = rows[rows['day'] == day]
        model = estimator().fit(train[list(columns)], train['home_win'])
        p = model.predict_proba(today[list(columns)])[:, 1]
        preds.update(zip(today['game_id'], p))
    return pd.Series(preds, name='p')


def base_rate(table: pd.DataFrame, seasons: Sequence[int]) -> pd.Series:
    """The home-win share of every earlier game, per game day."""
    preds: dict[str, float] = {}
    for day in sorted(table.loc[table['season'].isin(seasons), 'day'].unique()):
        rate = table.loc[table['day'] < day, 'home_win'].mean()
        for gid in table.loc[table['day'] == day, 'game_id']:
            preds[gid] = rate
    return pd.Series(preds, name='p')


def log_losses(p: npt.NDArray[np.float64], y: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
    p = np.clip(p, EPS, 1 - EPS)
    out: npt.NDArray[np.float64] = -(y * np.log(p) + (1 - y) * np.log(1 - p))
    return out


def scores(p: pd.Series, table: pd.DataFrame) -> dict[str, float]:
    t = table.set_index('game_id').loc[p.index]
    y, q = t['home_win'].to_numpy(float), p.to_numpy(float)
    return {'games': int(len(q)), 'log_loss': float(log_losses(q, y).mean()),
            'brier': float(((q - y) ** 2).mean()), 'accuracy': float(((q > 0.5) == (y == 1)).mean())}


def day_block_interval(a: pd.Series, b: pd.Series, table: pd.DataFrame, level: float,
                       n: int = 5000, seed: int = 20261005) -> dict[str, float]:
    """Mean log loss of (a - b) on the games both scored, with a paired
    bootstrap that resamples whole game days."""
    common = a.index.intersection(b.index)
    t = table.set_index('game_id').loc[common]
    y = t['home_win'].to_numpy(float)
    diff = log_losses(a.loc[common].to_numpy(float), y) - log_losses(b.loc[common].to_numpy(float), y)
    frame = pd.DataFrame({'day': t['day'].to_numpy(), 'diff': diff})
    per_day = frame.groupby('day')['diff'].agg(['sum', 'count'])
    sums, counts = per_day['sum'].to_numpy(), per_day['count'].to_numpy()
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(sums), size=(n, len(sums)))
    boot = sums[draws].sum(axis=1) / counts[draws].sum(axis=1)
    tail = (1 - level) / 2
    lo, hi = np.quantile(boot, [tail, 1 - tail])
    return {'games': int(len(common)), 'days': int(len(sums)), 'diff': float(diff.mean()),
            'low': float(lo), 'high': float(hi), 'level': level}


def label(interval: dict[str, float]) -> str:
    """The registered rule: ACCEPT if the interval lies below 0, REJECT if
    above, otherwise INCONCLUSIVE."""
    if interval['high'] < 0:
        return 'ACCEPT'
    if interval['low'] > 0:
        return 'REJECT'
    return 'INCONCLUSIVE'


def goalie_column(k: float) -> str:
    return f'goalie_matchup_{k:g}'


def tune(games: pd.DataFrame, reg: dict[str, Any]) -> dict[str, Any]:
    grid = reg['models']['model_a']['grid']
    seasons = reg['protocol']['validation_seasons']
    results = []
    for h in grid['H_days']:
        table = ratings.features(games, h, grid['K_shots']).merge(
            games[['game_id', 'home_prob']], on='game_id', how='left')
        for k in grid['K_shots']:
            cols = ['goal_matchup', 'shot_matchup', goalie_column(k)]
            s = scores(walk_forward(table, cols, seasons), table)
            results.append({'H_days': h, 'K_shots': k, **s})
            print(f'H={h} K={k}: log loss {s["log_loss"]:.5f} over {s["games"]} games', flush=True)
    best = min(results, key=lambda r: r['log_loss'])  # min keeps the first of equals
    return {'seasons': seasons, 'grid': results, 'chosen': {'H_days': best['H_days'], 'K_shots': best['K_shots']}}


def confirm(games: pd.DataFrame, reg: dict[str, Any], h: float, k: float) -> dict[str, Any]:
    p = reg['protocol']
    seasons = p['confirmation_seasons']
    level = round(1 - p['alpha'] / p['budget_m'], 4)
    table = ratings.features(games, h, [k]).merge(games[['game_id', 'home_prob']], on='game_id', how='left')
    a_cols = ['goal_matchup', 'shot_matchup', goalie_column(k)]
    table['market_logit'] = np.log(table['home_prob'] / (1 - table['home_prob']))
    preds = {
        'model_a': walk_forward(table, a_cols, seasons),
        'model_a_no_goalie': walk_forward(table, a_cols[:2], seasons),
        'model_b': walk_forward(table, [*a_cols, 'market_logit'], seasons, needs_market=True),
        'base_rate': base_rate(table, seasons),
    }
    in_seasons = table[table['season'].isin(seasons)].dropna(subset=['home_prob'])
    preds['market'] = pd.Series(in_seasons['home_prob'].to_numpy(), index=in_seasons['game_id'], name='p')
    out: dict[str, Any] = {'seasons': seasons, 'H_days': h, 'K_shots': k,
                           'scores': {name: scores(s, table) for name, s in preds.items()}}
    pairs = {'H1': ('model_a', 'base_rate'), 'H2': ('model_b', 'model_a'), 'H3': ('model_b', 'market'),
             'M1': ('model_a', 'model_a_no_goalie')}
    out['questions'] = {}
    for hid, (cand, inc) in pairs.items():
        iv = day_block_interval(preds[cand], preds[inc], table, level)
        entry = {'candidate': cand, 'incumbent': inc, **iv}
        if hid != 'M1':
            entry['label'] = label(iv)
        out['questions'][hid] = entry
    return out


def write(name: str, doc: dict[str, Any]) -> Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / name
    path.write_text(json.dumps(doc, indent=1) + '\n', encoding='utf-8')
    return path


def main() -> int:
    reg = registry()
    first = reg['protocol']['training_from_season']
    last = reg['protocol']['confirmation_seasons'][-1]
    games = ratings.prepare(load_history(first, last))
    tuning = tune(games, reg)
    write('tuning.json', tuning)
    chosen = tuning['chosen']
    result = confirm(games, reg, chosen['H_days'], chosen['K_shots'])
    write('confirmation.json', result)
    for hid, q in result['questions'].items():
        print(f"{hid}: {q['candidate']} - {q['incumbent']} = {q['diff']:+.5f} "
              f"[{q['low']:+.5f}, {q['high']:+.5f}] {q.get('label', '(measurement)')}", flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
