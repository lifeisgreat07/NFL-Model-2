"""
Generates dashboard.html from real, saved data -- predictions/*.json and
data/current_ratings.json. This replaces per-run agent improvisation with
a deterministic template fill: same inputs always produce the same output,
and a bug here throws a real Python error instead of silently mangling
the HTML.

Run manually: python src/generate_dashboard.py
The weekly Routine should call this as its last step, after
weekly_update.py and grade_predictions.py have run.
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / 'data'
PRED_DIR = ROOT / 'predictions'
RESULTS_DIR = ROOT / 'results'
TEMPLATE_PATH = ROOT / 'src' / 'dashboard_template.html'
OUTPUT_PATH = ROOT / 'dashboard.html'


def load_current_ratings():
    """Reads data/current_ratings.json, written by weekly_update.py.
    Format: [{"team": "BUF", "name": "Buffalo Bills", "off": 0.113,
               "def": -0.014, "net": 0.127}, ...]"""
    path = DATA_DIR / 'current_ratings.json'
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run weekly_update.py first -- it writes this "
            f"file as part of building current team ratings."
        )
    with open(path) as f:
        return json.load(f)


def find_latest_predictions():
    """Finds the most recent predictions/{season}_week{N}.json file by
    (season, week), not by file modification time -- so re-running an
    older week doesn't accidentally become 'latest'."""
    files = list(PRED_DIR.glob('*_week*.json'))
    if not files:
        return None, None, None
    parsed = []
    for f in files:
        stem = f.stem  # e.g. "2026_week1"
        try:
            season_str, week_str = stem.split('_week')
            parsed.append((int(season_str), int(week_str), f))
        except ValueError:
            continue
    if not parsed:
        return None, None, None
    season, week, path = max(parsed, key=lambda x: (x[0], x[1]))
    with open(path) as pf:
        preds = json.load(pf)
    return season, week, preds


def load_graded_results(season, week):
    """If this week has already been graded, load it (adds actual_home_win
    / market_correct fields) -- used to show real/won record if available."""
    path = RESULTS_DIR / f'{season}_week{week}_graded.json'
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return None


def spread_display(away, home, spread):
    if spread is None:
        return "No line available"
    if spread >= 0:
        return f"{home} -{spread}"
    return f"{away} -{abs(spread)}"


def build_games_js(season, week, preds):
    """Convert saved predictions into the dashboard's game-card JS format."""
    games = []
    for p in preds:
        model_a = p.get('model_a_home_win_prob')
        model_b = p.get('model_b_home_win_prob')
        if model_a is None:
            # Old-format prediction file (pre-fix) -- skip rather than
            # show a card with fabricated/missing probabilities.
            continue
        flag_parts = []
        if p.get('qb_note'):
            flag_parts.append(p['qb_note'])
        games.append({
            'away': p['away'], 'home': p['home'],
            'kickoff': f"{season} Week {week}",
            'spread': p.get('spread_line'),
            'fbA_home': round(model_a * 100, 1),
            'mktB_home': round((model_b if model_b is not None else model_a) * 100, 1),
            'flag': " ".join(flag_parts),
        })
    return games


def build_teams_js(ratings):
    return [
        {'team': r['team'], 'name': r['name'], 'off': r['off'], 'def': r['def'], 'net': r['net']}
        for r in ratings
    ]


def main():
    print("Loading current ratings...")
    ratings = load_current_ratings()
    teams_js = build_teams_js(ratings)

    print("Finding latest predictions...")
    season, week, preds = find_latest_predictions()

    if preds is None:
        print("No saved predictions found yet -- dashboard will show ratings only, empty game board.")
        games_js = []
        foot_html = (
            f"Trained on: current nflfastR history<br>"
            f"{len(ratings)} teams rated<br>"
            f"No predictions saved yet"
        )
    else:
        print(f"Using {season} Week {week} ({len(preds)} games)")
        games_js = build_games_js(season, week, preds)
        graded = load_graded_results(season, week)
        graded_note = ""
        if graded:
            n = len(graded)
            correct = sum(1 for g in graded if g.get('market_correct'))
            graded_note = f"<br>Last graded: {correct}/{n} correct"
        foot_html = (
            f"Trained on: current nflfastR history<br>"
            f"Showing: {season} Week {week}<br>"
            f"{len(games_js)} games"
            f"{graded_note}"
        )

    with open(TEMPLATE_PATH) as f:
        template = f.read()

    html = template.replace('__TEAMS_JSON__', json.dumps(teams_js, indent=2))
    html = html.replace('__GAMES_JSON__', json.dumps(games_js, indent=2))
    html = html.replace('__SIDEBAR_FOOT__', foot_html)

    with open(OUTPUT_PATH, 'w') as f:
        f.write(html)
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == '__main__':
    main()
