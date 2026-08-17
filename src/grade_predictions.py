"""
Grade a previously-saved week's predictions against actual results.
Run this AFTER a week's games complete, before generating next week's
predictions. Builds the real accuracy track record over the season --
never edit a saved prediction file after the fact; this script only reads
predictions/ and writes to results/.
"""
import argparse
import json
from pathlib import Path
import pandas as pd

PRED_DIR = Path(__file__).parent.parent / 'predictions'
RESULTS_DIR = Path(__file__).parent.parent / 'results'
RESULTS_DIR.mkdir(exist_ok=True)


def main(season, week):
    from data_loader import load_schedule
    pred_path = PRED_DIR / f'{season}_week{week}.json'
    if not pred_path.exists():
        print(f"No saved predictions found at {pred_path} -- nothing to grade.")
        return

    with open(pred_path) as f:
        preds = json.load(f)

    sched = load_schedule(season)
    week_results = sched[sched['week'] == week]

    graded = []
    for p in preds:
        row = week_results[(week_results['home_team'] == p['home']) & (week_results['away_team'] == p['away'])]
        if len(row) == 0 or pd.isna(row.iloc[0].get('home_score')):
            print(f"  {p['away']}@{p['home']}: result not yet available, skipping")
            continue
        r = row.iloc[0]
        actual_home_win = int(r['home_score'] > r['away_score'])
        p['actual_home_win'] = actual_home_win
        p['market_correct'] = int((p['market_prob_home'] >= 0.5) == actual_home_win) if p.get('market_prob_home') else None
        graded.append(p)

    out_path = RESULTS_DIR / f'{season}_week{week}_graded.json'
    with open(out_path, 'w') as f:
        json.dump(graded, f, indent=2)

    if graded:
        n = len(graded)
        mkt_correct = sum(g['market_correct'] for g in graded if g['market_correct'] is not None)
        print(f"Graded {n} games. Market model: {mkt_correct}/{n} correct.")
    print(f"Saved to {out_path}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--season', type=int, required=True)
    parser.add_argument('--week', type=int, required=True)
    args = parser.parse_args()
    main(args.season, args.week)
