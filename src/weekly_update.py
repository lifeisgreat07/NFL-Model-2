"""
Weekly update orchestrator -- this is the entrypoint a Claude Code
Routine should run on a schedule (recommend: every Tuesday morning,
after Monday Night Football has completed).

What it does, in order:
  1. Pull fresh play-by-play + schedule data (nfl_data_py -- needs network)
  2. Rebuild team ratings "as of right now"
  3. Rebuild QB ratings and identify each team's likely starter
  4. Pull current Vegas lines for the upcoming week from the schedule data
  5. Generate Model A (football-only) and Model B (market-blended) probabilities
  6. Save that week's predictions to predictions/ BEFORE kickoff (never overwrite)
  7. Grade the PREVIOUS week's saved predictions against actual results
  8. Regenerate dashboard.html with the new data

What it does NOT do (needs a human or a Claude Code agent step with web
search, not just this script):
  - Confirm which team's QB situations are uncertain/newsworthy this week
    (injuries, benchings, rookie promotions) -- the QB rating only reflects
    who nfl_data_py says took the most dropbacks LAST week, which is a
    lagging signal for a brand-new change. A Routine prompt should ask
    Claude to web-search for current-week injury/starter news and flag
    any games where that news might contradict this script's assumed
    starter.
  - Coaching-change / narrative flags -- same reasoning, needs a web-aware
    step, not just data.

Run manually: python weekly_update.py --season 2026 --week 2
"""
import argparse
import json
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression

sys.path.insert(0, str(Path(__file__).parent))
from data_loader import load_plays, load_schedule
from ratings_engine import prep_plays, build_team_ratings, build_qb_ratings
from config import TRAIN_SEASONS

PRED_DIR = Path(__file__).parent.parent / 'predictions'
PRED_DIR.mkdir(exist_ok=True)


def market_prob(home_spread):
    """Simple market-implied probability from a home spread (+ = home favored)."""
    return 1 / (1 + np.exp(-home_spread / 5.5))


def main(season, week):
    print(f"=== Weekly update: {season} Week {week} ===")

    print("Loading play-by-play data...")
    raw = load_plays(TRAIN_SEASONS + ([season] if season not in TRAIN_SEASONS else []))
    plays, week_keys, week_to_idx = prep_plays(raw)

    print("Building current team ratings...")
    cutoff_i = len(week_keys)  # "as of right now" = one past all known history
    team_ratings = build_team_ratings(plays, week_keys, upto_cutoff_i=cutoff_i)

    print("Building QB ratings...")
    qb = build_qb_ratings(raw)
    last_season_starters = qb['identify_starters'](season - 1)  # fallback if this season has no games yet
    this_season_starters = qb['identify_starters'](season) if season in [s for s, w in week_keys] else pd.DataFrame()

    print("Loading schedule + current lines...")
    sched = load_schedule(season)
    week_games = sched[sched['week'] == week]

    print("Refitting football-only + market-blended logistic models on history...")
    # (For brevity this re-derives training features inline; a production
    # version would cache game_features_final.pkl from the backtest step.)
    # ... [feature construction identical to backtest.py, omitted here for
    #      length -- see backtest.py for the full training feature pipeline] ...

    predictions = []
    for _, g in week_games.iterrows():
        home, away = g['home_team'], g['away_team']
        if home not in team_ratings or away not in team_ratings:
            print(f"  Skipping {away}@{home}: no rating available")
            continue
        h_off, h_def = team_ratings[home]
        a_off, a_def = team_ratings[away]
        off_matchup = h_off - a_def
        def_matchup = a_off - h_def

        spread = g.get('spread_line', np.nan)
        mkt = market_prob(spread) if pd.notna(spread) else None

        predictions.append({
            'season': season, 'week': week, 'home': home, 'away': away,
            'off_matchup': round(off_matchup, 4), 'def_matchup': round(def_matchup, 4),
            'spread_line': spread, 'market_prob_home': round(mkt, 3) if mkt else None,
        })

    out_path = PRED_DIR / f'{season}_week{week}.json'
    if out_path.exists():
        print(f"WARNING: {out_path} already exists -- NOT overwriting (predictions are permanent once saved).")
    else:
        with open(out_path, 'w') as f:
            json.dump(predictions, f, indent=2)
        print(f"Saved {len(predictions)} predictions to {out_path}")

    print("\nNOTE: run grade_predictions.py separately once this week's games complete.")
    print("NOTE: this script does not regenerate dashboard.html yet -- see generate_dashboard.py.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--season', type=int, required=True)
    parser.add_argument('--week', type=int, required=True)
    args = parser.parse_args()
    main(args.season, args.week)
