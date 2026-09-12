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
import sys
from datetime import datetime, timezone
from pathlib import Path

# config is a pure-constants module with no third-party imports, so unlike
# generate_picks_pdf below there is nothing here for a module-level import to
# take down. sys.path is set explicitly rather than relying on the script's
# own directory, so this still resolves when the module is imported by a test
# rather than run as a script.
sys.path.insert(0, str(Path(__file__).parent))
from config import MODEL_VERSION, VERSION_HISTORY

# generate_picks_pdf is imported lazily, inside the PDF loop in main() --
# NOT here. It pulls in reportlab, and a module-level import would mean a
# reportlab problem takes down the entire dashboard build rather than just
# the PDFs. The dashboard is the actual deliverable and has been generated
# fine without PDFs for most of this project's life; the printable sheet is
# a nice-to-have on top. Making the dashboard's availability depend on a
# rendering library it doesn't otherwise need was a regression introduced
# with the PDF feature on 2026-09-04, not a deliberate choice.
# Guarded by tests/test_weekly_pipeline.py.

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / 'data'
PRED_DIR = ROOT / 'predictions'
DIST_DIR = ROOT / 'dist'
RESULTS_DIR = ROOT / 'results'
TEMPLATE_PATH = ROOT / 'src' / 'dashboard_template.html'
OUTPUT_PATH = ROOT / 'index.html'  # served as the default page by GitHub Pages

# Minimum games in a live calibration bucket before its "actual rate" is
# treated as meaning anything. 20 is a judgement call, not a derived value:
# at n=20 the 95% interval on a rate is still roughly +/-20 points, so this
# is a floor for "not obviously noise" rather than a threshold for
# statistical confidence. Buckets under it are kept and flagged, never
# silently dropped.
MIN_CALIBRATION_BUCKET_N = 20


def load_current_ratings():
    path = DATA_DIR / 'current_ratings.json'
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run weekly_update.py first -- it writes this "
            f"file as part of building current team ratings."
        )
    with open(path) as f:
        return json.load(f)


def load_playoff_odds():
    """Unlike load_current_ratings, this is deliberately tolerant of a
    missing file -- weekly_update.py's save_playoff_odds() can fail soft
    (simulation is a non-critical feature), so the dashboard must not
    crash if it hasn't run yet or failed on a given run."""
    path = DATA_DIR / 'playoff_odds.json'
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def load_agent_log():
    """Booth's audit history, written by .github/workflows/collect-agent-log.yml.

    Absent until that workflow has run, so a missing file is a normal state and
    returns None rather than raising. It does NOT return {} -- the Team
    Deep-Dive page rendered empty for months because a missing file came back
    as an empty dict that every caller treated as real data, and the page said
    nothing. None forces the caller to decide, and the page says the log has
    not been collected yet.
    """
    path = DATA_DIR / 'agent_log.json'
    if not path.exists():
        print("  No data/agent_log.json yet -- run the Collect Booth's audit "
              "log workflow. The reliability page will say so rather than "
              "render an empty section.")
        return None
    with open(path) as f:
        return json.load(f)


def load_calibration():
    """Backtest-derived calibration written by src/calibration.py.

    Tolerant of a missing file for the same reason as playoff odds, but for a
    different failure: calibration.py needs six seasons of play-by-play and
    takes minutes, so it is run deliberately rather than on every dashboard
    build. A checkout that has never run it still has to produce a dashboard.

    Deliberately does NOT recompute anything. The numbers in this file came
    from a specific machine on a specific date, and the cross-platform
    reproducibility finding says that matters -- so the file's own provenance
    block is passed through to the page and displayed, rather than the
    dashboard silently implying the figures were computed here and now.
    """
    path = DATA_DIR / 'calibration.json'
    if not path.exists():
        return None
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

        notes = p.get('context_notes') or []
        # Backward compat with predictions saved before this change (single qb_note field)
        if p.get('qb_note'):
            notes = notes + [p['qb_note']]

        games.append({
            'away': p['away'], 'home': p['home'],
            # .get(), not [], and the reason is a file that exists right now:
            # predictions/2026_week1.json was written before these fields did,
            # and predictions are permanent once saved -- weekly_update refuses
            # to overwrite one. So every already-saved week reaches this line
            # without them, for good, and a subscript here would take the
            # Week Board down rather than render a card with no start time.
            # Absent stays absent: None, never a fabricated date.
            'gameday': p.get('gameday'),
            'gametime_et': p.get('gametime_et'),
            'weekday': p.get('weekday'),
            'spread': p.get('spread_line'),
            'fbA_home': round(model_a * 100, 1),
            'mktB_home': round((model_b if model_b is not None else model_a) * 100, 1),
            'flag': " ".join(notes),
            'notes': notes,
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
        # A week with nothing graded is not a data point, and emitting one puts
        # a fiction in the JSON that every consumer then has to know about.
        # 2026 Week 1 was graded before it was played, so results/ held an empty
        # list for it -- and the dashboard printed "2026 Wk 1  0/0  0/0  0/0" in
        # the Weekly Trend table, which reads as "we went 0 for 0" rather than
        # "not played yet", and gave the cumulative trend chart a second point
        # to draw a flat line to. Three steady-looking trend lines, entirely an
        # artifact of charting an empty week.
        #
        # Dropped here rather than filtered in the page's JavaScript so the
        # generated data has one meaning, not one meaning plus a convention the
        # reader has to apply.
        if not graded:
            continue
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
    #
    # Buckets below MIN_CALIBRATION_BUCKET_N are marked underpowered rather
    # than dropped: the count is still real information, but an "actual rate"
    # computed from one or two games is noise, and plotting it against the
    # perfect-calibration line presents that noise as a finding. Before this
    # guard the live dashboard was charting buckets of n=1 asserting 0% and
    # 100% actual rates off single games -- from 14 graded games in total.
    # Live calibration only becomes meaningful after many weeks; the
    # backtest-derived reliability diagram (data/calibration.json, ~1087
    # games) is what carries the real calibration claim.
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
                'underpowered': len(bucket_games) < MIN_CALIBRATION_BUCKET_N,
            })

    n_graded = len(all_games)
    return {
        'weeks': weekly,
        'overall': overall,
        'calibration': calibration,
        'n_graded': n_graded,
        'min_bucket_n': MIN_CALIBRATION_BUCKET_N,
        # True when nothing in the live calibration panel is worth plotting.
        'calibration_underpowered': all(c['underpowered'] for c in calibration) if calibration else True,
    }


def build_teams_js(ratings, playoff_odds=None):
    """Team rows for the Power Ratings table.

    Playoff odds are joined here rather than looked up in the browser so the
    table can SORT by them -- the sort reads `a[sortKey]` off the team object,
    so a value living in a separate lookup would render but never sort, which
    is the kind of half-working column nobody notices is broken.

    A team with no odds gets None, not 0. Zero is a real playoff chance and
    would rank a team last on merit; None means "not simulated" and the cell
    says so. The same distinction the SOS column already makes.

    The '#' the table prints is `rank`, computed here from the net-rating
    order rather than in the browser from the row's position in whatever the
    reader last sorted by. Position-in-sort would relabel the ninth-best team
    "#1" the moment somebody sorted by playoff odds -- on a page titled Power
    Ratings, and "#1" is the part a casual reader carries away. Computed once
    here, every view agrees, and it also survives search filtering.
    """
    odds = {}
    if playoff_odds:
        for row in playoff_odds.get('teams') or []:
            if row.get('team') is not None:
                odds[row['team']] = row.get('playoff_pct')

    # Ties broken by team code so the ranking is the same on every run; two
    # teams on identical net ratings must not swap places between builds and
    # show up as a diff nobody made.
    order = sorted(ratings, key=lambda r: (-r['net'], r['team']))
    rank_of = {r['team']: i + 1 for i, r in enumerate(order)}

    return [{'team': r['team'], 'name': r['name'], 'off': r['off'], 'def': r['def'], 'net': r['net'],
             'sos': r.get('sos'), 'games_played': r.get('games_played'),
             'rank': rank_of[r['team']],
             'playoff': odds.get(r['team'])} for r in ratings]


def load_team_history():
    """Merges static historical season-end ratings (2020-2025, computed
    once from real backtested data) with any live in-season weekly data
    that weekly_update.py has been appending since -- building a single
    continuous timeline per team: season-end points for past years, then
    week-by-week points for the current season as it's actually played."""
    static_path = DATA_DIR / 'team_history.json'
    if not static_path.exists():
        # Loudly, because quietly is how this broke. The file had been sitting
        # in src/ rather than data/ since it was uploaded, so this branch
        # returned {} on every build and the Team Deep-Dive page rendered "No
        # team history data available yet" for all 32 teams -- while the
        # roadmap listed the page as Done. A missing-file branch that returns
        # empty and says nothing produces a page that looks deliberate.
        print(f"  WARNING: {static_path} not found -- the Team Deep-Dive page "
              f"will render empty. This file is committed; if it is missing, "
              f"something moved it.")
        return {}
    with open(static_path) as f:
        static_data = json.load(f)
    names = static_data.get('names', {})
    history = static_data.get('history', {})

    timeline = {team: [] for team in names}
    for team, points in history.items():
        for p in sorted(points, key=lambda x: x['season']):
            timeline.setdefault(team, []).append({'label': str(p['season']), 'net': p['net']})

    # Layer in any live current-season files (data/team_history_2026.json etc.),
    # sorted by season so multiple seasons of live data would stack correctly.
    live_files = sorted(DATA_DIR.glob('team_history_*.json'))
    for f in live_files:
        season = f.stem.replace('team_history_', '')
        with open(f) as lf:
            live_data = json.load(lf)
        for team, points in live_data.items():
            timeline.setdefault(team, [])
            for p in sorted(points, key=lambda x: x['week']):
                timeline[team].append({'label': f"{season} Wk{p['week']}", 'net': p['net']})

    return {'names': names, 'timeline': timeline}


def main():
    print("Loading current ratings...")
    ratings = load_current_ratings()

    print("Loading playoff odds...")
    playoff_odds = load_playoff_odds()

    # Joined into the team rows, not injected separately: playoff odds are a
    # column on Power Ratings now, and the table sorts by reading the value
    # off the team object.
    teams_js = build_teams_js(ratings, playoff_odds)

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

    # Printable picks PDFs, one per saved week. Generated here rather than
    # client-side because the sheet has to match exactly what the board
    # shows, and browser print output silently varies by browser. Only the
    # weeks that actually produce a file get listed, so the dashboard's
    # download control can hide itself rather than link to a 404.
    print("Generating printable picks PDFs...")
    pdf_weeks = []
    try:
        from generate_picks_pdf import build_picks_rows, render_picks_pdf
    except Exception as exc:
        # reportlab missing or broken: skip PDFs entirely and carry on. The
        # dashboard still builds, and the download control hides itself
        # because pdf_weeks stays empty.
        print(f"  WARNING: PDF generation unavailable ({exc}) -- dashboard will build without printable sheets.")
        build_picks_rows = render_picks_pdf = None

    for key, preds in sorted(all_preds.items()) if build_picks_rows else []:
        season, week = key
        label = f"{season}_week{week}"
        try:
            rows = build_picks_rows(preds)
            versions = {p.get('model_version') for p in preds if p.get('model_version')}
            model_version = versions.pop() if len(versions) == 1 else 'mixed'
            render_picks_pdf(rows, season, week, model_version,
                             DIST_DIR / f'picks_{label}.pdf')
            pdf_weeks.append(label)
        except Exception as exc:
            # A malformed or empty week must not take the whole dashboard
            # build down -- skip that week's PDF and say so out loud.
            print(f"  WARNING: no PDF for {label}: {exc}")
    print(f"  {len(pdf_weeks)} PDF(s) written to {DIST_DIR}")

    print("Building season accuracy summary...")
    accuracy_js = build_accuracy_summary(all_graded)

    calibration_js = load_calibration()
    if calibration_js is None:
        print("  NOTE: data/calibration.json absent -- reliability diagram will "
              "be omitted. Run src/calibration.py to produce it.")
    else:
        print(f"  Backtest calibration loaded "
              f"({calibration_js['models']['model_a']['metrics']['n']} games, "
              f"generated {calibration_js['generated_at']})")

    print("Loading Booth's audit log...")
    agent_log = load_agent_log()

    print("Loading team history...")
    team_history_js = load_team_history()

    generated_at = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    if not all_preds:
        foot_html = f"Trained on: current nflfastR history<br>{len(ratings)} teams rated<br>No predictions saved yet<br><span class='foot-freshness'>Data as of {generated_at}</span>"
    else:
        foot_html = f"Trained on: current nflfastR history<br>{len(weeks_js)} week(s) saved<br>Latest: {latest_label}<br><span class='foot-freshness'>Data as of {generated_at}</span>"

    with open(TEMPLATE_PATH) as f:
        template = f.read()

    html = template.replace('__TEAMS_JSON__', json.dumps(teams_js, indent=2))
    # Only the run's own metadata: the per-team odds now travel inside
    # teams_js so the Power Ratings table can sort by them.
    html = html.replace('__PLAYOFF_META_JSON__', json.dumps(
        {k: (playoff_odds or {}).get(k) for k in
         ('n_simulations', 'games_played', 'games_remaining', 'season')},
        indent=2))
    html = html.replace('__WEEKS_JSON__', json.dumps(weeks_js, indent=2))
    html = html.replace('__LATEST_WEEK__', json.dumps(latest_label))
    html = html.replace('__PICKS_PDFS_JSON__', json.dumps(pdf_weeks))
    html = html.replace('__ACCURACY_JSON__', json.dumps(accuracy_js, indent=2))
    html = html.replace('__CALIBRATION_JSON__', json.dumps(calibration_js, indent=2))
    html = html.replace('__TEAM_HISTORY_JSON__', json.dumps(team_history_js, indent=2))
    # null, not {}, when the collector has never run. The page distinguishes
    # "no audits recorded yet" from "audits recorded, none of them found
    # anything" -- those are opposite claims about the verifier, and an empty
    # object would let the page make the flattering one by accident.
    html = html.replace('__AGENT_LOG_JSON__', json.dumps(agent_log, indent=2))
    # The Changelog page is rendered from config.VERSION_HISTORY, so the
    # release notes on the site and the constant the model actually runs under
    # cannot drift apart -- they are the same object.
    html = html.replace('__VERSION_HISTORY_JSON__', json.dumps(VERSION_HISTORY, indent=2))
    html = html.replace('__MODEL_VERSION__', json.dumps(MODEL_VERSION))
    html = html.replace('__SIDEBAR_FOOT__', foot_html)

    with open(OUTPUT_PATH, 'w') as f:
        f.write(html)
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == '__main__':
    main()
