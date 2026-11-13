"""Model A's log loss season by season, for the NHL drift baseline's spread
(Stage 85 item 3). Writes experiments/nhl/stage56/results/model_a_by_season.json.

    python -m src.sports.nhl.season_spread
"""
from __future__ import annotations

import json
from typing import Any

from src.core import season_spread
from src.core.sport import sport_paths
from src.sports.nhl import backtest, ratings

NAME = 'model_a_by_season.json'



def checkpoints() -> list[int]:
    """The drift check's registered looks (data/nhl/drift_baseline.json)."""
    rule = json.loads((sport_paths('nhl').data / 'drift_baseline.json').read_text(encoding='utf-8'))['rule']
    return [int(n) for n in rule['checkpoints']]


def compute() -> dict[str, Any]:
    reg = backtest.registry()
    p = reg['protocol']
    conf = json.loads((backtest.RESULTS / 'confirmation.json').read_text(encoding='utf-8'))
    h, k = conf['H_days'], conf['K_shots']
    games = ratings.prepare(backtest.load_history(p['training_from_season'], p['confirmation_seasons'][-1]))
    table = ratings.features(games, h, [k]).merge(games[['game_id', 'home_prob']], on='game_id', how='left')
    cols = ['goal_matchup', 'shot_matchup', backtest.goalie_column(k)]
    out = season_spread.spread(backtest.walk_forward, backtest.scores, table, cols, p['validation_seasons'],
                               p['confirmation_seasons'], conf['scores']['model_a']['log_loss'])
    # Stage 95 item 31: Model A over each season's first n games, for each registered look.
    by_look = season_spread.by_look(backtest.walk_forward, backtest.scores, table, cols, p['validation_seasons'],
                                    p['confirmation_seasons'], checkpoints())
    return {'model': 'model_a', 'settings': {'H_days': h, 'K_shots': k},
            'source': 'src/sports/nhl/season_spread.py, the Stage 56 walk-forward at the chosen settings', **out,
            'by_look': by_look}


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
