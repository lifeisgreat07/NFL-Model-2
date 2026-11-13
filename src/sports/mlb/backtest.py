"""MLB's Stage 98 backtest, as registered (experiments/mlb/stage98/registry.json). Stage 99 item 3, first part.

**Tuning** (`results/tuning.json`): for each (H, lambda, K_outs) in the registered grid, Model A walk-forward over the
validation seasons 2023 and 2024, scored by log loss over all their games pooled. The lowest wins; ties go to the
earlier grid entry. No game after the last validation season is read.

**Confirmation** (`results/confirmation.json`, `python -m src.sports.mlb.backtest confirm`): with the tuned (H,
lambda, K_outs) fixed, Model A, Model A without its starter term (M1), Model B, the market and the home-win base rate
walk-forward over 2025 and 2026, and H1 to H3 decided by their registered rules: a paired bootstrap over whole game
days, 5,000 resamples, seed 20261112, at 98.33%. Model B and the market score only games with a price
(`market_<season>.csv`, `src/sports/mlb/market_history.py`), and Model B trains only on such games. It refuses to run
until every season it reads is checked against Retrosheet, so it waits for 2026's log (the registration's
fallback_check), and both confirmation seasons are scored together, once.

Walk-forward: before each game day, refit on every game strictly earlier (from 2010), then predict that day. On a
neutral-site game the fitted intercept, the home edge, is not added to the forecast; its row still enters the fit.
Only seasons `data/mlb/history/checks.json` marks checked are read.

Run by hand: python -m src.sports.mlb.backtest            (tuning)
             python -m src.sports.mlb.backtest confirm    (confirmation, once 2026 is checked)
"""
from __future__ import annotations

import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.core.day_backtest import base_rate, estimator, label, log_losses, scores
from src.core.sport import sport_paths
from src.sports.mlb import history, ratings

PATHS = sport_paths('mlb')
FOLDER = PATHS.experiments / 'stage98'
REGISTRY = FOLDER / 'registry.json'
RESULTS = FOLDER / 'results'
SEED = 20261112


def registry() -> dict[str, Any]:
    reg: dict[str, Any] = json.loads(REGISTRY.read_text(encoding='utf-8'))
    return reg


def checked_seasons(folder: Path = history.HISTORY) -> set[int]:
    doc = json.loads((folder / 'checks.json').read_text(encoding='utf-8'))
    return {int(s) for s, c in doc.items() if c['checked']}


def load_history(first: int, last: int, folder: Path = history.HISTORY) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(games, pitcher lines) for seasons `first` to `last`. Raises if any of them is not checked against
    Retrosheet."""
    seasons = range(first, last + 1)
    unchecked = sorted(set(seasons) - checked_seasons(folder))
    if unchecked:
        raise history.HistoryError(f'seasons not checked against Retrosheet, so not used: {unchecked}')
    games = pd.concat([pd.read_csv(folder / f'games_{s}.csv', dtype={'game_id': str, 'home': str, 'away': str})
                       for s in seasons], ignore_index=True)
    lines = pd.concat([pd.read_csv(folder / f'pitchers_{s}.csv', dtype={'game_id': str, 'pitcher_id': str})
                       for s in seasons], ignore_index=True)
    return games, lines


def load_market(first: int, last: int, folder: Path = history.HISTORY) -> pd.DataFrame:
    """(game_id, home_prob) for every priced game of seasons `first` to `last`; a season with no file has none."""
    parts = [pd.read_csv(p, dtype={'game_id': str})[['game_id', 'home_prob']]
             for s in range(first, last + 1) if (p := folder / f'market_{s}.csv').exists()]
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=['game_id', 'home_prob'])


def walk_forward(table: pd.DataFrame, columns: Sequence[str], seasons: Sequence[int],
                 needs_market: bool = False) -> pd.Series:
    """Out-of-sample home-win probabilities for every game of `seasons`, refitting before each game day on every
    earlier row; a neutral-site game's forecast loses the fitted intercept. With `needs_market`, a game without a
    price is neither trained on nor predicted."""
    table = table.dropna(subset=['home_win'])  # an official tie is neither trained on nor scored
    if needs_market:
        table = table.dropna(subset=['home_prob'])
    preds: dict[str, float] = {}
    for day in sorted(table.loc[table['season'].isin(seasons), 'day'].unique()):
        train = table[table['day'] < day]
        today = table[table['day'] == day]
        model = estimator().fit(train[list(columns)], train['home_win'])
        z = model.decision_function(today[list(columns)])
        neutral = today['neutral_site'].astype(bool).to_numpy()
        z = np.where(neutral, z - float(model[-1].intercept_[0]), z)
        preds.update(zip(today['game_id'], 1.0 / (1.0 + np.exp(-z))))
    return pd.Series(preds, name='p')


def tune(games: pd.DataFrame, lines: pd.DataFrame, reg: dict[str, Any]) -> dict[str, Any]:
    grid = reg['models']['model_a']['grid']
    seasons = reg['protocol']['validation_seasons']
    games = games[games['season'] <= max(seasons)]
    results = []
    for h in grid['H_days']:
        table = ratings.features(games, lines, h, grid['lambda'], grid['K_outs'])
        for lam in grid['lambda']:
            for k in grid['K_outs']:
                cols = [f'run_matchup_{lam:g}', f'starter_matchup_{k:g}']
                s = scores(walk_forward(table, cols, seasons), table)
                results.append({'H_days': h, 'lambda': lam, 'K_outs': k, **s})
                print(f'H={h} lambda={lam} K={k}: log loss {s["log_loss"]:.5f} over {s["games"]} games', flush=True)
    best = min(results, key=lambda r: r['log_loss'])  # min keeps the first of equals
    return {'seasons': seasons, 'grid': results,
            'chosen': {'H_days': best['H_days'], 'lambda': best['lambda'], 'K_outs': best['K_outs']}}


def day_block_interval(a: pd.Series, b: pd.Series, table: pd.DataFrame, level: float,
                       n: int = 5000, seed: int = SEED) -> dict[str, float]:
    """Mean log loss of (a - b) on the games both scored, with a paired bootstrap that resamples whole game days."""
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


def confirm(games: pd.DataFrame, lines: pd.DataFrame, market: pd.DataFrame, reg: dict[str, Any],
            chosen: dict[str, Any]) -> dict[str, Any]:
    """H1 to H3 and M1 on the confirmation seasons, with the tuned settings fixed."""
    p = reg['protocol']
    seasons = p['confirmation_seasons']
    level = round(1 - p['alpha'] / p['budget_m'], 4)
    h, lam, k = chosen['H_days'], chosen['lambda'], chosen['K_outs']
    table = ratings.features(games, lines, h, [lam], [k])
    table = table.merge(market, on='game_id', how='left').dropna(subset=['home_win'])
    table['market_logit'] = np.log(table['home_prob'] / (1 - table['home_prob']))
    run, starter = f'run_matchup_{lam:g}', f'starter_matchup_{k:g}'
    preds = {
        'model_a': walk_forward(table, [run, starter], seasons),
        'model_a_no_starter': walk_forward(table, [run], seasons),
        'model_b': walk_forward(table, [run, starter, 'market_logit'], seasons, needs_market=True),
        'base_rate': base_rate(table, seasons),
    }
    priced = table[table['season'].isin(seasons)].dropna(subset=['home_prob'])
    preds['market'] = pd.Series(priced['home_prob'].to_numpy(), index=priced['game_id'], name='p')
    out: dict[str, Any] = {'seasons': seasons, **{key: chosen[key] for key in ('H_days', 'lambda', 'K_outs')},
                           'scores': {name: scores(s, table) for name, s in preds.items()}}
    pairs = {'H1': ('model_a', 'base_rate'), 'H2': ('model_b', 'model_a'), 'H3': ('model_b', 'market'),
             'M1': ('model_a', 'model_a_no_starter')}
    out['questions'] = {}
    for hid, (cand, inc) in pairs.items():
        iv = day_block_interval(preds[cand], preds[inc], table, level)
        entry: dict[str, Any] = {'candidate': cand, 'incumbent': inc, **iv}
        if hid != 'M1':
            entry['label'] = label(iv)
        out['questions'][hid] = entry
    return out


def main_confirm() -> int:
    reg = registry()
    p = reg['protocol']
    chosen = json.loads((RESULTS / 'tuning.json').read_text(encoding='utf-8'))['chosen']
    last = max(p['confirmation_seasons'])
    games, lines = load_history(p['training_from_season'], last)  # raises until every season is checked
    market = load_market(p['training_from_season'], last)
    result = confirm(ratings.prepare(games), lines, market, reg, chosen)
    (RESULTS / 'confirmation.json').write_text(json.dumps(result, indent=1) + '\n', encoding='utf-8')
    for hid, q in result['questions'].items():
        print(f"{hid}: {q['candidate']} - {q['incumbent']} = {q['diff']:+.5f} "
              f"[{q['low']:+.5f}, {q['high']:+.5f}] {q.get('label', '(measurement)')}", flush=True)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args == ['confirm']:
        return main_confirm()
    if args:
        raise SystemExit('usage: python -m src.sports.mlb.backtest [confirm]')
    reg = registry()
    p = reg['protocol']
    games, lines = load_history(p['training_from_season'], max(p['validation_seasons']))
    tuning = tune(ratings.prepare(games), lines, reg)
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / 'tuning.json').write_text(json.dumps(tuning, indent=1) + '\n', encoding='utf-8')
    c = tuning['chosen']
    print(f"chosen: H {c['H_days']}, lambda {c['lambda']}, K {c['K_outs']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
