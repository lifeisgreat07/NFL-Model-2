"""MLB's pages: the day board (Stage 100 item 1), built and tested but not yet published.

Mark chose layout A on 2026-11-22: the NHL's and NBA's day board (a strip of the week's days, compact rows, a tap
to the full card) with what baseball adds: each club's starting pitcher where the NHL names the goalies, the
game's place in its series ("Game 2 of 4 · DET leads 1-0") and a doubleheader's game number. The other pages
(Power Ratings, Season Accuracy, Model Lab, Methodology, Teams, What's Changed, Checking the AI's work) are Stage
100 item 2; the standings odds item 3. The site build does not list MLB in its SPORTS until Stage 101 makes it
live, so nothing here reaches the public site yet.

The board shows no picks yet, on purpose: MLB's pick file and the daily run that writes it are Stage 101, and
the pick's shape is fixed there with its writer, not guessed here. Until then every row is a scheduled game.

What it reads, all under MLB's folders (`src.core.sport.sport_paths`):

- `results/mlb/schedule_<season>.json`: what the daily run will write (Stage 101 item 2), `{"as_of", "games"}`
  with each game in the core's schedule shape as `src/sports/mlb/schedule.py` makes it (clubs as Stats API ids,
  as text), plus `game_number`, `double_header`, `series_game`, `series_games`, and, once a club has named one,
  `home_starter` / `away_starter` as `{"id", "name"}`, and `start_time_tbd`. Absent before the first run, which the board says
  rather than failing the build. Present with no games, it stops the build, as the NBA's does.

Run by hand: python -m src.sports.mlb.site --out site/mlb/index.html
"""
from __future__ import annotations

import argparse
import csv
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.core import page_render
from src.core.page_fill import (
    DAY_BOARD_JS,
    ESCAPE_JS,
    FAVS_JS,
    PREFS_JS,
    ROUTES_JS,
    font_faces_css,
    safe_json,
)
from src.core.sport import sport_paths
from src.sports.mlb import backtest, colours, history, teams
from src.sports.mlb.schedule import current_season

ROOT = Path(__file__).resolve().parents[3]
PATHS = sport_paths('mlb')
TEMPLATE = Path(__file__).resolve().parent / 'pages'
SHARED_STYLES = ROOT / 'src' / 'dashboard' / 'styles.css'

Json = Any
#: The Stats API's doubleHeader flag: 'Y' a doubleheader for one ticket, 'S' a split (two tickets), 'N' none.
DOUBLEHEADER = frozenset({'Y', 'S'})


def _maybe(path: Path) -> Json:
    """A file the daily run writes: absent until its first run, which the board says rather than failing the build."""
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else None


def abbr(club: Any) -> str:
    """A Stats API club id as the board names it; '?' for one this file does not know, never markup."""
    return teams.NAMES[str(club)][0] if str(club) in teams.NAMES else '?'


def _whole(x: Any) -> int | None:
    return x if type(x) is int else None


def series_line(game: Json, games: list[Json]) -> dict[str, int] | None:
    """The game's place in its series and the series so far: {'game', 'of', 'home_won', 'away_won'}, counting
    the series' earlier games that are final with a winner. None when the schedule gives no place (src/sports/
    mlb/schedule.py leaves a place that makes no sense empty).

    A series is the run of games with the same home club, away club and length, numbered 1 to N, each earlier
    than this one, in the week before it: a club that plays the same opponent at home twice in a season is two
    series, kept apart by that week."""
    n, of = _whole(game.get('series_game')), _whole(game.get('series_games'))
    if n is None or of is None or not 1 <= n <= of:
        return None
    start = str(game.get('start_utc') or '')
    week_before = _shift(start, -7)
    home_won = away_won = 0
    for g in games:
        if (g is game or str(g.get('home')) != str(game.get('home')) or str(g.get('away')) != str(game.get('away'))
                or _whole(g.get('series_games')) != of):
            continue
        k = _whole(g.get('series_game'))
        if k is None or not k < n or not week_before <= str(g.get('start_utc') or '') < start:
            continue
        if g.get('status') == 'final' and g.get('home_win') in (0, 1):
            home_won += g['home_win']
            away_won += 1 - g['home_win']
    return {'game': n, 'of': of, 'home_won': home_won, 'away_won': away_won}


def _shift(iso: str, days: int) -> str:
    """An ISO UTC start moved by whole days, in the same 'YYYY-MM-DDTHH:MM:SSZ' form, so strings compare in order."""
    if not iso:
        return ''
    t = datetime.fromisoformat(iso.replace('Z', '+00:00'))
    return (t.fromtimestamp(t.timestamp() + days * 86400, UTC)).strftime('%Y-%m-%dT%H:%M:%SZ')


def starter(s: Json) -> str | None:
    return str(s['name']) if isinstance(s, dict) and s.get('name') else None


def slim_game(g: Json, games: list[Json]) -> dict[str, Any]:
    number = _whole(g.get('game_number'))
    return {'id': str(g['game_id']), 'day': g['slate'], 'start': g.get('start_utc'),
            'home': abbr(g['home']), 'away': abbr(g['away']), 'status': g['status'], 'type': g.get('game_type'),
            'hs': g.get('home_score'), 'as': g.get('away_score'),
            'dh': number if g.get('double_header') in DOUBLEHEADER and number in (1, 2) else 0,
            # A start the league has not set: 'after' for game 2 of a one-ticket doubleheader (it starts when
            # game 1 ends), 'tbd' otherwise; the start_utc beside it is a placeholder (src/sports/mlb/schedule.py).
            'time': ('after' if g.get('double_header') == 'Y' and number == 2 else 'tbd') if g.get('start_time_tbd') is True else 'set',
            'series': series_line(g, games),
            'hsp': starter(g.get('home_starter')), 'asp': starter(g.get('away_starter'))}


def standings_file(season: int) -> Json:
    """The standings odds MLB's daily run will write (`src/sports/mlb/standings.py` to_json; Stage 101 writes it),
    each club by its code; None before the first."""
    doc = _maybe(PATHS.results / f'standings_{season}.json')
    if doc is None:
        return None
    return {**doc, 'teams': [{**t, 'team': abbr(t['team'])} for t in doc['teams']]}


def ratings_file(season: int) -> Json:
    """The Power Ratings page's file (`src/sports/mlb/page_inputs.py` ratings_json; MLB's daily run writes it in
    Stage 101), every club by its code; None before the first. A starter the Stats API named no one keeps a blank
    name, which the page shows as his id."""
    doc = _maybe(PATHS.results / f'ratings_{season}.json')
    if doc is None:
        return None
    return {**doc, 'clubs': [{**c, 'team': abbr(c['team'])} for c in doc['clubs']],
            'starters': [{**s, 'club': abbr(s['club'])} for s in doc['starters']]}


def board(season: int) -> dict[str, Any]:
    """The board's inputs: the season's games, each with its series line, and the clubs' names and logos."""
    sched = _maybe(PATHS.results / f'schedule_{season}.json')
    if sched is not None and not sched.get('games'):
        raise ValueError(f'results/mlb/schedule_{season}.json has no games; refusing to build a board from it')
    games = (sched or {}).get('games', [])
    return {
        'season': season,
        'schedule_as_of': (sched or {}).get('as_of'),
        'games': [slim_game(g, games) for g in games],
        # Stage 101 defines MLB's pick file with its writer; until then no game has a pick.
        'picks': {},
        'standings': standings_file(season),
        'ratings': ratings_file(season),
        'teams': {code: {'name': name, 'logo': colours.LOGO['dark'].format(code=colours.LOGO_CODE[club]),
                         'logo_light': colours.LOGO['light'].format(code=colours.LOGO_CODE[club])}
                  for club, (code, name) in teams.NAMES.items()},
    }


#: The tuning grid's best settings Model Lab lists; the page says how many were searched.
TUNING_SHOWN = 10


def coverage() -> list[dict[str, Any]]:
    """Per season of the registration's history: the games the backtest reads, those with a price it keeps
    (`backtest.load_market`'s filters), and whether the season is checked against Retrosheet yet."""
    p = backtest.registry()['protocol']
    first, last = p['training_from_season'], max(p['confirmation_seasons'])
    folder = history.HISTORY
    priced = set(backtest.load_market(first, last, folder)['game_id'].astype(str))
    checked = backtest.checked_seasons(folder)
    out = []
    for season in range(first, last + 1):
        path = folder / f'games_{season}.csv'
        if not path.exists():
            continue
        with path.open(encoding='utf-8', newline='') as f:
            ids = [row['game_id'] for row in csv.DictReader(f)]
        out.append({'season': season, 'games': len(ids), 'priced': sum(i in priced for i in ids),
                    'checked': season in checked})
    return out


def lab() -> dict[str, Any]:
    """What Model Lab and Methodology read: the registration's protocol and questions, the tuning, the confirmation
    once it has run (`python -m src.sports.mlb.backtest confirm`, once), and the history's coverage."""
    reg = backtest.registry()
    p = reg['protocol']
    tuning = _maybe(backtest.RESULTS / 'tuning.json')
    grid = reg['models']['model_a']['grid']
    return {
        'registered': reg['registered'],
        'protocol': {k: p[k] for k in ('training_from_season', 'validation_seasons', 'confirmation_seasons',
                                       'forward_holdout_season', 'alpha', 'budget_m')},
        'grid': grid,
        'questions': [{k: q.get(k) for k in ('id', 'kind', 'title', 'question', 'expected')}
                      for q in reg['hypotheses']],
        'tuning': None if tuning is None else {
            'seasons': tuning['seasons'], 'chosen': tuning['chosen'], 'searched': len(tuning['grid']),
            'best': sorted(tuning['grid'], key=lambda g: g['log_loss'])[:TUNING_SHOWN]},
        'confirmation': _maybe(backtest.RESULTS / 'confirmation.json'),
        'coverage': coverage(),
        'not_registered': reg['not_in_this_registration'],
        'amendments': len(reg['amendments']),
    }


def payload(now: datetime) -> dict[str, Any]:
    return {'built_utc': now.strftime('%Y-%m-%dT%H:%M:%SZ'), 'board': board(current_season(now)), 'lab': lab(),
            'changes': json.loads((TEMPLATE / 'changes.json').read_text(encoding='utf-8'))}


#: The parts page.html includes that live outside pages/: the shared stylesheet and the scripts the day boards
#: share. Every other part is the file of that name in pages/.
SHARED_PARTS = {'styles.css': SHARED_STYLES, 'escape.js': ESCAPE_JS, 'routes.js': ROUTES_JS,
                'favs.js': FAVS_JS, 'prefs.js': PREFS_JS, 'day_board.js': DAY_BOARD_JS}


def render(data: dict[str, Any]) -> str:
    """The page, by the renderer every page shares (src/core/page_render.py)."""
    return page_render.finish(page_render.assemble(TEMPLATE, SHARED_PARTS),
                              {'__FONT_FACES__': font_faces_css(), '__MLB_JSON__': safe_json(data)})


def main(argv: list[str] | None = None, now: datetime | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build MLB's pages (not yet published)")
    ap.add_argument('--out', default='site/mlb/index.html')
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(payload(now or datetime.now(UTC))), encoding='utf-8')
    print(f'wrote {out} ({out.stat().st_size} bytes)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
