"""The NBA's pages: the day board (Stage 65) and the registered backtest
(Stage 61), said plainly.

Mark said GO for live NBA picks on 2026-10-09: a runner reads ESPN's price
and injury report (#357), so the forward test registered in
`experiments/nba/stage65/registry.json` runs from opening night. The board
is the NHL's day board (Stages 63 and 64): a strip of the week's days,
compact rows, a tap to the full card. Where the NHL's card names the
goalies, the NBA's says who was listed Out and the availability each side
was given; where a game had no price, it says "no price" and why.

What it reads, all under the NBA's folders (`src.core.sport.sport_paths`):

- `predictions/nba/<season>/*.json`: the saved picks, one per game;
- `results/nba/schedule_<season>.json`, `graded_<season>.json` and
  `drift_<season>.json`: what the daily run writes. Absent before its
  first run, which the board says rather than failing the build;
- `experiments/nba/stage65/registry.json`: the forward test's rules;
- `experiments/nba/stage61/registry.json`: the seasons and the level;
- `experiments/nba/stage61/results/confirmation.json` and `tuning.json`:
  the backtest's answers and its validation grid;
- `data/nba/history/games_<season>.csv` and `market_<season>.csv`: how
  many games each season holds and how many have a price.

Missing backtest results stop the build: without them those pages have
nothing true to say. The template is `src/sports/nba/pages/`; the shared stylesheet is the
NFL board's own (`src/dashboard/styles.css`) until Stage 53 moves it to the
shared shell, as the NHL's pages do.

Run by hand: python -m src.sports.nba.site --out site/nba/index.html
"""
from __future__ import annotations

import argparse
import csv
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.core import colour, pick_proof
from src.core.page_comments import strip_page_comments
from src.core.page_fill import ESCAPE_JS, ROUTES_JS, font_faces_css, safe_json
from src.core.sport import sport_paths
from src.sports.nba import colours, teams
from src.sports.nba.schedule import current_season

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


def _maybe(path: Path) -> Json:
    """A file the daily run writes: absent until its first run, which the
    board says rather than failing the build."""
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else None


def _hex(rgb: tuple[float, float, float]) -> str:
    return '#' + ''.join(f'{max(0, min(255, round(c))):02X}' for c in rgb)


def bar_colours(away: str, home: str) -> list[str]:
    """The two colours a game's bar draws, pushed apart when they are close,
    as the NFL and NHL boards do (`src.core.colour.matchup_push`)."""
    a, h = colours.TEAM_COLOUR.get(away, '#8A93A8'), colours.TEAM_COLOUR.get(home, '#8A93A8')
    pa, ph = colour.matchup_push(a, h)
    return [_hex(pa), _hex(ph)]


def slim_game(g: Json) -> dict[str, Any]:
    return {'id': g['game_id'], 'day': g['slate'], 'start': g['start_utc'], 'home': g['home'], 'away': g['away'],
            'status': g['status'], 'type': g.get('game_type'), 'hs': g.get('home_score'), 'as': g.get('away_score')}


def slim_pick(p: Json, graded: dict[str, str]) -> dict[str, Any]:
    """What the board shows of a saved pick: both models, the price and its
    source (or why there was none), the availability each side was given,
    and who was listed Out."""
    m = p.get('market') or {}
    avail = p.get('availability') or {}
    inj = p.get('injuries') or {}
    out: dict[str, Any] = {
        'a': p.get('model_a'), 'b': p.get('model_b'), 'pick': p.get('pick'), 'by': p.get('pick_model'),
        'saved': p.get('saved_utc'), 'result': graded.get(p['game_id'], 'pending'),
        'colours': bar_colours(p['away'], p['home']),
        'source': p.get('market_source'),
        'avail': {'read': bool(avail.get('read')), 'home': avail.get('home'), 'away': avail.get('away')},
        'out': {side: [x['name'] for x in inj.get(side) or [] if x.get('status') == 'Out'] for side in ('home', 'away')},
    }
    if p.get('market_source'):
        out['market'] = {'book': m.get('provider'), 'hp': m.get('home_price'), 'ap': m.get('away_price'),
                         'prob': m.get('home_prob')}
    else:
        out['why'] = m.get('why')
    return out


def board(season: int) -> dict[str, Any]:
    """The live board's inputs: the season's games, the saved picks with
    their grades, the drift check, and the clubs' names and logos."""
    sched = _maybe(PATHS.results / f'schedule_{season}.json')
    graded = {str(r['game_id']): r['result'] for r in _maybe(PATHS.results / f'graded_{season}.json') or []}
    picks: dict[str, dict[str, Any]] = {}
    folder = PATHS.predictions / str(season)
    for path in sorted(folder.glob('*.json')) if folder.exists() else []:
        p = json.loads(path.read_text(encoding='utf-8'))
        picks[p['game_id']] = slim_pick(p, graded)
    return {
        'season': season,
        'schedule_as_of': (sched or {}).get('as_of'),
        'games': [slim_game(g) for g in (sched or {}).get('games', [])],
        'picks': picks,
        # Stage 68 item 20: when each pick file reached the public history.
        'proof': pick_proof.proof(folder) if folder.exists() else {},
        'teams': {abbr: {'name': name, 'logo': colours.logo(abbr, 'dark'), 'logo_light': colours.logo(abbr, 'light')}
                  for abbr, name in teams.NAMES.items()},
        'drift': _maybe(PATHS.results / f'drift_{season}.json'),
        'live': _read(PATHS.experiments / 'stage65' / 'registry.json')['forward_test'],
    }


def payload(now: datetime) -> dict[str, Any]:
    folder = PATHS.experiments / 'stage61'
    reg = _read(folder / 'registry.json')
    p = reg['protocol']
    return {
        'built_utc': now.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'board': board(current_season(now)),
        'protocol': {k: p[k] for k in ('training_from_season', 'validation_seasons', 'confirmation_seasons',
                                       'forward_holdout_season', 'alpha', 'budget_m')},
        'registered': reg['registered'],
        'backtest': _read(folder / 'results' / 'confirmation.json'),
        'tuning': _read(folder / 'results' / 'tuning.json'),
        'coverage': coverage(p['training_from_season'], p['confirmation_seasons'][-1]),
    }






def render(data: dict[str, Any]) -> str:
    page = (TEMPLATE / 'page.html').read_text(encoding='utf-8')
    html = (page.replace('{% include "styles.css" %}', SHARED_STYLES.read_text(encoding='utf-8'))
                .replace('{% include "nba.css" %}', (TEMPLATE / 'nba.css').read_text(encoding='utf-8'))
                .replace('{% include "escape.js" %}', ESCAPE_JS.read_text(encoding='utf-8'))
                .replace('{% include "routes.js" %}', ROUTES_JS.read_text(encoding='utf-8'))
                .replace('{% include "body.html" %}', (TEMPLATE / 'body.html').read_text(encoding='utf-8'))
                .replace('{% include "nba.js" %}', (TEMPLATE / 'nba.js').read_text(encoding='utf-8')))
    # Comments stay in the templates for whoever reads them; the page a
    # visitor downloads does not carry them (src/core/page_comments.py,
    # Stage 68 item 19). Stripped before the fills, so no data is lexed.
    html = strip_page_comments(html)
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
