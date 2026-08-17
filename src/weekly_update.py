"""
Weekly update orchestrator -- entrypoint for the Claude Code Routine.

v2: fixes the bug the routine caught on its first offseason run -- this
previously built matchup features but never actually fit or applied the
Model A / Model B logistic regressions, so saved predictions had no real
win probabilities in them. That's fixed here: both models are trained on
full historical data and actually applied to the target week's games.

What it does, in order:
  1. Pull fresh play-by-play + schedule data (nfl_data_py -- needs network)
  2. Build historical, leak-free team + QB ratings for every past week
  3. Construct the historical training feature set (off_matchup, def_matchup,
     qb_matchup, spread_line vs actual home_win)
  4. Fit Model A (football-only) and Model B (+ market) logistic regression
     on ALL available history (for live use we want every real game we
     have, not a holdout -- backtest.py is where holdout evaluation lives)
  5. Build this week's ratings "as of right now" and apply both models
  6. Save predictions to predictions/ BEFORE kickoff (never overwrite)
  7. Grade the previous week's saved predictions against actual results
  8. Regenerate dashboard.html (not yet implemented -- see README)

What it does NOT do (needs a human or a web-search-capable agent step,
not just this script):
  - Confirm which team's QB situations are uncertain/newsworthy this week.
    The QB rating reflects historical trailing performance for whoever
    had the most dropbacks last known appearance -- a lagging signal for
    a brand-new change (new starter, injury, benching). The routine
    prompt should web-search for this and flag any contradiction.
  - Coaching-change / narrative flags -- same reasoning.

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
DATA_DIR = Path(__file__).parent.parent / 'data'
DATA_DIR.mkdir(exist_ok=True)

TEAM_NAMES = {
    'ARI':'Arizona Cardinals','ATL':'Atlanta Falcons','BAL':'Baltimore Ravens','BUF':'Buffalo Bills',
    'CAR':'Carolina Panthers','CHI':'Chicago Bears','CIN':'Cincinnati Bengals','CLE':'Cleveland Browns',
    'DAL':'Dallas Cowboys','DEN':'Denver Broncos','DET':'Detroit Lions','GB':'Green Bay Packers',
    'HOU':'Houston Texans','IND':'Indianapolis Colts','JAX':'Jacksonville Jaguars','KC':'Kansas City Chiefs',
    'LA':'LA Rams','LAC':'LA Chargers','LV':'Las Vegas Raiders','MIA':'Miami Dolphins','MIN':'Minnesota Vikings',
    'NE':'New England Patriots','NO':'New Orleans Saints','NYG':'NY Giants','NYJ':'NY Jets',
    'PHI':'Philadelphia Eagles','PIT':'Pittsburgh Steelers','SEA':'Seattle Seahawks','SF':'San Francisco 49ers',
    'TB':'Tampa Bay Buccaneers','TEN':'Tennessee Titans','WAS':'Washington Commanders',
}


def save_current_ratings(team_ratings):
    """Write the current team ratings snapshot to data/current_ratings.json
    so generate_dashboard.py can display them without recomputing (which
    would mean re-pulling all play-by-play data a second time)."""
    rows = []
    for team, (off, deff) in team_ratings.items():
        rows.append({
            'team': team, 'name': TEAM_NAMES.get(team, team),
            'off': round(off, 4), 'def': round(deff, 4), 'net': round(off - deff, 4),
        })
    rows.sort(key=lambda r: -r['net'])
    with open(DATA_DIR / 'current_ratings.json', 'w') as f:
        json.dump(rows, f, indent=2)
    print(f"Saved {len(rows)} team ratings to data/current_ratings.json")


def market_prob(home_spread):
    """Simple market-implied probability from a home spread (+ = home favored)."""
    return 1 / (1 + np.exp(-home_spread / 5.5))


def build_historical_features(plays, week_keys, week_to_idx, team_ratings_by_week,
                                qb, schedules_by_season):
    """Construct the training dataset: one row per historical game with
    real, leak-free matchup features and the actual outcome."""
    rows = []
    for season, sched in schedules_by_season.items():
        played = sched.dropna(subset=['home_score', 'away_score'])
        for _, g in played.iterrows():
            key = (g['season'], g['week'])
            if key not in team_ratings_by_week or key not in week_to_idx:
                continue
            rt = team_ratings_by_week[key]
            if g['home_team'] not in rt or g['away_team'] not in rt:
                continue
            h_off, h_def = rt[g['home_team']]
            a_off, a_def = rt[g['away_team']]

            starters = qb['identify_starters'](g['season'], g['week'])
            starters_idx = starters.set_index(['season', 'week', 'posteam'])
            hk, ak = (g['season'], g['week'], g['home_team']), (g['season'], g['week'], g['away_team'])
            if hk not in starters_idx.index or ak not in starters_idx.index:
                continue
            cutoff = week_to_idx[key] if key in week_to_idx else qb['week_to_idx'].get(key)
            qb_cutoff = qb['week_to_idx'].get(key)
            if qb_cutoff is None:
                continue
            home_qb_rating = qb['trailing_rating'](starters_idx.loc[hk, 'passer_player_id'], qb_cutoff)
            away_qb_rating = qb['trailing_rating'](starters_idx.loc[ak, 'passer_player_id'], qb_cutoff)

            rows.append({
                'season': g['season'], 'week': g['week'],
                'home_win': int(g['home_score'] > g['away_score']),
                'off_matchup': h_off - a_def,
                'def_matchup': a_off - h_def,
                'qb_matchup': home_qb_rating - away_qb_rating,
                'spread_line': g.get('spread_line', np.nan),
            })
    return pd.DataFrame(rows)


def determine_next_week(season):
    """If --week isn't given, figure out the right week automatically:
    one past whatever week was most recently saved for this season.
    Starts at week 1 if nothing's been saved yet. This is what lets the
    routine run unattended all season without a manually-edited week
    number in its prompt."""
    existing = list(PRED_DIR.glob(f'{season}_week*.json'))
    weeks_done = []
    for f in existing:
        try:
            weeks_done.append(int(f.stem.split('_week')[1]))
        except (IndexError, ValueError):
            continue
    if weeks_done:
        next_week = max(weeks_done) + 1
        print(f"Most recent saved week for {season}: {max(weeks_done)}. Using week {next_week}.")
        return next_week
    print(f"No predictions saved yet for {season}. Starting at week 1.")
    return 1
    # Playoff numbering note (resolved -- verified against real nflverse data
    # and official docs): weeks do NOT reset after the regular season. They
    # continue counting up (e.g. 2021+: reg season 1-18, wild card 19,
    # divisional 20, conf champ 21, Super Bowl 22). So max+1 naturally walks
    # straight through the playoffs with no special-casing needed. The one
    # real edge case -- running this again after the Super Bowl -- is
    # handled in main() by exiting cleanly when a week has zero games.


def main(season, week):
    print(f"=== Weekly update: {season} Week {week} ===")

    print("Loading play-by-play data...")
    seasons_needed = sorted(set(TRAIN_SEASONS) | {season})
    raw = load_plays(seasons_needed)
    plays, week_keys, week_to_idx = prep_plays(raw)

    print("Building historical team ratings for every past week (leak-free)...")
    team_ratings_by_week = build_team_ratings(plays, week_keys, upto_cutoff_i=None)

    print("Building QB ratings...")
    qb = build_qb_ratings(raw)

    print("Loading schedules (scores + lines) for training history...")
    schedules_by_season = {s: load_schedule(s) for s in seasons_needed}

    print("Constructing historical training features...")
    hist = build_historical_features(plays, week_keys, week_to_idx, team_ratings_by_week,
                                       qb, schedules_by_season)
    print(f"  {len(hist)} historical games with complete features")
    if len(hist) < 100:
        print("WARNING: very little historical training data -- predictions below may be unreliable.")

    print("Fitting Model A (football-only) and Model B (+ market)...")
    model_a = LogisticRegression(max_iter=1000)
    model_a.fit(hist[['off_matchup', 'def_matchup', 'qb_matchup']].values, hist['home_win'].values)

    hist_b = hist.dropna(subset=['spread_line'])
    model_b = LogisticRegression(max_iter=1000)
    model_b.fit(hist_b[['off_matchup', 'def_matchup', 'qb_matchup', 'spread_line']].values, hist_b['home_win'].values)

    print("Building current ('as of right now') team + QB ratings...")
    cutoff_i = len(week_keys)
    current_team_ratings = build_team_ratings(plays, week_keys, upto_cutoff_i=cutoff_i)
    save_current_ratings(current_team_ratings)
    qb_cutoff = len(qb['week_keys'])
    # fallback starter source: most recent season with any starter data
    starter_season = season if season in [s for s, w in qb['week_keys']] else season - 1
    current_starters = qb['identify_starters'](starter_season)
    current_starters_idx = current_starters.sort_values('week').drop_duplicates(subset=['posteam'], keep='last').set_index('posteam')

    print("Loading target week's schedule + current lines...")
    sched = load_schedule(season)
    week_games = sched[sched['week'] == week]

    if len(week_games) == 0:
        print(f"No games found for {season} week {week} -- likely means the season "
              f"(including playoffs) is over. Nothing to predict. Exiting cleanly.")
        return

    predictions = []
    for _, g in week_games.iterrows():
        home, away = g['home_team'], g['away_team']
        if home not in current_team_ratings or away not in current_team_ratings:
            print(f"  Skipping {away}@{home}: no team rating available")
            continue
        h_off, h_def = current_team_ratings[home]
        a_off, a_def = current_team_ratings[away]
        off_matchup = h_off - a_def
        def_matchup = a_off - h_def

        if home in current_starters_idx.index and away in current_starters_idx.index:
            home_qb_id = current_starters_idx.loc[home, 'passer_player_id']
            away_qb_id = current_starters_idx.loc[away, 'passer_player_id']
            home_qb_rating = qb['trailing_rating'](home_qb_id, qb_cutoff)
            away_qb_rating = qb['trailing_rating'](away_qb_id, qb_cutoff)
            qb_matchup = home_qb_rating - away_qb_rating
            qb_note = None
        else:
            qb_matchup = 0.0
            qb_note = "No known starter found -- QB feature defaulted to neutral (0). Verify manually."

        prob_a = model_a.predict_proba([[off_matchup, def_matchup, qb_matchup]])[0][1]

        spread = g.get('spread_line', np.nan)
        if pd.notna(spread):
            prob_b = model_b.predict_proba([[off_matchup, def_matchup, qb_matchup, spread]])[0][1]
            mkt = market_prob(spread)
        else:
            prob_b, mkt = None, None

        predictions.append({
            'season': season, 'week': week, 'home': home, 'away': away,
            'off_matchup': round(off_matchup, 4), 'def_matchup': round(def_matchup, 4),
            'qb_matchup': round(qb_matchup, 4),
            'spread_line': spread if pd.notna(spread) else None,
            'model_a_home_win_prob': round(float(prob_a), 4),
            'model_b_home_win_prob': round(float(prob_b), 4) if prob_b is not None else None,
            'market_prob_home': round(mkt, 4) if mkt is not None else None,
            'qb_note': qb_note,
        })

    out_path = PRED_DIR / f'{season}_week{week}.json'
    if out_path.exists():
        print(f"WARNING: {out_path} already exists -- NOT overwriting (predictions are permanent once saved).")
    else:
        with open(out_path, 'w') as f:
            json.dump(predictions, f, indent=2)
        print(f"Saved {len(predictions)} predictions to {out_path}")
        for p in predictions:
            print(f"  {p['away']} @ {p['home']}: Model A home={p['model_a_home_win_prob']:.1%}"
                  + (f", Model B home={p['model_b_home_win_prob']:.1%}" if p['model_b_home_win_prob'] else "")
                  + (f"  [{p['qb_note']}]" if p['qb_note'] else ""))

    print("\nNOTE: run grade_predictions.py separately once this week's games complete.")
    print("NOTE: this script does not regenerate dashboard.html yet -- see generate_dashboard.py.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--season', type=int, required=True)
    parser.add_argument('--week', type=int, default=None,
                         help='Week number. If omitted, auto-detects the next '
                              'un-saved week for this season.')
    args = parser.parse_args()
    week = args.week if args.week is not None else determine_next_week(args.season)
    main(args.season, week)
