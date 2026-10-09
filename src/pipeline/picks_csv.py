"""Every locked pick and its grade, as one CSV beside the board (Stage 46
item 7).

The page shows the record; this file lets anyone check it without the page.
One row per game of every locked week (predictions/<season>_week<N>.json,
never a preview), in season, week and kickoff order, joined to that week's
grades (results/<season>_week<N>_graded.json) where the game has one. A game
not yet played has empty result columns; a tie says so and grades no one,
as the grading does.

Probabilities are as saved, to four decimals. A pick is the side a model
gives 50% or more, the rule the grading uses.

Run: python -m src.pipeline.picks_csv --out picks.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any

from src.pipeline.paths import PRED_DIR, RESULTS_DIR

COLUMNS = [
    'season', 'week', 'gameday', 'kickoff_et', 'away', 'home', 'model_version',
    'model_a_home_win_prob', 'model_b_home_win_prob', 'market_home_win_prob',
    'model_a_pick', 'model_b_pick', 'market_pick',
    'result', 'winner', 'model_a_correct', 'model_b_correct', 'market_correct',
]
WEEK_FILE = re.compile(r'(\d{4})_week(\d+)')


def week_files(pred_dir: Path) -> list[tuple[int, int, Path]]:
    """Locked weeks only: previews live in predictions/preview/ and are never
    graded, so they are not picks."""
    out = []
    for p in pred_dir.glob('*_week*.json'):
        m = WEEK_FILE.fullmatch(p.stem)
        if m:
            out.append((int(m.group(1)), int(m.group(2)), p))
    return sorted(out)


def pick(prob: float | None, game: dict[str, Any]) -> str:
    if prob is None:
        return ''
    return game['home'] if prob >= 0.5 else game['away']


def _prob(v: Any) -> str:
    return '' if v is None else f'{float(v):.4f}'


def _flag(v: Any) -> str:
    return '' if v is None else str(int(v))


def rows(pred_dir: Path = PRED_DIR, results_dir: Path = RESULTS_DIR) -> list[dict[str, str]]:
    out = []
    for season, week, path in week_files(pred_dir):
        games = json.loads(path.read_text(encoding='utf-8'))
        graded_path = results_dir / f'{season}_week{week}_graded.json'
        graded = json.loads(graded_path.read_text(encoding='utf-8')) if graded_path.exists() else []
        by_game = {(g['away'], g['home']): g for g in graded}
        games = sorted(games, key=lambda g: (g.get('gameday') or '', g.get('gametime_et') or '', g['home']))
        for g in games:
            r = by_game.get((g['away'], g['home']))
            if r is None:
                result, winner = '', ''
            elif r.get('result') == 'tie':
                result, winner = 'tie', ''
            elif r.get('actual_home_win') is None:
                result, winner = '', ''
            else:
                result = 'final'
                winner = g['home'] if r['actual_home_win'] else g['away']
            out.append({
                'season': str(season), 'week': str(week),
                'gameday': g.get('gameday') or '', 'kickoff_et': g.get('gametime_et') or '',
                'away': g['away'], 'home': g['home'], 'model_version': str(g.get('model_version') or ''),
                'model_a_home_win_prob': _prob(g.get('model_a_home_win_prob')),
                'model_b_home_win_prob': _prob(g.get('model_b_home_win_prob')),
                'market_home_win_prob': _prob(g.get('market_prob_home')),
                'model_a_pick': pick(g.get('model_a_home_win_prob'), g),
                'model_b_pick': pick(g.get('model_b_home_win_prob'), g),
                'market_pick': pick(g.get('market_prob_home'), g),
                'result': result, 'winner': winner,
                'model_a_correct': _flag(r.get('model_a_correct')) if r else '',
                'model_b_correct': _flag(r.get('model_b_correct')) if r else '',
                'market_correct': _flag(r.get('market_correct')) if r else '',
            })
    return out


def write(out: Path, pred_dir: Path = PRED_DIR, results_dir: Path = RESULTS_DIR) -> int:
    data = rows(pred_dir, results_dir)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator='\n')
        w.writeheader()
        w.writerows(data)
    return len(data)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--out', default='picks.csv')
    args = ap.parse_args(argv)
    n = write(Path(args.out))
    print(f'wrote {args.out} ({n} picks)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
