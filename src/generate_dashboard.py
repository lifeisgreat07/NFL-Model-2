"""
Generates dashboard.html (as index.html) from real, saved data:
predictions/*.json, results/*_graded.json, and data/current_ratings.json.
Deterministic template fill -- same inputs always produce the same output.

v2 additions: bundles ALL saved weeks (not just the latest) for past-week
browsing, aggregates all graded results into a real season accuracy record
and calibration table, and passes through confidence ranking + why-
breakdown that weekly_update.py now computes per game.
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / 'data'
PRED_DIR = ROOT / 'predictions'
RESULTS_DIR = ROOT / 'results'
TEMPLATE_PATH = ROOT / 'src' / 'dashboard_template.html'
OUTPUT_PATH = ROOT / 'index.html'  # served as the default page by GitHub Pages


def load_current_ratings():
    path = DATA_DIR / 'current_ratings.json'
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run weekly_update.py first -- it writes this "
            f"file as part of building current team ratings."
        )
    with open(path) as f:
        return json.load(f)


def parse_week_stem(stem):
    """'2026_week1' -> (2026, 1). Returns None if it doesn't match."""
    try:
        season_str, week_str = stem.split('_week')
        return int(season_str), int(week_str)
    except ValueError:
        return None


def load_all_predictions():
    """Returns {(season, week): [predictions...]} for every saved week."""
    out = {}
    for f in PRED_DIR.glob('*_week*.json'):
        parsed = parse_week_stem(f.stem)
        if parsed is None:
            continue
        with open(f) as pf:
            out[parsed] = json.load(pf)
    return out


def load_all_graded():
    """Returns {(season, week): [graded predictions...]} for every graded week."""
    out = {}
    for f in RESULTS_DIR.glob('*_week*_graded.json'):
        stem = f.stem.replace('_graded', '')
        parsed = parse_week_stem(stem)
        if parsed is None:
            continue
        with open(f) as gf:
            out[parsed] = json.load(gf)
    return out


def build_games_js(preds, graded_lookup_by_key):
    """Convert one week's saved predictions into the dashboard's game-card
    JS format, joining in graded results (actual outcome, correctness) if
    that week has already been graded."""
    games = []
    for p in preds:
        model_a = p.get('model_a_home_win_prob')
        if model_a is None:
            continue  # old-format prediction file (pre-fix) -- skip rather than fabricate
        model_b = p.get('model_b_home_win_prob')
        key = (p['home'], p['away'])
        graded = graded_lookup_by_key.get(key)

        flag_parts = []
        if p.get('qb_note'):
            flag_parts.append(p['qb_note'])

        games.append({
            'away': p['away'], 'home': p['home'],
            'spread': p.get('spread_line'),
            'fbA_home': round(model_a * 100, 1),
            'mktB_home': round((model_b if model_b is not None else model_a) * 100, 1),
            'flag': " ".join(flag_parts),
            'confidence_rank': p.get('confidence_rank'),
            'confidence_points': p.get('confidence_points'),
            'why': p.get('why'),
            'graded': graded is not None,
            'actual_home_win': graded.get('actual_home_win') if graded else None,
            'model_a_correct': graded.get('model_a_correct') if graded else None,
            'model_b_correct': graded.get('model_b_correct') if graded else None,
        })
    return games


def build_accuracy_summary(all_graded):
    """Aggregate every graded week into a season-level record + a
    per-week trend + calibration buckets (predicted probability vs
    actual win rate), using Model B (or Model A as fallback) per game."""
    all_games = []
    for (season, week), graded in sorted(all_graded.items()):
        for g in graded:
            all_games.append({**g, 'season': season, 'week': week})

    if not all_games:
        return {'weeks': [], 'overall': None, 'calibration': []}

    weekly = []
    for (season, week), graded in sorted(all_graded.items()):
        a_vals = [g['model_a_correct'] for g in graded if g.get('model_a_correct') is not None]
        b_vals = [g['model_b_correct'] for g in graded if g.get('model_b_correct') is not None]
        m_vals = [g['market_correct'] for g in graded if g.get('market_correct') is not None]
        weekly.append({
            'season': season, 'week': week,
            'n': len(graded),
            'model_a_correct': sum(a_vals), 'model_a_n': len(a_vals),
            'model_b_correct': sum(b_vals), 'model_b_n': len(b_vals),
            'market_correct': sum(m_vals), 'market_n': len(m_vals),
        })

    def totals(key_correct, key_n):
        c = sum(w[key_correct] for w in weekly)
        n = sum(w[key_n] for w in weekly)
        return {'correct': c, 'n': n, 'pct': round(100 * c / n, 1) if n else None}

    overall = {
        'model_a': totals('model_a_correct', 'model_a_n'),
        'model_b': totals('model_b_correct', 'model_b_n'),
        'market': totals('market_correct', 'market_n'),
    }

    # Calibration: bucket by Model B's predicted probability (fallback Model A),
    # compare average predicted prob in that bucket to actual win rate.
    buckets = [(0, 0.55, '<55%'), (0.55, 0.60, '55-60%'), (0.60, 0.65, '60-65%'),
               (0.65, 0.70, '65-70%'), (0.70, 0.80, '70-80%'), (0.80, 1.01, '80%+')]
    calibration = []
    for lo, hi, label in buckets:
        bucket_games = []
        for g in all_games:
            prob = g.get('model_b_home_win_prob') if g.get('model_b_home_win_prob') is not None else g.get('model_a_home_win_prob')
            if prob is None or g.get('actual_home_win') is None:
                continue
            pick_prob = max(prob, 1 - prob)  # probability of whichever side was picked
            if lo <= pick_prob < hi:
                bucket_games.append((pick_prob, g))
        if bucket_games:
            avg_pred = sum(p for p, _ in bucket_games) / len(bucket_games)
            correct_count = sum(
                1 for _, g in bucket_games
                if (g.get('model_b_correct') if g.get('model_b_correct') is not None else g.get('model_a_correct'))
            )
            calibration.append({
                'bucket': label, 'n': len(bucket_games),
                'avg_predicted': round(avg_pred * 100, 1),
                'actual_rate': round(100 * correct_count / len(bucket_games), 1),
            })

    return {'weeks': weekly, 'overall': overall, 'calibration': calibration}


def build_teams_js(ratings):
    return [{'team': r['team'], 'name': r['name'], 'off': r['off'], 'def': r['def'], 'net': r['net']} for r in ratings]


def main():
    print("Loading current ratings...")
    ratings = load_current_ratings()
    teams_js = build_teams_js(ratings)

    print("Loading all saved predictions...")
    all_preds = load_all_predictions()
    all_graded = load_all_graded()

    weeks_js = {}
    for key, preds in sorted(all_preds.items()):
        season, week = key
        graded = all_graded.get(key, [])
        graded_lookup = {(g['home'], g['away']): g for g in graded}
        weeks_js[f"{season}_week{week}"] = {
            'season': season, 'week': week,
            'games': build_games_js(preds, graded_lookup),
        }

    latest_key = max(all_preds.keys()) if all_preds else None
    latest_label = f"{latest_key[0]}_week{latest_key[1]}" if latest_key else None

    print("Building season accuracy summary...")
    accuracy_js = build_accuracy_summary(all_graded)

    if not all_preds:
        foot_html = f"Trained on: current nflfastR history<br>{len(ratings)} teams rated<br>No predictions saved yet"
    else:
        foot_html = f"Trained on: current nflfastR history<br>{len(weeks_js)} week(s) saved<br>Latest: {latest_label}"

    with open(TEMPLATE_PATH) as f:
        template = f.read()

    html = template.replace('__TEAMS_JSON__', json.dumps(teams_js, indent=2))
    html = html.replace('__WEEKS_JSON__', json.dumps(weeks_js, indent=2))
    html = html.replace('__LATEST_WEEK__', json.dumps(latest_label))
    html = html.replace('__ACCURACY_JSON__', json.dumps(accuracy_js, indent=2))
    html = html.replace('__SIDEBAR_FOOT__', foot_html)

    with open(OUTPUT_PATH, 'w') as f:
        f.write(html)
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == '__main__':
    main()
