"""MLB's drift check: is live Model A doing worse than its backtest said? (Stage 101 item 3)

As `experiments/mlb/stage101/registry.json` (`drift`) registers it, with the NBA's two amendments written in from
the start:

- **Looks:** five, after 100, 200, 400, 800 and 1,600 graded regular-season picks (`CHECKPOINTS`), each on the
  first that many graded picks in the order their games start. Each look is one-sided at 99% on its own
  (`LEVEL`). A flag at any look stands for the season.
- **Baselines:** each look has its own, Model A's backtest log loss over a season's first n games, Stage 98's
  confirmation seasons pooled. `baselines_from` computes them from the confirmation's per-game file
  (`experiments/mlb/stage98/results/confirmation_games.csv`, written by `backtest confirm`), and `write_baseline`
  commits them to `data/mlb/drift_baseline.json` before the first pick. Until that file exists the check does not
  run (`check` says why); a look is never held to a baseline written from another season.
- **The test:** flag when the lower end of the one-sided 99% bootstrap interval of the look's mean per-game log loss
  is above that look's baseline, resampling whole game days, each resample the pooled mean of the days drawn
  (`src.core.day_drift.lower_bound`). 5,000 resamples with Stage 98's seed, 20261112 (`N_RESAMPLES`, `SEED`):
  the registry names neither, so the backtest's are used.

A flag is a reason to look, not proof that something broke: the backtest knew who started, and a live pick knows
only the probable pitcher, or none.

Run by hand once the confirmation has run: python -m src.sports.mlb.drift baseline
"""
from __future__ import annotations

import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.core.day_drift import lower_bound, per_game_log_loss
from src.core.sport import sport_paths

PATHS = sport_paths('mlb')
BASELINE = PATHS.data / 'drift_baseline.json'
CONFIRMATION_GAMES = PATHS.experiments / 'stage98' / 'results' / 'confirmation_games.csv'
CHECKPOINTS = (100, 200, 400, 800, 1600)
LEVEL = 0.99
N_RESAMPLES = 5000
SEED = 20261112
RULE: dict[str, Any] = {'checkpoints': list(CHECKPOINTS), 'per_look_level': LEVEL, 'n_resamples': N_RESAMPLES,
                        'seed': SEED, 'resample': 'whole game days'}


def baselines_from(games: pd.DataFrame) -> dict[str, float]:
    """For each look at n: Model A's log loss over each confirmation season's first n scored games (in the order
    they were played), the seasons pooled."""
    games = games.dropna(subset=['model_a', 'home_win'])
    out = {}
    for n in CHECKPOINTS:
        first = pd.concat([g.head(n) for _, g in games.groupby('season', sort=True)])
        losses = per_game_log_loss(zip(first['model_a'].astype(float), first['home_win'].astype(int), strict=True))
        out[str(n)] = float(np.mean(losses))
    return out


def write_baseline(source: Path = CONFIRMATION_GAMES, path: Path = BASELINE) -> dict[str, Any]:
    """Write the drift file from the confirmation's per-game file. Refuses to overwrite one already written."""
    if path.exists():
        raise SystemExit(f'{path.name} exists: the baselines are written once, before the first pick')
    games = pd.read_csv(source, dtype={'game_id': str})
    games = games.sort_values(['season', 'day', 'start_utc', 'game_id'], kind='stable')
    spec = {'registered': 'experiments/mlb/stage101/registry.json, drift', 'model': 'model_a', 'metric': 'log_loss',
            'source': (source.relative_to(PATHS.root) if source.is_relative_to(PATHS.root) else source).as_posix(),
            'seasons': sorted(int(s) for s in games['season'].unique()), 'rule': RULE,
            'baseline_by_look': baselines_from(games)}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(spec, indent=1) + '\n', encoding='utf-8')
    return spec


def looks(losses: Sequence[float], days: Sequence[str], spec: dict[str, Any]) -> list[dict[str, Any]]:
    """Every registered look the graded picks have reached, in order. `losses` and `days` are the graded
    regular-season picks' per-game log loss and game day, in the order their games started."""
    if len(losses) != len(days):
        raise ValueError(f'{len(days)} days for {len(losses)} losses')
    rule = {'n_resamples': N_RESAMPLES, 'seed': SEED, 'one_sided_level': LEVEL}
    out = []
    for n in CHECKPOINTS:
        if len(losses) < n:
            break
        bound = lower_bound(list(losses[:n]), rule, LEVEL, list(days[:n]))
        base = float(spec['baseline_by_look'][str(n)])
        out.append({'games': n, 'lower_bound': bound, 'baseline': base, 'flagged': bool(bound > base)})
    return out


def check(rows: Sequence[tuple[float | None, int | None, str]], path: Path = BASELINE) -> dict[str, Any]:
    """The drift check's report from (Model A's home probability, home won, game day) rows of the graded
    regular-season picks, in the order their games started: the looks reached, whether any flagged, and the next
    look; or, with no baseline file, that the check is not running and why."""
    if not path.exists():
        return {'running': False, 'why': 'the baselines come from Stage 99\'s confirmation, which has not run yet',
                'looks': [], 'flagged': False, 'next_look': CHECKPOINTS[0]}
    spec = json.loads(path.read_text(encoding='utf-8'))
    kept = [(p, y, d) for p, y, d in rows if p is not None and y in (0, 1)]
    losses = per_game_log_loss((p, y) for p, y, _ in kept)
    done = looks(losses, [d for *_, d in kept], spec)
    return {'running': True, 'looks': done, 'flagged': any(look['flagged'] for look in done),
            'graded': len(losses), 'next_look': next((n for n in CHECKPOINTS if n > len(losses)), None)}


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args != ['baseline']:
        raise SystemExit('usage: python -m src.sports.mlb.drift baseline')
    print(json.dumps(write_baseline(), indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
