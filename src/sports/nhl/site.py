"""The NHL's pages (Stage 57): one self-contained HTML file, built from the
NHL's own files and nothing of the NFL's but the shared stylesheet.

What it reads, all under the NHL's folders (`src.core.sport.sport_paths`):

- `predictions/nhl/<season>/*.json`: the saved picks, one per game;
- `results/nhl/graded_<season>.json`, `drift_<season>.json`,
  `standings_<season>.json`, `schedule_<season>.json`,
  `ratings_<season>.json`: what the daily run writes;
- `experiments/nhl/stage56/results/confirmation.json`: the backtest's
  answers;
- `data/nhl/drift_baseline.json`: the drift check's registered rule;

and `src/sports/nhl/pages/changes.json`, the What's Changed page's entries.

A missing results file is not an error: the page says what it has not got
yet (the standings before the first run that saves picks, say). A missing
schedule is: the board is built on it.

The template is `src/sports/nhl/pages/` (`page.html`, `body.html`,
`nhl.css`, `nhl.js`); the shared stylesheet is the NFL board's own (`src/dashboard/styles.css`)
until Stage 53 moves it to the shared shell, so the two boards look alike.

Run by hand: python -m src.sports.nhl.site --out site/nhl/index.html
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.core import colour, pick_proof
from src.core.sport import sport_paths
from src.sports.nhl import colours, teams
from src.sports.nhl.schedule import current_season

ROOT = Path(__file__).resolve().parents[3]
PATHS = sport_paths('nhl')
TEMPLATE = Path(__file__).resolve().parent / 'pages'
SHARED_STYLES = ROOT / 'src' / 'dashboard' / 'styles.css'
FONT_DIR = ROOT / 'assets' / 'fonts'

Json = Any


def _read(path: Path) -> Json:
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else None


def _hex(rgb: tuple[float, float, float]) -> str:
    return '#' + ''.join(f'{max(0, min(255, round(c))):02X}' for c in rgb)


def bar_colours(away: str, home: str) -> list[str]:
    """The two colours a game's bar draws, pushed apart when they are close,
    as the NFL board does (`src.core.colour.matchup_push`)."""
    a, h = colours.TEAM_COLOUR.get(away, '#8A93A8'), colours.TEAM_COLOUR.get(home, '#8A93A8')
    pa, ph = colour.matchup_push(a, h)
    return [_hex(pa), _hex(ph)]


def slim_game(g: Json) -> dict[str, Any]:
    return {'id': g['game_id'], 'day': g['slate'], 'start': g['start_utc'], 'home': g['home'], 'away': g['away'],
            'status': g['status'], 'type': g.get('game_type'), 'hs': g.get('home_score'), 'as': g.get('away_score'),
            'lp': g.get('last_period')}


def slim_pick(p: Json, graded: dict[str, str]) -> dict[str, Any]:
    market = p.get('market')
    out: dict[str, Any] = {
        'a': p.get('model_a'), 'b': p.get('model_b'), 'pick': p.get('pick'), 'by': p.get('pick_model'),
        'saved': p.get('saved_utc'), 'result': graded.get(p['game_id'], 'pending'),
        'colours': bar_colours(p['away'], p['home']),
        'goalies': {side: {k: (p.get('goalies') or {}).get(side, {}).get(k) for k in ('name', 'status', 'basis')}
                    for side in ('home', 'away')},
    }
    if market:
        out['market'] = {'book': market.get('book'), 'hp': market.get('home_price'), 'ap': market.get('away_price'),
                         'prob': market.get('home_prob')}
    return out


def payload(season: int, now: datetime) -> dict[str, Any]:
    sched = _read(PATHS.results / f'schedule_{season}.json')
    if sched is None:
        raise FileNotFoundError(f'no schedule for {season}: the daily run writes it (results/nhl/schedule_{season}.json)')
    graded_rows = _read(PATHS.results / f'graded_{season}.json') or []
    graded = {str(r['game_id']): r['result'] for r in graded_rows}
    picks: dict[str, dict[str, Any]] = {}
    folder = PATHS.predictions / str(season)
    for path in sorted(folder.glob('*.json')) if folder.exists() else []:
        p = json.loads(path.read_text(encoding='utf-8'))
        picks[p['game_id']] = slim_pick(p, graded)
    confirmation = _read(PATHS.experiments / 'stage56' / 'results' / 'confirmation.json')
    return {
        'season': season,
        'built_utc': now.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'schedule_as_of': sched.get('as_of'),
        'games': [slim_game(g) for g in sched['games'] if g.get('game_type') in ('regular', 'playoff')],
        'picks': picks,
        # Stage 68 item 20: when each pick file reached the public history.
        'proof': pick_proof.proof(folder) if folder.exists() else {},
        'teams': {abbr: {'name': name, 'logo': colours.LOGO.format(abbr=abbr, theme='dark'),
                         'logo_light': colours.LOGO.format(abbr=abbr, theme='light')}
                  for abbr, name in teams.NAMES.items()},
        'standings': _read(PATHS.results / f'standings_{season}.json'),
        'ratings': _read(PATHS.results / f'ratings_{season}.json'),
        'drift': _read(PATHS.results / f'drift_{season}.json'),
        'drift_rule': _read(PATHS.data / 'drift_baseline.json'),
        'backtest': confirmation,
        'changes': json.loads((TEMPLATE / 'changes.json').read_text(encoding='utf-8')),
    }


def font_faces_css(font_dir: Path = FONT_DIR) -> str:
    """The self-hosted face, as the NFL board inlines it (each file checked
    against assets/fonts/manifest.json first)."""
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


def safe_json(obj: Any) -> str:
    """JSON for a <script> block: nothing in it can close the tag."""
    return (json.dumps(obj, separators=(',', ':'), ensure_ascii=False)
            .replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026'))


def render(data: dict[str, Any]) -> str:
    page = (TEMPLATE / 'page.html').read_text(encoding='utf-8')
    html = (page.replace('{% include "styles.css" %}', SHARED_STYLES.read_text(encoding='utf-8'))
                .replace('{% include "nhl.css" %}', (TEMPLATE / 'nhl.css').read_text(encoding='utf-8'))
                .replace('{% include "body.html" %}', (TEMPLATE / 'body.html').read_text(encoding='utf-8'))
                .replace('{% include "nhl.js" %}', (TEMPLATE / 'nhl.js').read_text(encoding='utf-8')))
    html = html.replace('__FONT_FACES__', font_faces_css())
    html = html.replace('__NHL_JSON__', safe_json(data))
    left = sorted({t for t in ('__FONT_FACES__', '__NHL_JSON__', '{% include') if t in html})
    if left:
        raise ValueError(f'unfilled placeholders: {left}')
    return html


def main(argv: list[str] | None = None, now: datetime | None = None) -> int:
    ap = argparse.ArgumentParser(description='Build the NHL pages')
    ap.add_argument('--out', default='site/nhl/index.html')
    ap.add_argument('--season', type=int, default=None)
    args = ap.parse_args(argv)
    now = now or datetime.now(UTC)
    season = args.season if args.season is not None else current_season(now)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(payload(season, now)), encoding='utf-8')
    print(f'wrote {out} ({out.stat().st_size} bytes)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
