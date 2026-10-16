"""The site's home page (Stage 59; Mark chose option A of the rendered
"Pick'em Home Options" on 2026-10-05): one card per sport with where that
sport stands now, its season record, and a link to its board.

What the build reads, each sport from its own folders only:

- NFL: the saved weeks (`predictions/nfl/<season>_week<N>.json`) for the
  latest locked week and its kickoffs, any preview of the next week
  (`predictions/nfl/preview/`), and the graded weeks for Model B's record;
- NHL: the season's schedule and graded picks (`results/nhl/`);
- NBA: the same (`results/nba/`), live from opening night 2026-10-20
  (Stage 65). Before the daily run's first schedule its card says when
  picks start.

Stage 80 item 52 (the 2026-10-13 audit's F1 and F2) adds the slate: each
sport's next games, one row a game, with the side and chance of its saved
pick (`predictions/nhl/<season>/`, `predictions/nba/<season>/`, the NFL's
locked week), the NFL preview's lean, or, for a game whose pick is not saved
yet, the run that will save it (each sport's own lock rule, read, not
changed). The home's cards name the best pick from it, and the site build
puts the "Next games" strip on every page from it (src/site/build.py).

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

from src.core.page_comments import strip_page_comments
from src.core.page_fill import font_faces_css, safe_json

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


def day_sport_facts(sport: str, game_types: tuple[str, ...], root: Path = ROOT,
                    now: datetime | None = None) -> dict[str, Any]:
    """A sport that locks game by game (the NHL, the NBA): its games from two
    days before the build to two weeks after, as [start UTC, status], so the
    visitor's browser can count tonight's, and its picks' record. None of
    the season's schedule yet: {'built': False}."""
    results = root / 'results' / sport
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
                   if g.get('game_type') in game_types and g.get('start_utc')
                   and lo <= g['start_utc'] <= hi and g.get('status') not in ('cancelled', 'postponed'))
    season_starts = sorted(g['start_utc'] for g in sched.get('games', [])
                           if g.get('game_type') in game_types and g.get('start_utc'))
    # Starts ESPN says are not set yet (`time_valid` false: a placeholder
    # hour), which the card prints as "time TBD". Only the NBA's schedule
    # carries the field; for the NHL this is empty.
    unset = sorted({g['start_utc'] for g in sched.get('games', [])
                    if g.get('game_type') in game_types and g.get('start_utc') and g.get('time_valid') is False})
    # The first game of the season and how many picks are saved, so a card
    # can say when picks start rather than show an empty record (Stage 68
    # item 6). graded_<season>.json has one row per saved pick.
    return {'built': True, 'season': season, 'games': games,
            'first_game': season_starts[0] if season_starts else None, 'picks': len(graded), 'unset': unset,
            'record': {'label': 'Picks this season',
                       'won': sum(1 for r in graded if r.get('result') == 'correct'),
                       'lost': sum(1 for r in graded if r.get('result') == 'wrong')}}


def nhl_facts(root: Path = ROOT, now: datetime | None = None) -> dict[str, Any]:
    return day_sport_facts('nhl', ('regular', 'playoff'), root, now)


def nba_facts(root: Path = ROOT, now: datetime | None = None) -> dict[str, Any]:
    """The NBA's, as the NHL's (Stage 65), play-in games included. Before the
    daily run's first schedule the page is still built, and the card says
    when picks start rather than "not built"."""
    f = day_sport_facts('nba', ('regular', 'playin', 'playoff'), root, now)
    return f if f['built'] else {'built': True, 'games': [], 'first_game': None, 'picks': 0, 'unset': [],
                                 'record': {'label': 'Picks this season', 'won': 0, 'lost': 0}}


#: How close to an even chance a side may be and still be called "even",
#: in points, as every board's EVEN_BAND.
EVEN_BAND = 2
#: Each sport's next games the slate carries, from three hours before the
#: build: a full day in every sport (the NHL plays at most 16 in a day).
SLATE_GAMES = 20
_ISO = '%Y-%m-%dT%H:%M:%SZ'


def _side(home_prob: float, home: str, away: str, team: str | None = None) -> dict[str, Any]:
    """The side a chance favours (or `team`, a saved pick's side), its chance
    in whole percent, and whether it is inside the even band."""
    team = team or (home if home_prob >= 0.5 else away)
    pct = home_prob if team == home else 1 - home_prob
    return {'p': team, 'c': round(pct * 100), 'e': abs(home_prob * 100 - 50) < EVEN_BAND}


def lock_run(start: datetime, runs: tuple[tuple[int, int, int], ...], slack: timedelta) -> datetime | None:
    """The run that will save a game starting at `start`: the last run before
    it whose next run, plus the slack, would come too late. The rule of
    each sport's GameLock.decide, and of the boards' lockRunFor
    (tests/test_tonight_strip.py runs it against GameLock)."""
    day0 = datetime(start.year, start.month, start.day, tzinfo=UTC) - timedelta(days=3)
    times = sorted(day0 + timedelta(days=d, hours=h, minutes=m)
                   for d in range(5) for (wd, h, m) in runs if (day0 + timedelta(days=d)).weekday() == wd)
    for i in range(len(times) - 1):
        if times[i] >= start:
            break
        if start < times[i + 1] + slack:
            return times[i]
    return None


def nfl_slate(root: Path = ROOT, now: datetime | None = None) -> list[dict[str, Any]]:
    """The NFL's latest locked week, each game Model B's side, and any later
    week's preview, each game a lean; from three hours before the build."""
    lo = ((now or datetime.now(UTC)) - timedelta(hours=3)).strftime(_ISO)
    weeks = _week_files(root / 'predictions' / 'nfl')
    if not weeks:
        return []
    out = []
    latest = max(weeks)
    previews = {k: p for k, p in _week_files(root / 'predictions' / 'nfl' / 'preview').items() if k > latest}
    for kind, path in [('pick', weeks[latest])] + [('lean', previews[k]) for k in sorted(previews)]:
        for g in _read(path) or []:
            t, b = nfl_kickoff(g), g.get('model_b_home_win_prob')
            if t is None or b is None or t < lo:
                continue
            out.append({'s': 'nfl', 't': t, 'a': g['away'], 'h': g['home'], 'k': kind, **_side(b, g['home'], g['away'])})
    return out


def day_slate(sport: str, game_types: tuple[str, ...], runs: tuple[tuple[int, int, int], ...], slack: timedelta,
              root: Path = ROOT, now: datetime | None = None) -> list[dict[str, Any]]:
    """A sport that locks game by game: its next games, each with its saved
    pick's side and the chance its leading model gave it (Model B, else
    Model A, as the board's pickText), or the run that will save it."""
    results = root / 'results' / sport
    seasons = sorted(int(m.group(1)) for p in results.glob('schedule_*.json')
                     if (m := re.fullmatch(r'schedule_(\d{4})', p.stem))) if results.is_dir() else []
    if not seasons:
        return []
    season = seasons[-1]
    now = now or datetime.now(UTC)
    lo = (now - timedelta(hours=3)).strftime(_ISO)
    games = sorted((g for g in (_read(results / f'schedule_{season}.json') or {}).get('games', [])
                    if g.get('game_type') in game_types and g.get('start_utc') and g['start_utc'] >= lo
                    and g.get('status') == 'scheduled'), key=lambda g: g['start_utc'])[:SLATE_GAMES]
    folder = root / 'predictions' / sport / str(season)
    out = []
    for g in games:
        row: dict[str, Any] = {'s': sport, 't': g['start_utc'], 'a': g['away'], 'h': g['home']}
        p = _read(folder / f"{g['game_id']}.json")
        lead = None if p is None else (p.get('model_b') if p.get('model_b') is not None else p.get('model_a'))
        if p is not None and p.get('pick') and lead is not None:
            row.update(k='pick', **_side(lead, g['home'], g['away'], p['pick']))
        else:
            run = lock_run(datetime.strptime(g['start_utc'], _ISO).replace(tzinfo=UTC), runs, slack)
            row.update(k='wait', l=run.strftime(_ISO) if run else None)
        out.append(row)
    return out


def slate(root: Path = ROOT, now: datetime | None = None) -> list[dict[str, Any]]:
    """Every sport's next games, in start order."""
    from src.sports.nba import lock as nba_lock
    from src.sports.nhl import lock as nhl_lock
    rows = (nfl_slate(root, now)
            + day_slate('nhl', ('regular', 'playoff'), nhl_lock.RUNS_UTC, nhl_lock.SLACK, root, now)
            + day_slate('nba', ('regular', 'playin', 'playoff'), nba_lock.RUNS_UTC, nba_lock.SLACK, root, now))
    return sorted(rows, key=lambda r: r['t'])


def facts(root: Path = ROOT, now: datetime | None = None) -> dict[str, Any]:
    # built_utc: when this page was made, printed as "Updated ... ET" as the
    # sport pages print theirs (Stage 77 item 30, the 2026-10-13 audit's H2).
    built = (now or datetime.now(UTC)).strftime('%Y-%m-%dT%H:%M:%SZ')
    return {'nfl': nfl_facts(root), 'nhl': nhl_facts(root, now), 'nba': nba_facts(root, now), 'built_utc': built,
            'slate': slate(root, now)}




def render(data: dict[str, Any], font_faces: str = '') -> str:
    page = (TEMPLATE / 'page.html').read_text(encoding='utf-8')
    html = (page.replace('{% include "styles.css" %}', SHARED_STYLES.read_text(encoding='utf-8'))
                .replace('{% include "home.css" %}', (TEMPLATE / 'home.css').read_text(encoding='utf-8'))
                .replace('{% include "home.js" %}', (TEMPLATE / 'home.js').read_text(encoding='utf-8')))
    # Comments stay in the templates for whoever reads them; the page a
    # visitor downloads does not carry them (src/core/page_comments.py,
    # Stage 68 item 19). Stripped before the fills, so no data is lexed.
    html = strip_page_comments(html)
    html = html.replace('__FONT_FACES__', font_faces).replace('__HOME_JSON__', safe_json(data))
    left = sorted(set(re.findall(r'__[A-Z0-9_]+__', html)) | ({'{% include'} if '{% include' in html else set()))
    if left:
        raise ValueError(f'unfilled placeholders: {left}')
    return html




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
