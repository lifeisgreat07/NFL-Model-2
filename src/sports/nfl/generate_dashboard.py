"""
Generates dashboard.html (as index.html) from real, saved data:
predictions/nfl/*.json, results/nfl/*_graded.json, and data/nfl/current_ratings.json.
Deterministic template fill -- same inputs always produce the same output.

v2 additions: bundles ALL saved weeks (not just the latest) for past-week
browsing, aggregates all graded results into a real season accuracy record
and calibration table, and passes through confidence ranking + why-
breakdown that weekly_update.py now computes per game.
"""
from __future__ import annotations

import base64
import hashlib
import json
import math
from collections.abc import Collection, Sequence
from datetime import UTC, datetime
from html import escape as _escape
from pathlib import Path
from typing import Any

from src.core.template_parts import read_template

# config is a pure-constants module with no third-party imports, so unlike
# generate_picks_pdf below there is nothing here for a module-level import to
# take down. It resolves the same way run as `python -m` or imported by a
# test: both put the repository root on the path.
from src.sports.nfl.config import MODEL_VERSION, TRAIN_SEASONS, VERSION_HISTORY
from src.sports.nfl.page_comments import strip_page_comments

# generate_picks_pdf is imported lazily, inside the PDF loop in main() --
# NOT here. It pulls in reportlab, and a module-level import would mean a
# reportlab problem takes down the entire dashboard build rather than just
# the PDFs. The dashboard is the actual deliverable and has been generated
# fine without PDFs for most of this project's life; the printable sheet is
# a nice-to-have on top. Making the dashboard's availability depend on a
# rendering library it doesn't otherwise need was a regression introduced
# with the PDF feature on 2026-09-04, not a deliberate choice.
# Guarded by tests/test_weekly_pipeline.py.
# The shared locations, and the one rule for reading a week out of a file
# name (src/sports/nfl/paths.py, Stage 32 item 15). parse_week_stem keeps its name here
# because tests and callers use it.
from src.sports.nfl.paths import (
    DATA_DIR,
    PRED_DIR,
    RESULTS_DIR,
    ROOT,
    SHARED_DATA_DIR,
    STATUS_DIR,
)
from src.sports.nfl.paths import parse_week as parse_week_stem

DIST_DIR = ROOT / 'dist'
NEWS_DIR = DATA_DIR / 'team_news'
TV_DIR = DATA_DIR / 'tv'
OUTPUT_PATH = ROOT / 'index.html'  # served as the default page by GitHub Pages

#: (season, week).
WeekKey = tuple[int, int]
#: One saved pick, as read from predictions/ or results/nfl/.
Pick = dict[str, Any]
#: One game card, as the page's weeks object carries it.
Game = dict[str, Any]

# Minimum games in a live calibration bucket before its "actual rate" is
# treated as meaning anything. 20 is a judgement call, not a derived value:
# at n=20 the 95% interval on a rate is still roughly +/-20 points, so this
# is a floor for "not obviously noise" rather than a threshold for
# statistical confidence. Buckets under it are kept and flagged, never
# silently dropped.
MIN_CALIBRATION_BUCKET_N = 20

# Season Accuracy's second score (Stage 19): the average log loss of each
# forecast's probability for what actually happened. The page calls it
# "How sure, and how right" -- "log loss" is banned there by
# tests/test_plain_language.py, and Mark chose plain wording over an
# exception (2026-09-28). 50 games is the floor CLAUDE.md's Stage 19 plan
# set: below it one confident miss moves the score more than the models
# differ, so the block is absent rather than shown as a finding.
FORECAST_SCORE_MIN_GAMES = 50
# A probability of exactly 0 or 1 for the side that lost would score
# infinity. No stored probability is that extreme today; the clamp means one
# never could take the page down.
FORECAST_SCORE_EPS = 1e-6
FORECAST_SOURCES = (('model_a', 'model_a_home_win_prob'),
                    ('model_b', 'model_b_home_win_prob'),
                    ('market', 'market_prob_home'))


def build_forecast_score(all_games: list[Game]) -> dict[str, Any] | None:
    """Mean log loss per forecast, over the games ALL THREE have a number for.

    Paired on purpose: a game only one forecast priced would let the three
    scores be averages over different games, and the smaller set is not the
    same test (backtest()'s dropna trap in CLAUDE.md, in page form). A tie,
    or a game with no result, has no winner to score and is left out.
    Returns None below FORECAST_SCORE_MIN_GAMES.
    """
    losses = {name: [] for name, _ in FORECAST_SOURCES}
    for g in all_games:
        actual = g.get('actual_home_win')
        if actual not in (0, 1):
            continue
        probs = [g.get(key) for _, key in FORECAST_SOURCES]
        if any(not isinstance(p, (int, float)) for p in probs):
            continue
        for (name, _), p in zip(FORECAST_SOURCES, probs):
            p_actual = p if actual == 1 else 1 - p
            p_actual = min(max(p_actual, FORECAST_SCORE_EPS), 1 - FORECAST_SCORE_EPS)
            losses[name].append(-math.log(p_actual))
    n = len(losses['model_a'])
    if n < FORECAST_SCORE_MIN_GAMES:
        return None
    return {
        'n': n,
        # What calling every game 50-50 scores, whatever happens: ln 2.
        'coin_flip': round(math.log(2), 3),
        **{name: round(sum(v) / n, 3) for name, v in losses.items()},
    }


def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """The 95% Wilson score interval for a proportion, as (lo, hi).

    The same formula as `src.sports.nfl.research.calibration.wilson_interval`,
    which the page code does not import (no production module reaches into
    research/); tests/test_against_market.py holds the two equal.
    """
    if n == 0:
        return (0.0, 1.0)
    p = successes / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
    return ((centre - margin) / denom, (centre + margin) / denom)


AGAINST_MARKET_MODELS = (('model_a', 'model_a_home_win_prob', 'model_a_correct'),
                         ('model_b', 'model_b_home_win_prob', 'model_b_correct'))


def build_against_market(all_games: list[Game]) -> dict[str, Any]:
    """Stage 46 item 9: how each model did on the graded games where it
    picked against the market's favourite.

    A model picks the home team at 50% or more (how its pick is graded); the
    market's favourite is the side its no-vig chance puts over 50%, and a
    game the market prices at exactly 50% has no favourite and is left out,
    as is a game with no price or no grade. Reported with a 95% Wilson
    interval, because at a few games a season the interval is the finding:
    the page leads with it, not with the rate.
    """
    out: dict[str, Any] = {}
    priced = 0
    for name, prob_key, correct_key in AGAINST_MARKET_MODELS:
        n = right = 0
        for g in all_games:
            prob, market, correct = g.get(prob_key), g.get('market_prob_home'), g.get(correct_key)
            if not isinstance(prob, (int, float)) or not isinstance(market, (int, float)) or correct not in (0, 1):
                continue
            if name == 'model_a':
                priced += 1
            if market == 0.5:
                continue
            if (prob >= 0.5) != (market > 0.5):
                n += 1
                right += int(correct)
        lo, hi = wilson_interval(right, n)
        out[name] = {'n': n, 'right': right, 'lo': round(100 * lo, 1), 'hi': round(100 * hi, 1)}
    out['priced'] = priced
    return out


def load_current_ratings() -> list[dict[str, Any]]:
    path = DATA_DIR / 'current_ratings.json'
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run weekly_update.py first -- it writes this "
            f"file as part of building current team ratings."
        )
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def load_playoff_odds() -> dict[str, Any] | None:
    """Unlike load_current_ratings, this is deliberately tolerant of a
    missing file -- weekly_update.py's save_playoff_odds() can fail soft
    (simulation is a non-critical feature), so the dashboard must not
    crash if it hasn't run yet or failed on a given run."""
    path = DATA_DIR / 'playoff_odds.json'
    if not path.exists():
        return None
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def load_agent_log() -> dict[str, Any] | None:
    """Booth's audit history, written by .github/workflows/collect-agent-log.yml.

    Absent until that workflow has run, so a missing file is a normal state and
    returns None rather than raising. It does NOT return {} -- the Team
    Deep-Dive page rendered empty for months because a missing file came back
    as an empty dict that every caller treated as real data, and the page said
    nothing. None forces the caller to decide, and the page says the log has
    not been collected yet.
    """
    path = SHARED_DATA_DIR / 'agent_log.json'
    if not path.exists():
        print("  No data/agent_log.json yet -- run the Collect Booth's audit "
              "log workflow. The reliability page will say so rather than "
              "render an empty section.")
        return None
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def agent_log_for_page(log: dict[str, Any] | None) -> dict[str, Any] | None:
    """The part of Booth's audit log the page reads: the summary and when it
    was collected. The per-audit records (`audits`) were most of the log and
    nothing on the page reads them; they stay in data/agent_log.json.
    None stays None -- the page says the log has not been collected yet.
    Stage 26 item 11."""
    if log is None:
        return None
    return {k: log.get(k) for k in ('generated_utc', 'summary')}


def load_recent_runs(path: Path | None = None) -> dict[str, Any] | None:
    """The scheduled jobs' last runs, read from GitHub by
    src/sports/nfl/recent_runs.py in the deploy job (Stage 41 item 4).

    The file is gitignored and only the deploy writes it, so every other
    build -- a local one, the test suite's, the browser checks' -- has none,
    and so does a deploy whose read failed. None, not [], so the page says
    the history was not read rather than that nothing ran.
    """
    path = path or SHARED_DATA_DIR / 'recent_runs.json'
    if not path.exists():
        print("  No data/recent_runs.json -- the deploy writes it; the page will "
              "say the run history was not read for this build.")
        return None
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def load_lock_proof(path: Path | None = None) -> dict[str, Any] | None:
    """Every commit that changed each locked week's picks, written by
    src/sports/nfl/lock_proof.py in the site build (Stage 46 item 5). None
    when this build has none (a local build that skipped it, or a shallow
    clone), and the page then shows no lock line."""
    path = path or DATA_DIR / 'lock_proof.json'
    if not path.exists():
        print("  No data/nfl/lock_proof.json -- the site build writes it; the page will show no lock line.")
        return None
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def load_calibration() -> dict[str, Any] | None:
    """Backtest-derived calibration written by src/sports/nfl/research/calibration.py.

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
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def load_all_predictions() -> dict[WeekKey, list[Pick]]:
    """Returns {(season, week): [predictions...]} for every saved week."""
    out = {}
    for f in PRED_DIR.glob('*_week*.json'):
        parsed = parse_week_stem(f.stem)
        if parsed is None:
            continue
        with open(f, encoding='utf-8') as pf:
            out[parsed] = json.load(pf)
    return out


def load_previews(preview_dir: Path | None = None,
                  locked: Collection[WeekKey] = ()) -> dict[WeekKey, list[Pick]]:
    """{(season, week): [picks]} for every preview whose week is NOT locked.

    predictions/nfl/preview/ holds what a holding run (Tuesday, usually) would
    pick if the week locked then (src/weekly_update.save_preview). The
    moment the week is locked its preview is ignored here, so the page can
    never show a preview beside, or instead of, a lock."""
    preview_dir = PRED_DIR / 'preview' if preview_dir is None else preview_dir
    out = {}
    if not preview_dir.exists():
        return out
    for f in preview_dir.glob('*_week*.json'):
        parsed = parse_week_stem(f.stem)
        if parsed is None or parsed in locked:
            continue
        with open(f, encoding='utf-8') as pf:
            out[parsed] = json.load(pf)
    return out


def skipped_weeks(skipped_dir: Path | None = None) -> set[WeekKey]:
    """{(season, week)} for every week recorded in predictions/nfl/skipped/: every
    game kicked off with nothing locked (weekly_update.record_skipped_week).
    Such a week is over, so a preview left from its Tuesday run is not shown
    as if it were still coming (Stage 30 item 3)."""
    skipped_dir = PRED_DIR / 'skipped' if skipped_dir is None else skipped_dir
    if not skipped_dir.exists():
        return set()
    return {w for w in (parse_week_stem(f.stem) for f in skipped_dir.glob('*_week*.json'))
            if w is not None}


def load_all_graded() -> dict[WeekKey, list[Pick]]:
    """Returns {(season, week): [graded predictions...]} for every graded week."""
    out = {}
    for f in RESULTS_DIR.glob('*_week*_graded.json'):
        stem = f.stem.replace('_graded', '')
        parsed = parse_week_stem(stem)
        if parsed is None:
            continue
        with open(f, encoding='utf-8') as gf:
            out[parsed] = json.load(gf)
    return out


def load_game_status(status_dir: Path = STATUS_DIR) -> dict[WeekKey, dict[tuple[str, str], dict]]:
    """{(season, week): {(home, away): entry}} from the weekend refresh's
    snapshots (src/sports/nfl/weekend_refresh.py, Stage 15): each game's status, and its
    score once final.

    A week with no snapshot is simply absent, and the card then shows its
    kickoff and nothing else -- weeks graded before the refresh existed never
    get one. Absent stays absent: nothing here invents a status."""
    out = {}
    if not status_dir.exists():
        print(f"  NOTE: {status_dir} absent -- no weekend refresh has run yet, "
              f"so cards show kickoff times only.")
        return out
    for f in status_dir.glob('*_week*.json'):
        parsed = parse_week_stem(f.stem)
        if parsed is None:
            continue
        with open(f, encoding='utf-8') as sf:
            snapshot = json.load(sf)
        out[parsed] = {(g['home'], g['away']): g for g in snapshot.get('games', [])}
    return out


def load_tv(tv_dir: Path = TV_DIR) -> dict[WeekKey, dict[tuple[str, str], dict]]:
    """{(season, week): {(home, away): record}} from src/sports/nfl/tv_channels.py's
    week files (Stage 15). `exceptions.json` shares the folder and is not a
    week; the `*_week*.json` pattern does not match it. A game whose channel failed a
    check has an empty `networks` list in its record, and the card then
    shows no channel: nothing here second-guesses the checks."""
    out = {}
    if not tv_dir.exists():
        return out
    for f in tv_dir.glob('*_week*.json'):
        parsed = parse_week_stem(f.stem)
        if parsed is None:
            continue
        with open(f, encoding='utf-8') as tf:
            body = json.load(tf)
        out[parsed] = {(r['home'], r['away']): r for r in body.get('games', [])
                       if r.get('home') and r.get('away')}
    return out


def html_escape(text: str) -> str:
    """Text into markup. Quotes are left alone: nothing here goes into an attribute."""
    return _escape(text, quote=False)


# The data fills are written without indentation or spaces after separators:
# nobody reads the built page's JSON by eye, and indentation was a large
# share of its bytes (Stage 26 item 11). data/nfl/*.json keep their own layout.
COMPACT = {'separators': (',', ':')}


def safe_json(obj: Any, **kwargs: Any) -> str:
    """JSON that can sit inside the page's <script> element without ending it.

    Every data fill lands between <script> and </script>, and the HTML parser
    ends a script at the first `</script` it meets -- inside a JS string or
    not. json.dumps leaves `<` alone, so any string reaching the page could
    close the script and start markup: an audit comment on GitHub (the
    collector accepts a report from any account), a context note from the
    web, a player name from nflverse. Stage 23, from the 2026-09-28 audit,
    which reproduced it through the agent log.

    Every `<` becomes the JSON escape `\\u003c`, not only `</`. `<!--` inside a
    script also changes how the parser reads the rest of it, and a JSON `<`
    only ever appears inside a string, where `\\u003c` means the same
    character to JSON.parse and to JavaScript. json.dumps already escapes
    every non-ASCII character, U+2028 and U+2029 included.
    """
    return json.dumps(obj, **kwargs).replace('<', '\\u003c')


def _signed(x, places=4):
    """+0.0021 / &minus;0.0109, the way Model Lab's rows already write signs."""
    s = f'{abs(x):.{places}f}'
    return ('&minus;' if x < 0 else '+') + s


def _seasons(seasons):
    return f'{seasons[0]}&ndash;{seasons[-1]}' if len(seasons) > 1 else str(seasons[0])


def _plain_signed(x, places=4):
    """-0.0109 as the text a screen reader is given: a real minus sign,
    written as &minus; because the page is written in the platform's default
    encoding, and on Windows (cp1252) a literal U+2212 crashes the build. A
    non-zero bound that would print as 0.0000 gets the decimals it needs, so
    "+0.0000 to +0.0058, excludes zero" never reads as a contradiction."""
    while places < 8 and x != 0 and round(abs(x), places) == 0:
        places += 1
    return ('&minus;' if x < 0 else '+') + f'{abs(x):.{places}f}'


def interval_glyph(h: dict[str, Any], width: int = 96, height: int = 14, pad: int = 5) -> str:
    """A result's interval drawn against zero (Stage 18): a line from the low
    to the high end with a tick at each, a dot at the difference, and a
    vertical line at zero. What it shows is the one thing the decision rests
    on -- whether the interval includes zero -- so it is drawn on each row's
    OWN scale, symmetric about zero, and glyphs on different rows are not
    comparable in length. The figures are in the sentence beside it.

    Every glyph draws the same visible frame first, so each row's graph is
    one size, in one place, with zero at its centre, and only the interval
    inside it moves (Mark, 2026-09-28: the bare lines looked like graphs of
    different sizes in different places).

    role="img" with a text equivalent (UX review, Model Lab):
    "-0.0109, interval -0.0319 to +0.0096, includes zero"."""
    lo, hi, d = h['ci'][0], h['ci'][1], h['diff']
    span = max(abs(lo), abs(hi), abs(d)) or 1.0

    def x(v):
        return round(pad + (v + span) / (2 * span) * (width - 2 * pad), 1)

    mid = height / 2
    zero = 'includes zero' if lo <= 0 <= hi else 'excludes zero'
    label = f"{_plain_signed(d)}, interval {_plain_signed(lo)} to {_plain_signed(hi)}, {zero}"
    return (f'<svg class="lab-ci" role="img" aria-label="{label}" viewBox="0 0 {width} {height}" '
            f'width="{width}" height="{height}">'
            f'<rect class="lab-ci-frame" x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="3"/>'
            f'<line class="lab-ci-zero" x1="{x(0)}" y1="0" x2="{x(0)}" y2="{height}"/>'
            f'<line class="lab-ci-range" x1="{x(lo)}" y1="{mid}" x2="{x(hi)}" y2="{mid}"/>'
            f'<line class="lab-ci-range" x1="{x(lo)}" y1="{mid - 4}" x2="{x(lo)}" y2="{mid + 4}"/>'
            f'<line class="lab-ci-range" x1="{x(hi)}" y1="{mid - 4}" x2="{x(hi)}" y2="{mid + 4}"/>'
            f'<circle class="lab-ci-point" cx="{x(d)}" cy="{mid}" r="3"/></svg>')


def _registered_result(e):
    """The Result cell for a pre-registered answer, from its file's own
    figures, leading with its interval drawn against zero (Stage 18)."""
    h = e['headline']
    if h is None:
        body = html_escape(e.get('reason') or 'Deferred.')
    else:
        where = {
            'confirmation': f"confirmation seasons {_seasons(h['seasons'])}",
            'validation': f"validation screen {_seasons(h['seasons'])}; it did not go on to confirmation",
            'measurement': f"all of {_seasons(h['seasons'])}",
            'screen': f"screen on {_seasons(h['seasons'])}",
        }[h['step']]
        model = f"{h['model']}, " if h['model'] else ''
        metric = h['metric'] if h['metric'] == 'log loss' else f"{h['metric']} of {html_escape(h['of'])}"
        if not model:
            metric = metric[:1].upper() + metric[1:]
        body = (f"{model}{metric} {_signed(h['diff'])} "
                f"CI [{_signed(h['ci'][0])}, {_signed(h['ci'][1])}] at {round(h['ci_level'] * 100, 2):g}%, "
                f"{where}, {h['n']:,} {h['n_of']}. "
                f"{h.get('note', 'A negative difference favours the new idea.')}")
        body = f'<span class="lab-lead">{interval_glyph(h)}</span>{body}'
    return (f"{body}<span class=\"lab-src\">Pre-registered, {e['stage']} {e['id']} "
            f"&middot; <code>{e['source']}</code></span>")


def render_model_lab_rows(entries: list[dict[str, Any]]) -> str:
    """Model Lab's table rows (Stage 18), rendered into the page at build time
    so the table exists without JavaScript and every #modellab/<slug> link
    still finds its row.

    A moved row's first two cells are its stored HTML, unchanged. The third is
    the decision; when the row was first labelled something else, that label
    follows it, so the mapping onto the five decisions is visible, not
    silent."""
    rows = []
    for e in entries:
        if e['stage'] is None:
            name, result = e['experiment'], e['result']
        else:
            name, result = html_escape(e['title']), _registered_result(e)
        # The pills sit in one wrapping row with a gap and never break inside
        # themselves: "CONFIRMED FINDING" split across two lines of one pill,
        # and DEFERRED and LEAKAGE stacked touching (Mark, 2026-09-28).
        cell = f'<span class="lab-tags"><span class="conf-tag tag-neutral">{e["decision"]}</span>'
        if e['leakage']:
            cell += '<span class="conf-tag tag-neutral">LEAKAGE</span>'
        cell += '</span>'
        if e['label'] != e['decision']:
            cell += f'<span class="lab-first">First labelled {e["label"]}</span>'
        rows.append(f'<tr><td>{name}</td><td>{result}</td><td>{cell}</td></tr>')
    return '\n          '.join(rows)


def load_team_news(news_dir: Path = NEWS_DIR) -> dict[WeekKey, dict[str, Any]]:
    """{(season, week): {'read_at', 'teams'}} from src/sports/nfl/team_news.py's week
    files (Stage 16). Absent folder, absent news: nothing is invented."""
    out = {}
    if not news_dir.exists():
        print(f"  NOTE: {news_dir} absent -- team news has not been read yet, "
              f"so Team Deep-Dive shows no news.")
        return out
    for f in news_dir.glob('*_week*.json'):
        parsed = parse_week_stem(f.stem)
        if parsed is None:
            continue
        with open(f, encoding='utf-8') as nf:
            body = json.load(nf)
        out[parsed] = {'read_at': body.get('read_at'), 'teams': body.get('teams') or {}}
    return out


def week_news(preds: list[Pick], graded: list[Pick], news: dict[str, Any] | None) -> dict[str, Any] | None:
    """The week's news while the week is still being played, else None.
    Items expire with their week: once every pick is graded the news is left
    out of the page, though its file stays in the repository."""
    if news is None or len(graded) >= len(preds):
        return None
    return news


def build_games_js(preds: list[Pick], graded_lookup_by_key: dict[tuple[str, str], Pick],
                   status_by_key: dict[tuple[str, str], dict] | None = None,
                   tv_by_key: dict[tuple[str, str], dict] | None = None) -> list[Game]:
    """Convert one week's saved predictions into the dashboard's game-card
    JS format, joining in graded results (actual outcome, correctness) if
    that week has already been graded, the weekend refresh's status and
    score if a snapshot exists, and the checked TV channel if one was read."""
    status_by_key = status_by_key or {}
    tv_by_key = tv_by_key or {}
    games = []
    for p in preds:
        model_a = p.get('model_a_home_win_prob')
        if model_a is None:
            continue  # old-format prediction file (pre-fix) -- skip rather than fabricate
        model_b = p.get('model_b_home_win_prob')
        key = (p['home'], p['away'])
        graded = graded_lookup_by_key.get(key)
        status = status_by_key.get(key) or {}
        tv = tv_by_key.get(key) or {}
        # ONE network, the first the record shows; an empty list means the
        # channel failed a check and is held back (src/sports/nfl/tv_channels.py).
        network = (tv.get('networks') or [None])[0]

        notes = p.get('context_notes') or []
        # Backward compat with predictions saved before this change (single qb_note field)
        if p.get('qb_note'):
            notes = notes + [p['qb_note']]

        games.append({
            'away': p['away'], 'home': p['home'],
            # .get(), not [], and the reason is a file that exists right now:
            # predictions/nfl/2026_week1.json was written before these fields did,
            # and predictions are permanent once saved -- weekly_update refuses
            # to overwrite one. So every already-saved week reaches this line
            # without them, for good, and a subscript here would take the
            # Week Board down rather than render a card with no start time.
            # Absent stays absent: None, never a fabricated date.
            'gameday': p.get('gameday'),
            # Stage 37 item 6: the saved pick says, or failing that (a week
            # locked before picks carried it) the status snapshot does.
            'neutral': bool(p.get('neutral_site') if p.get('neutral_site') is not None
                            else status.get('neutral_site')),
            'venue': p.get('venue') or status.get('venue'),
            # Stage 38 N1: a pick saved from v2.6 at a neutral site says the
            # home edge was taken out; one saved before says nothing, and the
            # card keeps saying the models gave the home team the edge.
            'edge_out': bool(p.get('home_edge_removed')),
            'gametime_et': p.get('gametime_et'),
            'weekday': p.get('weekday'),
            'spread': p.get('spread_line'),
            'fbA_home': round(model_a * 100, 1),
            'mktB_home': round((model_b if model_b is not None else model_a) * 100, 1),
            # The market's own win probability (Stage 17: the card shows the
            # market as a probability, not only as a spread). None when the
            # pick was saved without one; the card then omits the market mark.
            'mkt_home': (round(p['market_prob_home'] * 100, 1)
                         if p.get('market_prob_home') is not None else None),
            'flag': " ".join(notes),
            'notes': notes,
            'confidence_rank': p.get('confidence_rank'),
            'confidence_points': p.get('confidence_points'),
            'why': p.get('why'),
            'graded': graded is not None,
            # 'tie' for a tied game, None otherwise (Stage 30 item 1). A tie is
            # graded -- it was checked against the result -- but has no winner,
            # so every *_correct below is None. Without this the card could
            # not tell a tie from a miss and drew a red cross.
            'result': graded.get('result') if graded else None,
            'actual_home_win': graded.get('actual_home_win') if graded else None,
            'model_a_correct': graded.get('model_a_correct') if graded else None,
            'model_b_correct': graded.get('model_b_correct') if graded else None,
            # From the weekend refresh (Stage 15). None when this week has no
            # snapshot, and the scores are None until the game is final.
            'status': status.get('status'),
            'away_score': status.get('away_score'),
            'home_score': status.get('home_score'),
            # Stage 17: where to watch, and whether that channel is regional
            # (Sunday-afternoon CBS and FOX games air in some markets only;
            # the page says so in one line rather than on every card).
            'tv': network,
            'tv_regional': bool(network) and tv.get('territory') == 'REGIONAL',
            # The quarterbacks the pick was made with (saved since v2.5, so
            # None for every week locked before it) and why each was chosen:
            # 'override', 'announced', or 'last_game' when no starter had
            # been listed and the pick fell back to last game's.
            'away_qb': p.get('away_qb'), 'home_qb': p.get('home_qb'),
            'away_qb_basis': p.get('away_qb_basis'), 'home_qb_basis': p.get('home_qb_basis'),
        })
    return games


def build_accuracy_summary(all_graded: dict[WeekKey, list[Pick]]) -> dict[str, Any]:
    """Aggregate every graded week into a season-level record + a
    per-week trend + calibration buckets (predicted probability vs
    actual win rate), using Model B (or Model A as fallback) per game."""
    all_games = []
    for (season, week), graded in sorted(all_graded.items()):
        for g in graded:
            all_games.append({**g, 'season': season, 'week': week})

    if not all_games:
        return {'weeks': [], 'overall': None, 'calibration': [], 'forecast_score': None, 'against_market': None}

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
    # backtest-derived reliability diagram (data/nfl/calibration.json, ~1087
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
        # None until FORECAST_SCORE_MIN_GAMES paired games are graded; the
        # page renders nothing for None.
        'forecast_score': build_forecast_score(all_games),
        # Stage 46 item 9: the games each model picked against the market's
        # favourite, with a Wilson interval.
        'against_market': build_against_market(all_games),
    }


def build_teams_js(ratings: list[dict[str, Any]],
                   playoff_odds: dict[str, Any] | None = None) -> list[dict[str, Any]]:
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


def with_rank_change(teams_js: list[dict[str, Any]],
                     previous_rank: dict[str, int] | None) -> list[dict[str, Any]]:
    """Add `rank_change` to each Power Ratings row (Stage 19): places moved
    since the previous weekly update, positive up the table, against the
    ranks previous_ranks() returns. None when there is no previous ranking,
    never 0, because 0 is a real answer -- "did not move" -- and the page
    prints the two differently."""
    def change(t):
        if not previous_rank or t['team'] not in previous_rank:
            return None
        return previous_rank[t['team']] - t['rank']
    return [{**t, 'rank_change': change(t)} for t in teams_js]


def previous_ranks(ratings: list[dict[str, Any]], live_history: dict[str, Any]) -> dict[str, int] | None:
    """Each team's Power Ratings rank at the weekly update before this one.

    `live_history` is one season's data/nfl/team_history_<season>.json: every
    weekly run appends a point for all 32 teams, byes included
    (weekly_update.append_live_history). The current ranking is the
    `ratings` snapshot, which the same run writes; so the latest history week
    must BE that snapshot, and the one before it is the previous ranking.

    Returns None -- and the page shows no movement -- when that cannot be
    said honestly: fewer than two weeks; a team missing from the previous
    week (a partial ranking is not a league rank); or a latest week that does
    not match the snapshot, which would mean comparing against the wrong
    week. That last case prints why, because a silent None there would look
    like a quiet week rather than a broken input.
    """
    weeks = sorted({p['week'] for pts in live_history.values() for p in pts})
    if len(weeks) < 2:
        return None
    latest, prev = weeks[-1], weeks[-2]

    def nets_at(week):
        out = {}
        for team, pts in live_history.items():
            for p in pts:
                if p['week'] == week:
                    out[team] = p['net']
        return out

    teams = {r['team'] for r in ratings}
    now = nets_at(latest)
    if any(r['team'] not in now or abs(now[r['team']] - r['net']) > 1e-9 for r in ratings):
        print(f"  WARNING: data/nfl/current_ratings.json does not match week {latest} of the "
              f"live team history, so Power Ratings shows no rank change this build.")
        return None
    before = nets_at(prev)
    if set(before) != teams:
        return None
    order = sorted(before, key=lambda t: (-before[t], t))
    return {t: i + 1 for i, t in enumerate(order)}


def load_latest_live_history() -> dict[str, Any]:
    """The newest data/nfl/team_history_<season>.json, or {} if there is none."""
    live_files = sorted(DATA_DIR.glob('team_history_*.json'))
    if not live_files:
        return {}
    with open(live_files[-1], encoding='utf-8') as f:
        return json.load(f)


def load_team_history() -> dict[str, Any]:
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
    with open(static_path, encoding='utf-8') as f:
        static_data = json.load(f)
    names = static_data.get('names', {})
    history = static_data.get('history', {})

    timeline = {team: [] for team in names}
    # Offense and defense ride along with net (Stage 19): Team Deep-Dive shows
    # all three, and both history files already carry them. .get(), because a
    # point without them is still a net rating worth drawing; the page shows
    # the split only when both are numbers.
    for team, points in history.items():
        for p in sorted(points, key=lambda x: x['season']):
            timeline.setdefault(team, []).append({'label': str(p['season']), 'net': p['net'],
                                                  'off': p.get('off'), 'def': p.get('def')})

    # Layer in any live current-season files (data/nfl/team_history_2026.json etc.),
    # sorted by season so multiple seasons of live data would stack correctly.
    live_files = sorted(DATA_DIR.glob('team_history_*.json'))
    for f in live_files:
        season = f.stem.replace('team_history_', '')
        with open(f, encoding='utf-8') as lf:
            live_data = json.load(lf)
        for team, points in live_data.items():
            timeline.setdefault(team, [])
            for p in sorted(points, key=lambda x: x['week']):
                timeline[team].append({'label': f"{season} Wk{p['week']}", 'net': p['net'],
                                       'off': p.get('off'), 'def': p.get('def')})

    return {'names': names, 'timeline': timeline}


FONT_DIR = Path(__file__).resolve().parents[3] / 'assets' / 'fonts'


def font_faces_css(font_dir: Path = FONT_DIR) -> str:
    """@font-face rules for the self-hosted Plus Jakarta Sans, as data URIs.

    Stage 12. The page used to load the face from Google Fonts at runtime, so
    a visitor offline, behind a filter, or on a slow link got the fallback
    face -- and CLAUDE.md records a layout defect that is ABSENT in the
    fallback face, so a render without the font can check nothing. The four
    files Mark approved on 2026-09-26 (latin and latin-ext; the normal face
    is one variable file for 400-800) are inlined at build time, which keeps
    the published site a single self-contained file, with no request to any
    font host.

    Every file is checked against the SHA-256 in assets/fonts/manifest.json
    before it is inlined. A mismatch raises: a corrupted font does not fail
    loudly in a browser, it silently falls back, which is the failure this
    exists to remove.
    """
    manifest = json.loads((font_dir / 'manifest.json').read_text(encoding='utf-8'))
    rules = []
    for f in manifest['files']:
        data = (font_dir / f['file']).read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest != f['sha256']:
            raise ValueError(f"{f['file']}: sha256 {digest} does not match the "
                             f"manifest's {f['sha256']}")
        weight = '400 800' if f['style'] == 'normal' else '500'
        rules.append(
            "@font-face{font-family:'Plus Jakarta Sans';"
            f"font-style:{f['style']};font-weight:{weight};font-display:swap;"
            f"src:url(data:font/woff2;base64,{base64.b64encode(data).decode('ascii')}) format('woff2');"
            f"unicode-range:{f['unicode_range']};}}")
    return '\n'.join(rules)


MONTHS = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')


def provenance_line(model_version: str = MODEL_VERSION,
                    train_seasons: Sequence[int] = TRAIN_SEASONS) -> str:
    """The sidebar footer: one plain line saying what made the page.

    Stage 11. It used to read "Trained on: current nflfastR history / 3
    week(s) saved / Latest: 2026_week3 / Data as of ..." -- a file-name
    week key, a "(s)" plural and a data project's name, which is the build
    talking to itself rather than to a reader. Every part of this line
    comes from config, so it cannot drift from what built the page: the
    model version and the first season the model learns from (the live run
    also learns from the current season's finished games, hence "since").

    Until Stage 13 it also carried "Updated ...". The sidebar is hidden
    below 1080px, so on every phone and tablet the page never said when it
    was built. That half is updated_line(), in the Week Board's header.
    """
    first = min(train_seasons)
    return f"Model {model_version}, built from NFL play-by-play since {first}."


def updated_line(now: datetime) -> str:
    """When the page was built, for the Week Board's header (Stage 13).

    Read from the clock in UTC and labelled so, because a time whose zone
    is not stated is not a time. Carried in a <time> element so the
    instant is machine-readable as well as printed.
    """
    stamp = (f"{MONTHS[now.month - 1]} {now.day}, {now.year}, "
             f"{now.strftime('%H:%M')} UTC")
    iso = now.strftime('%Y-%m-%dT%H:%MZ')
    return f'<time datetime="{iso}">Updated {stamp}.</time>'


def main() -> None:
    print("Loading current ratings...")
    ratings = load_current_ratings()

    print("Loading playoff odds...")
    playoff_odds = load_playoff_odds()

    # Joined into the team rows, not injected separately: playoff odds are a
    # column on Power Ratings now, and the table sorts by reading the value
    # off the team object.
    teams_js = build_teams_js(ratings, playoff_odds)
    # A step of its own rather than a third argument above:
    # tests/test_playoff_odds_column.py reads that call as written.
    teams_js = with_rank_change(teams_js, previous_ranks(ratings, load_latest_live_history()))

    print("Loading all saved predictions...")
    all_preds = load_all_predictions()
    all_graded = load_all_graded()
    all_status = load_game_status()
    all_news = load_team_news()
    all_tv = load_tv()

    weeks_js = {}
    for key, preds in sorted(all_preds.items()):
        season, week = key
        graded = all_graded.get(key, [])
        graded_lookup = {(g['home'], g['away']): g for g in graded}
        weeks_js[f"{season}_week{week}"] = {
            'season': season, 'week': week,
            'games': build_games_js(preds, graded_lookup, all_status.get(key), all_tv.get(key)),
        }
        news = week_news(preds, graded, all_news.get(key))
        if news is not None:
            weeks_js[f"{season}_week{week}"]['news'] = news

    # A preview is a week of its own on the board, flagged so the page labels
    # it and never grades it. No graded lookup, status, TV or news: those are
    # read for locked weeks only. No PDF either (the loop below reads
    # all_preds), since a printed sheet outlives the preview it came from.
    previews = load_previews(locked=set(all_preds) | skipped_weeks())
    for key, preds in sorted(previews.items()):
        season, week = key
        weeks_js[f"{season}_week{week}"] = {
            'season': season, 'week': week, 'preview': True,
            'previewed_utc': preds[0].get('previewed_utc') if preds else None,
            'games': build_games_js(preds, {}),
        }

    shown = set(all_preds) | set(previews)
    latest_key = max(shown) if shown else None
    latest_label = f"{latest_key[0]}_week{latest_key[1]}" if latest_key else None

    # Printable picks PDFs, one per saved week. Generated here rather than
    # client-side because the sheet has to match exactly what the board
    # shows, and browser print output silently varies by browser. Only the
    # weeks that actually produce a file get listed, so the dashboard's
    # download control can hide itself rather than link to a 404.
    print("Generating printable picks PDFs...")
    pdf_weeks = []
    try:
        from src.sports.nfl.generate_picks_pdf import build_picks_rows, render_picks_pdf
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
        print("  NOTE: data/nfl/calibration.json absent -- reliability diagram will "
              "be omitted. Run src/sports/nfl/research/calibration.py to produce it.")
    else:
        print(f"  Backtest calibration loaded "
              f"({calibration_js['models']['model_a']['metrics']['n']} games, "
              f"generated {calibration_js['generated_at']})")

    print("Loading Booth's audit log...")
    agent_log = load_agent_log()

    print("Loading the scheduled jobs' recent runs...")
    recent_runs = load_recent_runs()
    lock_proof = load_lock_proof()

    print("Loading team history...")
    team_history_js = load_team_history()

    foot_html = provenance_line()
    updated_html = updated_line(datetime.now(UTC))

    # The template is kept as parts under src/dashboard/ (Stage 33 item 26)
    # and joined here into the one file it always was.
    template = read_template()
    # The template's comments stay in the template for whoever reads it; the
    # page a visitor downloads does not carry them (Stage 26 item 11,
    # src/sports/nfl/page_comments.py). Stripped before the fills, so no data string is
    # ever put through the lexer.
    template = strip_page_comments(template)

    # Every fill below lands inside a <script> element, so every one goes
    # through safe_json(): a `</script` in any string would end the script
    # (Stage 23). tests/test_safe_json_fills.py finds the placeholders by
    # reading the template's script elements, so a new one is covered.
    html = template.replace('__TEAMS_JSON__', safe_json(teams_js, **COMPACT))
    # Only the run's own metadata: the per-team odds now travel inside
    # teams_js so the Power Ratings table can sort by them.
    html = html.replace('__PLAYOFF_META_JSON__', safe_json(
        {k: (playoff_odds or {}).get(k) for k in
         ('n_simulations', 'games_played', 'games_remaining', 'season')},
        **COMPACT))
    html = html.replace('__WEEKS_JSON__', safe_json(weeks_js, **COMPACT))
    html = html.replace('__LATEST_WEEK__', safe_json(latest_label))
    html = html.replace('__PICKS_PDFS_JSON__', safe_json(pdf_weeks))
    html = html.replace('__ACCURACY_JSON__', safe_json(accuracy_js, **COMPACT))
    html = html.replace('__CALIBRATION_JSON__', safe_json(calibration_js, **COMPACT))
    html = html.replace('__TEAM_HISTORY_JSON__', safe_json(team_history_js, **COMPACT))
    # null, not {}, when the collector has never run. The page distinguishes
    # "no audits recorded yet" from "audits recorded, none of them found
    # anything" -- those are opposite claims about the verifier, and an empty
    # object would let the page make the flattering one by accident.
    html = html.replace('__AGENT_LOG_JSON__', safe_json(agent_log_for_page(agent_log), **COMPACT))
    # null when this build did not read the run history (see load_recent_runs).
    html = html.replace('__RECENT_RUNS_JSON__', safe_json(recent_runs, **COMPACT))
    # null when this build read no lock commits (see load_lock_proof).
    html = html.replace('__LOCK_PROOF_JSON__', safe_json(lock_proof, **COMPACT))
    # The Changelog page is rendered from config.VERSION_HISTORY, so the
    # release notes on the site and the constant the model actually runs under
    # cannot drift apart -- they are the same object.
    html = html.replace('__VERSION_HISTORY_JSON__', safe_json(VERSION_HISTORY, **COMPACT))
    html = html.replace('__MODEL_VERSION__', safe_json(MODEL_VERSION))
    html = html.replace('__SIDEBAR_FOOT__', foot_html)
    html = html.replace('__BOARD_UPDATED__', updated_html)
    html = html.replace('__FONT_FACES__', font_faces_css())
    # Model Lab's rows, from the experiment records (Stage 18, src/sports/nfl/model_lab.py).
    from src.sports.nfl.model_lab import entries as model_lab_entries
    html = html.replace('__MODEL_LAB_ROWS__', render_model_lab_rows(model_lab_entries()))

    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == '__main__':
    main()
