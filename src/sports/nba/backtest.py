"""The NBA's Stage 61 backtest, exactly as registered.

`experiments/nba/stage61/registry.json` is the plan; this file carries it
out and writes what it found to `experiments/nba/stage61/results/`:

1. **Tuning** (`tuning.json`): for each (H, lambda) in the registered grid,
   Model A walk-forward over the validation seasons 2022-23 and 2023-24,
   scored by log loss over all their games pooled. The lowest wins; ties go
   to the earlier grid entry.
2. **Confirmation** (`confirmation.json`): with that (H, lambda) fixed,
   Model A, Model A without its availability term (M1), Model B, the
   market and the home-win base rate walk-forward over 2024-25 and
   2025-26. H1 to H3 are decided by their registered rules: a paired
   bootstrap over whole game days, 5,000 resamples, seed 20261006, at
   98.33%.

Walk-forward means: before each game day, refit on every game strictly
earlier (from 2015-16), then predict that day. Model B, and the market,
only score games with a market price, and Model B only trains on such games.
The registration's games are every final regular-season, play-in and
playoff game; the history holds no others.

Run by hand: python -m src.sports.nba.backtest
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.core.day_backtest import base_rate as base_rate
from src.core.day_backtest import estimator as estimator
from src.core.day_backtest import label as label
from src.core.day_backtest import log_losses as log_losses
from src.core.day_backtest import scores as scores
from src.core.day_backtest import walk_forward as walk_forward
from src.core.sport import sport_paths
from src.sports.nba import ratings
from src.sports.nba.history import HISTORY

PATHS = sport_paths('nba')
FOLDER = PATHS.experiments / 'stage61'
REGISTRY = FOLDER / 'registry.json'
RESULTS = FOLDER / 'results'

EPS = 1e-15
SEED = 20261006
GAME_TYPES = ('regular', 'playin', 'playoff')
A_COLUMNS = ('point_matchup', 'efficiency_matchup', 'availability_matchup')


def registry() -> dict[str, Any]:
    reg: dict[str, Any] = json.loads(REGISTRY.read_text(encoding='utf-8'))
    return reg


def load_history(first: int, last: int, folder: Path = HISTORY) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(games joined to the market's home probability where there is one,
    player minutes) for seasons `first` to `last`."""
    games = pd.concat([pd.read_csv(folder / f'games_{s}.csv', dtype={'game_id': str})
                       for s in range(first, last + 1)], ignore_index=True)
    games = games[games['game_type'].isin(GAME_TYPES)]
    minutes = pd.concat([pd.read_csv(folder / f'minutes_{s}.csv', dtype={'game_id': str, 'player_id': str})
                         for s in range(first, last + 1)], ignore_index=True)
    markets = [pd.read_csv(p, dtype={'game_id': str}) for s in range(first, last + 1)
               if (p := folder / f'market_{s}.csv').exists()]
    if markets:
        market = pd.concat(markets, ignore_index=True)[['game_id', 'home_prob']]
        games = games.merge(market, on='game_id', how='left')
    else:
        games['home_prob'] = np.nan
    return games, minutes


def day_block_interval(a: pd.Series, b: pd.Series, table: pd.DataFrame, level: float,
                       n: int = 5000, seed: int = SEED) -> dict[str, float]:
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


def _table(games: pd.DataFrame, minutes: pd.DataFrame, h: float, lam: float,
           avail: pd.Series | None = None) -> pd.DataFrame:
    table = ratings.features(games, minutes, h, lam, avail=avail)
    return table.merge(games[['game_id', 'home_prob']], on='game_id', how='left')


def tune(games: pd.DataFrame, minutes: pd.DataFrame, reg: dict[str, Any]) -> dict[str, Any]:
    grid = reg['models']['model_a']['grid']
    seasons = reg['protocol']['validation_seasons']
    # Tuning never reads a game after the validation seasons.
    games = games[games['season'] <= max(seasons)]
    results = []
    for h in grid['H_days']:
        avail = ratings.availability_table(games, minutes, h)
        for lam in grid['lambda']:
            table = _table(games, minutes, h, lam, avail)
            s = scores(walk_forward(table, A_COLUMNS, seasons), table)
            results.append({'H_days': h, 'lambda': lam, **s})
            print(f'H={h} lambda={lam}: log loss {s["log_loss"]:.5f} over {s["games"]} games', flush=True)
    best = min(results, key=lambda r: r['log_loss'])  # min keeps the first of equals
    return {'seasons': seasons, 'grid': results, 'chosen': {'H_days': best['H_days'], 'lambda': best['lambda']}}


def confirm(games: pd.DataFrame, minutes: pd.DataFrame, reg: dict[str, Any], h: float, lam: float) -> dict[str, Any]:
    p = reg['protocol']
    seasons = p['confirmation_seasons']
    level = round(1 - p['alpha'] / p['budget_m'], 4)
    table = _table(games, minutes, h, lam)
    table['market_logit'] = np.log(table['home_prob'] / (1 - table['home_prob']))
    preds = {
        'model_a': walk_forward(table, A_COLUMNS, seasons),
        'model_a_no_availability': walk_forward(table, A_COLUMNS[:2], seasons),
        'model_b': walk_forward(table, [*A_COLUMNS, 'market_logit'], seasons, needs_market=True),
        'base_rate': base_rate(table, seasons),
    }
    in_seasons = table[table['season'].isin(seasons)].dropna(subset=['home_prob'])
    preds['market'] = pd.Series(in_seasons['home_prob'].to_numpy(), index=in_seasons['game_id'], name='p')
    out: dict[str, Any] = {'seasons': seasons, 'H_days': h, 'lambda': lam,
                           'scores': {name: scores(s, table) for name, s in preds.items()}}
    pairs = {'H1': ('model_a', 'base_rate'), 'H2': ('model_b', 'model_a'), 'H3': ('model_b', 'market'),
             'M1': ('model_a', 'model_a_no_availability')}
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
    raw, minutes = load_history(first, last)
    games = ratings.prepare(raw)
    tuning = tune(games, minutes, reg)
    write('tuning.json', tuning)
    chosen = tuning['chosen']
    result = confirm(games, minutes, reg, chosen['H_days'], chosen['lambda'])
    write('confirmation.json', result)
    for hid, q in result['questions'].items():
        print(f"{hid}: {q['candidate']} - {q['incumbent']} = {q['diff']:+.5f} "
              f"[{q['low']:+.5f}, {q['high']:+.5f}] {q.get('label', '(measurement)')}", flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
