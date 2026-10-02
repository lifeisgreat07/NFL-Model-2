"""
Grade a previously-saved week's predictions against actual results.
Run this AFTER a week's games complete, before generating next week's
predictions. Builds the real accuracy track record over the season --
never edit a saved prediction file after the fact; this script only reads
predictions/ and writes to results/.

v2: now grades Model A and Model B individually, not just the market --
the original version only checked market_correct, which meant the
"Season Accuracy Tracker" would have had nothing of our own model's
performance to show.
"""
from __future__ import annotations

import argparse
import json

import pandas as pd

from src.pipeline.paths import (  # noqa: E402  (src/pipeline/paths.py, Stage 32 item 15)
    PRED_DIR,
    RESULTS_DIR,
)
from src.pipeline.runlog import get_logger  # noqa: E402  (Stage 32 item 17)

log = get_logger(__name__)
RESULTS_DIR.mkdir(exist_ok=True)


def graded_correct(prob: float | None, actual_home_win: int | None) -> int | None:
    if prob is None:
        return None
    return int((prob >= 0.5) == bool(actual_home_win))


def main(season: int, week: int) -> None:
    from src.pipeline.data_loader import load_schedule
    pred_path = PRED_DIR / f'{season}_week{week}.json'
    if not pred_path.exists():
        log.info(f"No saved predictions found at {pred_path} -- nothing to grade.")
        return

    with open(pred_path) as f:
        preds = json.load(f)

    sched = load_schedule(season)
    week_results = sched[sched['week'] == week]

    graded = []
    for p in preds:
        row = week_results[(week_results['home_team'] == p['home']) & (week_results['away_team'] == p['away'])]
        if len(row) == 0 or pd.isna(row.iloc[0].get('home_score')):
            log.info(f"  {p['away']}@{p['home']}: result not yet available, skipping")
            continue
        r = row.iloc[0]
        if r['home_score'] == r['away_score']:
            # A tie has no winner, so no pick on it is right or wrong (Stage
            # 25). It used to be graded as an away win, which scored every
            # home pick wrong and every away pick right. It is still recorded,
            # marked, with nulls a reader already treats as "no result to score".
            p['result'] = 'tie'
            p['actual_home_win'] = None
            p['market_correct'] = p['model_a_correct'] = p['model_b_correct'] = None
            graded.append(p)
            continue
        actual_home_win = int(r['home_score'] > r['away_score'])
        p['actual_home_win'] = actual_home_win
        p['market_correct'] = graded_correct(p.get('market_prob_home'), actual_home_win)
        p['model_a_correct'] = graded_correct(p.get('model_a_home_win_prob'), actual_home_win)
        p['model_b_correct'] = graded_correct(p.get('model_b_home_win_prob'), actual_home_win)
        graded.append(p)

    out_path = RESULTS_DIR / f'{season}_week{week}_graded.json'
    with open(out_path, 'w') as f:
        json.dump(graded, f, indent=2)

    if graded:
        n = len(graded)
        def summarize(key):
            vals = [g[key] for g in graded if g.get(key) is not None]
            return f"{sum(vals)}/{len(vals)}" if vals else "n/a"
        log.info(f"Graded {n} games.")
        log.info(f"  Model A: {summarize('model_a_correct')} correct")
        log.info(f"  Model B: {summarize('model_b_correct')} correct")
        log.info(f"  Market:  {summarize('market_correct')} correct")
    log.info(f"Saved to {out_path}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--season', type=int, required=True)
    parser.add_argument('--week', type=int, required=True)
    args = parser.parse_args()
    main(args.season, args.week)
