"""The NBA's pages (Stage 61): the registered backtest, said plainly, and no
live picks (Mark's call pending, built on Claude's recommendation of
2026-10-06: option A of "NBA Board Options").

Why there is no board: the backtest answered H3 with REJECT (Model B
forecasts worse than the market alone), and no GitHub runner can read a
pre-game NBA price or injury report (`docs/nba-data.md`). The section says
so, shows the questions and their answers, how the models work, and how
the result was checked.

What it reads, all under the NBA's folders (`src.core.sport.sport_paths`):

- `experiments/nba/stage61/registry.json`: the seasons and the level;
- `experiments/nba/stage61/results/confirmation.json` and `tuning.json`:
  the backtest's answers and its validation grid;
- `data/nba/history/games_<season>.csv` and `market_<season>.csv`: how
  many games each season holds and how many have a price.

Missing results stop the build: without them the page has nothing true to
say. The template is `src/sports/nba/pages/`; the shared stylesheet is the
NFL board's own (`src/dashboard/styles.css`) until Stage 53 moves it to the
shared shell, as the NHL's pages do.

Run by hand: python -m src.sports.nba.site --out site/nba/index.html
"""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.core.sport import sport_paths

ROOT = Path(__file__).resolve().parents[3]
PATHS = sport_paths('nba')
TEMPLATE = Path(__file__).resolve().parent / 'pages'
SHARED_STYLES = ROOT / 'src' / 'dashboard' / 'styles.css'
FONT_DIR = ROOT / 'assets' / 'fonts'

Json = Any


def _read(path: Path) -> Json:
    if not path.exists():
        raise FileNotFoundError(f'{path}: the NBA page is built from it (python -m src.sports.nba.backtest writes it)')
    return json.loads(path.read_text(encoding='utf-8'))


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def coverage(first: int, last: int) -> list[dict[str, int]]:
    """Per season: the games the history holds, how many have a price, and
    how many of those are a closing price."""
    folder = PATHS.data / 'history'
    out = []
    for season in range(first, last + 1):
        games = {r['game_id'] for r in _rows(folder / f'games_{season}.csv')}
        market = [r for r in _rows(folder / f'market_{season}.csv') if r['game_id'] in games]
        out.append({'season': season, 'games': len(games), 'priced': len({r['game_id'] for r in market}),
                    'closing': len({r['game_id'] for r in market if r['closing'] == 'True'})})
    return out


def payload(now: datetime) -> dict[str, Any]:
    folder = PATHS.experiments / 'stage61'
    reg = _read(folder / 'registry.json')
    p = reg['protocol']
    return {
        'built_utc': now.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'protocol': {k: p[k] for k in ('training_from_season', 'validation_seasons', 'confirmation_seasons',
                                       'forward_holdout_season', 'alpha', 'budget_m')},
        'registered': reg['registered'],
        'backtest': _read(folder / 'results' / 'confirmation.json'),
        'tuning': _read(folder / 'results' / 'tuning.json'),
        'coverage': coverage(p['training_from_season'], p['confirmation_seasons'][-1]),
    }


def font_faces_css(font_dir: Path = FONT_DIR) -> str:
    """The self-hosted face, as the NFL board and the NHL's pages inline it
    (each file checked against assets/fonts/manifest.json first). A copy of
    the NHL's until Stage 53's shared shell holds one for every sport."""
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
                .replace('{% include "nba.css" %}', (TEMPLATE / 'nba.css').read_text(encoding='utf-8'))
                .replace('{% include "body.html" %}', (TEMPLATE / 'body.html').read_text(encoding='utf-8'))
                .replace('{% include "nba.js" %}', (TEMPLATE / 'nba.js').read_text(encoding='utf-8')))
    html = html.replace('__FONT_FACES__', font_faces_css())
    html = html.replace('__NBA_JSON__', safe_json(data))
    left = sorted({t for t in ('__FONT_FACES__', '__NBA_JSON__', '{% include') if t in html})
    if left:
        raise ValueError(f'unfilled placeholders: {left}')
    return html


def main(argv: list[str] | None = None, now: datetime | None = None) -> int:
    ap = argparse.ArgumentParser(description='Build the NBA pages')
    ap.add_argument('--out', default='site/nba/index.html')
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(payload(now or datetime.now(UTC))), encoding='utf-8')
    print(f'wrote {out} ({out.stat().st_size} bytes)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
