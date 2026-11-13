"""Model A's log loss season by season, for the NBA drift baseline's spread
(Stage 85 item 3). Writes experiments/nba/stage61/results/model_a_by_season.json.

    python -m src.sports.nba.season_spread
"""
from __future__ import annotations

import json
from typing import Any

from src.core import season_spread
from src.core.sport import sport_paths
from src.sports.nba import backtest, ratings

NAME = 'model_a_by_season.json'



def checkpoints() -> list[int]:
    """The drift check's registered looks (data/nba/drift_baseline.json)."""
    rule = json.loads((sport_paths('nba').data / 'drift_baseline.json').read_text(encoding='utf-8'))['rule']
    return [int(n) for n in rule['checkpoints']]


def compute() -> dict[str, Any]:
    reg = backtest.registry()
    p = reg['protocol']
    tuning = json.loads((backtest.RESULTS / 'tuning.json').read_text(encoding='utf-8'))
    conf = json.loads((backtest.RESULTS / 'confirmation.json').read_text(encoding='utf-8'))
    h, lam = tuning['chosen']['H_days'], tuning['chosen']['lambda']
    games, minutes = backtest.load_history(p['training_from_season'], p['confirmation_seasons'][-1])
    games = ratings.prepare(games)
    table = ratings.features(games, minutes, h, lam).merge(games[['game_id', 'home_prob']], on='game_id', how='left')
    out = season_spread.spread(backtest.walk_forward, backtest.scores, table, list(backtest.A_COLUMNS),
                               p['validation_seasons'], p['confirmation_seasons'], conf['scores']['model_a']['log_loss'])
    # Stage 95 item 31: Model A, with and without its availability term, over each season's first n games.
    looks = {key: season_spread.by_look(backtest.walk_forward, backtest.scores, table, cols, p['validation_seasons'],
                                        p['confirmation_seasons'], checkpoints())
             for key, cols in (('by_look', list(backtest.A_COLUMNS)),
                               ('by_look_no_availability', list(backtest.A_COLUMNS[:2])))}
    return {'model': 'model_a', 'settings': {'H_days': h, 'lambda': lam},
            'source': 'src/sports/nba/season_spread.py, the Stage 61 walk-forward at the chosen settings', **out,
            **looks}


def main() -> int:
    out = compute()
    path = backtest.write(NAME, out)
    for r in out['seasons']:
        print(f"{r['label']} ({r['role']}): {r['log_loss']:.4f} over {r['games']} games")
    print(f"pooled confirmation {out['baseline']['pooled_confirmation']:.6f} vs baseline "
          f"{out['baseline']['value']:.6f}: {'agrees' if out['baseline']['agrees'] else 'DIFFERS'}; wrote {path}")
    return 0 if out['baseline']['agrees'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
