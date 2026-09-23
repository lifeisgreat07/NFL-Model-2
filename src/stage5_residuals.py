"""
Stage 5b, descriptive only: where the live Model A loses log loss.

This makes no decision and tests nothing. It exists to check the MECHANISM
behind H1's point estimate -- that the live model loses ground on the games
where last week's quarterback is not this week's starter -- because a
number without its mechanism is the half of a finding this project has
learned not to trust (CLAUDE.md: "an audit finding is a hypothesis").

Every slice below was chosen before this script was run, and is written
into the output file with its game count so nothing can be quoted without
the n beside it. Seasons: 2022-2025 (the same games as Q0). The 2026
forward holdout is refused by stage5_eval.guard_seasons.

    python src/stage5_residuals.py   -> experiments/stage5/residuals.json
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stage5_data as sd  # noqa: E402
import stage5_eval as se  # noqa: E402
from stage5_run import GAMES, REPO_ROOT, git_head  # noqa: E402

SEASONS = [2022, 2023, 2024, 2025]
OUT = REPO_ROOT / 'experiments' / 'stage5' / 'residuals.json'


def main():
    registry = se.load_registry()
    se.guard_seasons(SEASONS, registry)
    games = pd.read_pickle(GAMES)
    specs = {s: sd.feature_set(spec=s) for s in ('lagged', 'sched', 'oracle')}
    specs['model_b_lagged'] = sd.feature_set(spec='lagged', market='spread_line')
    specs['market'] = ['spread_line']
    ids, y, probs = se.walk_forward(games, specs, SEASONS)
    g = games.set_index('game_id').loc[ids].reset_index()
    ll = {k: se.per_game_losses(y, p)[0] for k, p in probs.items()}

    # A game where either side's lagged quarterback differs from its announced
    # starter. Read off the two QB features rather than player ids: both are
    # the same trailing_rating call at the same cutoff, so they are equal
    # exactly when the same two players are named.
    mismatch = (g['lagged_qb_matchup'] != g['sched_qb_matchup']).values
    slices = {
        'all games': np.ones(len(y), dtype=bool),
        'lagged QB differs from announced starter (either side)': mismatch,
        'lagged QB matches announced starter (both sides)': ~mismatch,
        'weeks 1-4': (g['week'] <= 4).values,
        'weeks 5-18': (g['week'] > 4).values,
    }
    out = {'code_commit': git_head(), 'seasons': SEASONS, 'n_games': int(len(y)),
           'note': 'Descriptive only. Mean per-game log loss by slice; no interval, no decision.',
           'slices': {}}
    for name, m in slices.items():
        out['slices'][name] = {
            'n_games': int(m.sum()),
            **{f'log_loss_{k}': float(v[m].mean()) for k, v in ll.items()},
        }
    OUT.write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    for name, row in out['slices'].items():
        print(f"{name:<58} n={row['n_games']:<5}" + ''.join(
            f" {k[9:]}={row[k]:.4f}" for k in row if k.startswith('log_loss_')))


if __name__ == '__main__':
    main()
