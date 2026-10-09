"""The site's home page (Stage 59; Mark chose option A of the rendered
"Pick'em Home Options" on 2026-10-05): one card per sport with where that
sport stands now, its season record, and a link to its board.

What the build reads, each sport from its own folders only:

- NFL: the saved weeks (`predictions/nfl/<season>_week<N>.json`) for the
  latest locked week and its kickoffs, any preview of the next week
  (`predictions/nfl/preview/`), and the graded weeks for Model B's record;
- NHL: the season's schedule and graded picks (`results/nhl/`);
- NBA: nothing. It has no live picks this season (Mark, 2026-10-06), and
  its card says so.

The page carries those facts as data and works out the status in the
visitor's browser, against the visitor's clock: "9 games tonight" is about
tonight where the visitor is, and a page built at 14:00 UTC is not stale
by the evening. A sport whose files are missing says it has not been built
yet rather than leaving its card out.

Anyone arriving at the root with a shared-picks link (`#picks=...`) is sent
on to the NFL board, which is where every such link was made.
"""
from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = Path(__file__).resolve().parent / 'home'
SHARED_STYLES = ROOT / 'src' / 'dashboard' / 'styles.css'

Json = Any


def _read(path: Path) -> Json:
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else None


def _week_files(folder: Path) -> dict[tuple[int, int], Path]:
    out = {}
    for p in folder.glob('*_week*.json') if folder.is_dir() else []:
        m = re.fullmatch(r'(\d{4})_week(\d+)', p.stem)
        if m:
            out[(int(m.group(1)), int(m.group(2)))] = p
    return out


def nfl_kickoff(game: Json) -> str | None:
    """A saved NFL pick's kickoff in UTC: its date and Eastern time, localised
    the way the weekly run's kickoff_utc does it (EDT or EST by the date).
    pandas, not zoneinfo: Windows ships no time-zone database for zoneinfo."""
    day, clock = game.get('gameday'), game.get('gametime_et')
    if not day or not clock:
        return None
    local = pd.Timestamp(f'{day} {clock}').tz_localize('America/New_York')
    return local.tz_convert('UTC').strftime('%Y-%m-%dT%H:%M:%SZ')


def nfl_facts(root: Path = ROOT) -> dict[str, Any]:
    weeks = _week_files(root / 'predictions' / 'nfl')
    if not weeks:
        return {'built': False}
    season, week = max(weeks)
    games = json.loads(weeks[(season, week)].read_text(encoding='utf-8'))
    previews = [k for k in _week_files(root / 'predictions' / 'nfl' / 'preview') if k > (season, week)]
    won = lost = 0
    for (s, _w), _p in weeks.items():
        if s != season:
            continue
        for row in _read(root / 'results' / 'nfl' / f'{s}_week{_w}_graded.json') or []:
            if row.get('model_b_correct') in (1, True):
                won += 1
            elif row.get('model_b_correct') in (0, False):
                lost += 1
    return {'built': True, 'season': season, 'week': week,
            'kickoffs': sorted(k for k in (nfl_kickoff(g) for g in games) if k),
            'preview_week': max(previews)[1] if previews else None,
            'record': {'label': 'Model B this season', 'won': won, 'lost': lost}}


def nhl_facts(root: Path = ROOT, now: datetime | None = None) -> dict[str, Any]:
    """The NHL's games from two days before the build to two weeks after,
    as [start UTC, status], so the visitor's browser can count tonight's."""
    results = root / 'results' / 'nhl'
    seasons = sorted(int(m.group(1)) for p in results.glob('schedule_*.json')
                     if (m := re.fullmatch(r'schedule_(\d{4})', p.stem))) if results.is_dir() else []
    if not seasons:
        return {'built': False}
    season = seasons[-1]
    sched = _read(results / f'schedule_{season}.json') or {}
    graded = _read(results / f'graded_{season}.json') or []
    now = now or datetime.now(UTC)
    lo, hi = (now - timedelta(days=2)).strftime('%Y-%m-%dT%H:%M:%SZ'), (now + timedelta(days=14)).strftime('%Y-%m-%dT%H:%M:%SZ')
    games = sorted([g['start_utc'], g.get('status')] for g in sched.get('games', [])
                   if g.get('game_type') in ('regular', 'playoff') and g.get('start_utc')
                   and lo <= g['start_utc'] <= hi and g.get('status') not in ('cancelled', 'postponed'))
    return {'built': True, 'season': season, 'games': games,
            'record': {'label': 'Picks this season',
                       'won': sum(1 for r in graded if r.get('result') == 'correct'),
                       'lost': sum(1 for r in graded if r.get('result') == 'wrong')}}


def facts(root: Path = ROOT, now: datetime | None = None) -> dict[str, Any]:
    return {'nfl': nfl_facts(root), 'nhl': nhl_facts(root, now), 'nba': {'built': True, 'live': False}}


def safe_json(obj: Any) -> str:
    """JSON for a <script> block: nothing in it can close the tag."""
    return (json.dumps(obj, separators=(',', ':'), ensure_ascii=False)
            .replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026'))


def render(data: dict[str, Any], font_faces: str = '') -> str:
    page = (TEMPLATE / 'page.html').read_text(encoding='utf-8')
    html = (page.replace('{% include "styles.css" %}', SHARED_STYLES.read_text(encoding='utf-8'))
                .replace('{% include "home.css" %}', (TEMPLATE / 'home.css').read_text(encoding='utf-8'))
                .replace('{% include "home.js" %}', (TEMPLATE / 'home.js').read_text(encoding='utf-8')))
    html = html.replace('__FONT_FACES__', font_faces).replace('__HOME_JSON__', safe_json(data))
    left = sorted(set(re.findall(r'__[A-Z0-9_]+__', html)) | ({'{% include'} if '{% include' in html else set()))
    if left:
        raise ValueError(f'unfilled placeholders: {left}')
    return html


def font_faces_css(font_dir: Path = ROOT / 'assets' / 'fonts') -> str:
    """The self-hosted face, inlined as every sport's page inlines it."""
    import base64
    import hashlib
    manifest = json.loads((font_dir / 'manifest.json').read_text(encoding='utf-8'))
    rules = []
    for f in manifest['files']:
        data = (font_dir / f['file']).read_bytes()
        if hashlib.sha256(data).hexdigest() != f['sha256']:
            raise ValueError(f"{f['file']}: sha256 does not match the manifest")
        weight = '400 800' if f['style'] == 'normal' else '500'
        rules.append("@font-face{font-family:'Plus Jakarta Sans';"
                     f"font-style:{f['style']};font-weight:{weight};font-display:swap;"
                     f"src:url(data:font/woff2;base64,{base64.b64encode(data).decode('ascii')}) format('woff2');"
                     f"unicode-range:{f['unicode_range']};}}")
    return '\n'.join(rules)


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Build the site's home page")
    ap.add_argument('--out', default='_site/index.html')
    ap.add_argument('--unpublished', default='',
                    help="comma-separated sports with no page in this build; their cards say so and link nowhere")
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    data = facts()
    for code in filter(None, args.unpublished.split(',')):
        data[code] = {'built': False}
    out.write_text(render(data, font_faces_css()), encoding='utf-8')
    print(f'wrote {out} ({out.stat().st_size} bytes)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
