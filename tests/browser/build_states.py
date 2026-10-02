"""
Build the dashboard in the states no real week is in yet (Stage 34 item 30).

The browser checks run on the page the real data builds. That page only
shows the states real weeks are in, so a card or note that appears only in
a rarer state has never been laid out, tabbed through or run through axe in
CI: a tied game, a week recorded as skipped, a preview whose kickoff has
passed with no lock. Each has code on the page (Stage 30 items 1 and 3,
Stage 24) and none has happened this season.

This builds the real generator over a synthetic copy of the saved weeks, in
a temporary folder, and writes one page per state. Everything else the page
reads (ratings, odds, calibration, team history, news, TV) is the real data.
The saved weeks are copied from the repository, which keeps them for good,
so the pages are the same on every run:

  states_tie.html      the latest GRADED week, with its first game a tie:
                       graded as grade_predictions grades one, and final
                       at 20-20 in the weekend refresh's snapshot. Weeks
                       locked after it are left out, so it is the week the
                       board opens on, and exactly one card reads "Tie".
  states_preview.html  after the locked weeks, a week recorded as skipped,
                       with the preview its Tuesday run left (which the page
                       must not show), then a preview whose games all kicked
                       off without a lock (which the page must show, saying
                       the lock run did not happen).

Each page is checked here for the state it was built for before it is
written, so a builder that stopped producing its state fails rather than
handing the browser checks a page with nothing new in it.

Usage: python tests/browser/build_states.py --out <folder>
Then:  python tests/browser/check_page.py <folder>/states_tie.html ...
"""
import argparse
import copy
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# Run as a script (browser-checks.yml, tasks.py), so the root is not on the
# path the way it is under pytest or `python -m`.
sys.path.insert(0, str(ROOT))

from src.pipeline import generate_dashboard as gd  # noqa: E402
from src.pipeline.paths import PRED_DIR, RESULTS_DIR, STATUS_DIR, parse_week  # noqa: E402

PAGES = ('states_tie.html', 'states_preview.html')


class StateMissing(Exception):
    """A built page does not hold the state it was built for."""
TIE_SCORE = 20
# The kickoffs of the preview that never locked. Fixed and in the past, so
# the page is past kickoff on every run without reading a clock here.
STALE_KICKOFFS = [('2026-09-24', '20:15', 'Thursday'), ('2026-09-27', '13:00', 'Sunday'),
                  ('2026-09-27', '16:25', 'Sunday'), ('2026-09-28', '20:15', 'Monday')]


def saved_weeks():
    """{(season, week): (picks, graded or None, status or None)} for every
    locked week in the repository."""
    out = {}
    for f in sorted(PRED_DIR.glob('*_week*.json')):
        key = parse_week(f.stem)
        if key is None:
            continue
        graded = RESULTS_DIR / f'{f.stem}_graded.json'
        status = STATUS_DIR / f'{f.stem}.json'
        out[key] = (json.loads(f.read_text(encoding='utf-8')),
                    json.loads(graded.read_text(encoding='utf-8')) if graded.exists() else None,
                    json.loads(status.read_text(encoding='utf-8')) if status.exists() else None)
    return out


def with_a_tie(graded, status, season, week):
    """The week's graded picks and snapshot with the first game tied: the
    grade exactly as grade_predictions writes one, the snapshot final and
    level."""
    graded, status = copy.deepcopy(graded), copy.deepcopy(status)
    first = graded[0]
    first['result'] = 'tie'
    first['actual_home_win'] = None
    first['market_correct'] = first['model_a_correct'] = first['model_b_correct'] = None
    status = status or {'season': season, 'week': week, 'games': []}
    status['games'] = [g for g in status['games']
                       if (g['home'], g['away']) != (first['home'], first['away'])]
    status['games'].append({'away': first['away'], 'home': first['home'], 'status': 'final',
                            'away_score': TIE_SCORE, 'home_score': TIE_SCORE,
                            'spread_line': first.get('spread_line')})
    return graded, status, (first['home'], first['away'])


def as_preview(picks, season, week, kickoffs=None):
    """A week's picks re-dated as a preview for another week."""
    out = []
    for i, p in enumerate(copy.deepcopy(picks)):
        p.update(season=season, week=week, preview=True,
                 previewed_utc='2026-09-22T12:00:00Z')
        if kickoffs:
            p['gameday'], p['gametime_et'], p['weekday'] = kickoffs[i % len(kickoffs)]
        for k in ('actual_home_win', 'market_correct', 'model_a_correct', 'model_b_correct', 'result'):
            p.pop(k, None)
        out.append(p)
    return out


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj), encoding='utf-8')


def tie_week(weeks):
    """The week the tie goes in: the latest week with a graded file.

    Until Stage 35 it was the latest LOCKED week, graded or not, and from each
    Thursday lock to the Tuesday grading that week has no graded file. The
    builder then graded the raw picks, every one of the 16 cards came out
    graded with no verdict, and every one read "Tie" -- a page no real week
    can produce, while the JSON check here counted the one tie it had written
    and passed. The third audit reproduced it: 16 of 16 without the graded
    file, 1 of 16 with it."""
    graded = [k for k, (_, g, _) in weeks.items() if g]
    if not graded:
        raise StateMissing('no saved week is graded yet, so there is no real grade to put a tie in')
    return max(graded)


def lay_out(work, weeks, state):
    """Write the saved weeks, and the state's own files, under `work`.
    Returns what the state must show: for 'tie' the tied game, for
    'preview' the skipped week and the stale preview's week.

    The tie state stops at the week holding the tie: later weeks, locked but
    not graded yet, are left out, so the tie week is the latest week and the
    one the board opens on, as it is on a real Tuesday after grading."""
    pred, results, status = work / 'predictions', work / 'results', work / 'game_status'
    for d in (pred, results, status):
        d.mkdir(parents=True, exist_ok=True)
    if state == 'tie':
        tied_week = tie_week(weeks)
        weeks = {k: v for k, v in weeks.items() if k <= tied_week}
    latest = max(weeks)
    for (season, week), (picks, graded, snap) in weeks.items():
        stem = f'{season}_week{week}'
        write(pred / f'{stem}.json', picks)
        if state == 'tie' and (season, week) == tied_week:
            graded, snap, tied = with_a_tie(graded, snap, season, week)
        if graded is not None:
            write(results / f'{stem}_graded.json', graded)
        if snap is not None:
            write(status / f'{stem}.json', snap)
    season, week = latest
    if state == 'tie':
        return tied
    skipped, stale = (season, week + 1), (season, week + 2)
    picks = weeks[latest][0]
    write(pred / 'skipped' / f'{season}_week{skipped[1]}.json',
          {'season': season, 'week': skipped[1], 'recorded_utc': '2026-09-28T11:00:00Z'})
    write(pred / 'preview' / f'{season}_week{skipped[1]}.json', as_preview(picks, season, skipped[1]))
    write(pred / 'preview' / f'{season}_week{stale[1]}.json',
          as_preview(picks, season, stale[1], STALE_KICKOFFS))
    return skipped, stale


def weeks_json(html):
    """The page's weeks, read back out of the built file."""
    m = re.search(r'\bconst weeks = ', html)
    if not m:
        raise StateMissing('the built page has no weeks object -- re-anchor this')
    return json.JSONDecoder().raw_decode(html, m.end())[0]


def rendered_tie_tags(html):
    """How many cards on the built page the page's own gradedTagHtml tags
    "Tie", over every week the page holds. Run in node from the built file,
    not the template, so it measures what ships. The script goes in on stdin:
    the page's weeks are far past Windows' command-line limit."""
    node = shutil.which('node')
    if not node:
        raise StateMissing('node is needed to render the graded tags, and it is not on PATH')
    m = re.search(r'function gradedTagHtml\(.*?\n\}\n', html, re.S)
    if not m:
        raise StateMissing('the built page has no gradedTagHtml -- re-anchor this')
    js = (m.group(0) + f'const W={json.dumps(weeks_json(html))};let n=0;'
          'for(const k in W)for(const g of W[k].games)'
          'if(gradedTagHtml(g).includes(\'class="graded-tag tie"\'))n++;'
          'process.stdout.write(String(n));')
    r = subprocess.run([node, '-'], input=js, capture_output=True, text=True, encoding='utf-8')
    if r.returncode != 0:
        raise StateMissing(f'gradedTagHtml threw: {r.stderr[-400:]}')
    return int(r.stdout)


def check(state, html, expect):
    weeks = weeks_json(html)
    if state == 'tie':
        home, away = expect
        games = [g for w in weeks.values() for g in w['games']
                 if (g['home'], g['away']) == (home, away) and g.get('result') == 'tie']
        if not games:
            raise StateMissing('the tie page has no tied game in it')
        tags = rendered_tie_tags(html)
        if tags != 1:
            raise StateMissing(f'the tie page renders {tags} "Tie" tags; a real week with one tie renders one')
    else:
        skipped, stale = expect
        labels = {f'{s}_week{w}' for s, w in (skipped, stale)}
        shown = labels & set(weeks)
        if shown != {f'{stale[0]}_week{stale[1]}'}:
            raise StateMissing(f'the preview page shows {sorted(shown)}; '
                             f'it must show only the stale preview, never the skipped week')
        if not weeks[f'{stale[0]}_week{stale[1]}'].get('preview'):
            raise StateMissing('the stale preview is not marked a preview')


def build(out, state, weeks):
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        expect = lay_out(work, weeks, state)
        saved = {k: getattr(gd, k) for k in ('PRED_DIR', 'RESULTS_DIR', 'OUTPUT_PATH',
                                             'DIST_DIR', 'load_game_status')}
        real_status = gd.load_game_status
        page = out / f'states_{state}.html'
        try:
            gd.PRED_DIR, gd.RESULTS_DIR = work / 'predictions', work / 'results'
            gd.OUTPUT_PATH, gd.DIST_DIR = page, work / 'dist'
            gd.load_game_status = lambda: real_status(work / 'game_status')
            gd.main()
        finally:
            for k, v in saved.items():
                setattr(gd, k, v)
    check(state, page.read_text(encoding='utf-8'), expect)
    return page


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    weeks = saved_weeks()
    if not weeks:
        raise SystemExit('build_states: no saved weeks to build from')
    for state in ('tie', 'preview'):
        print(f'build_states: wrote {build(out, state, weeks)}')


if __name__ == '__main__':
    try:
        main()
    except StateMissing as e:
        raise SystemExit(f'build_states: {e}')
