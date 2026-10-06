"""Build the NHL's page from a sample week, for the browser checks.

The NHL's page is built from the daily run's files, which a fresh checkout
may not have yet and which hold whatever state the season is in. The browser
checks need a page with every kind of card on it, so this writes one sample
week (Monday 2026-10-05 to Sunday 2026-10-11) into a scratch copy of the
NHL's folders and builds the page from it with the real builder
(`src.sports.nhl.site`):

- final games graded right and wrong, a final game with no pick, an overtime
  and a shootout result;
- saved picks with a market price (Model B's) and without (Model A's), one
  too close to call;
- goalies Confirmed, Likely, with no report yet, and a club's last starter;
- a postponed game, and games not saved yet;
- standings odds and ratings for all 32 clubs.

The backtest's results and the drift rule are copied from the repository.

Run: python tests/browser/build_nhl.py --out <file.html>
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.core.sport import SportPaths
from src.sports.nhl import site, standings

SEASON = 2026
#: (game id, day, start UTC, away, home, status, away score, home score, last period)
GAMES = [
    ('2026020901', '2026-10-05', '23:00', 'PHI', 'TBL', 'final', 1, 4, 'REG'),
    ('2026020902', '2026-10-05', '23:30', 'OTT', 'BOS', 'final', 4, 3, 'OT'),
    ('2026020903', '2026-10-06', '23:00', 'NSH', 'TOR', 'final', 2, 3, 'SO'),
    ('2026020904', '2026-10-06', '23:00', 'CAR', 'MTL', 'final', 3, 1, 'REG'),
    ('2026020905', '2026-10-07', '23:00', 'UTA', 'NJD', 'postponed', None, None, None),
    ('2026020906', '2026-10-08', '23:00', 'MIN', 'BUF', 'scheduled', None, None, None),
    ('2026020907', '2026-10-08', '02:00', 'VGK', 'SEA', 'scheduled', None, None, None),
    ('2026020908', '2026-10-09', '23:30', 'COL', 'DAL', 'scheduled', None, None, None),
    ('2026020909', '2026-10-11', '00:00', 'EDM', 'LAK', 'scheduled', None, None, None),
]
#: game id -> (Model A, Model B or None, market (home price, away price, home prob) or None, goalies)
PICKS = {
    '2026020901': (0.58, 0.61, (-150, 130, 0.588), (('Andrei Vasilevskiy', 'Confirmed', 'projected'),
                                                    ('Samuel Ersson', 'Likely', 'projected'))),
    '2026020902': (0.55, 0.53, (-120, 100, 0.534), (('Jeremy Swayman', 'Confirmed', 'projected'),
                                                    ('Linus Ullmark', None, 'projected'))),
    '2026020903': (0.505, 0.51, (-105, -105, 0.5), (('Joseph Woll', 'Likely', 'projected'),
                                                    ('Juuse Saros', 'Confirmed', 'projected'))),
    '2026020904': (0.39, None, None, (('Jakub Dobes', None, 'last_start'),
                                      ('Pyotr Kochetkov', 'Confirmed', 'projected'))),
    '2026020906': (0.52, 0.49, (110, -130, 0.468), (('Ukko-Pekka Luukkonen', None, 'projected'),
                                                    ('Filip Gustavsson', 'Likely', 'projected'))),
    '2026020907': (0.47, None, None, (('Joey Daccord', 'Confirmed', 'projected'),
                                      ('Adin Hill', 'Confirmed', 'projected'))),
}


def _start(day: str, clock: str) -> str:
    # A start before 12:00 UTC is the evening of the day before, US time.
    if clock < '12:00':
        d = int(day[-2:]) + 1
        return f'{day[:-2]}{d:02d}T{clock}:00Z'
    return f'{day}T{clock}:00Z'


def write_season(root: Path) -> None:
    paths = SportPaths('nhl', root=root)
    games = [{'game_id': gid, 'slate': day, 'start_utc': _start(day, clock), 'home': home, 'away': away,
              'status': status, 'game_type': 'regular', 'home_score': hs, 'away_score': as_,
              'last_period': lp, 'neutral_site': False}
             for gid, day, clock, away, home, status, as_, hs, lp in GAMES]
    paths.results.mkdir(parents=True, exist_ok=True)
    (paths.results / f'schedule_{SEASON}.json').write_text(
        json.dumps({'as_of': '2026-10-06', 'games': games}), encoding='utf-8')
    folder = paths.predictions / str(SEASON)
    folder.mkdir(parents=True, exist_ok=True)
    graded = []
    by_id = {g['game_id']: g for g in games}
    for gid, (a, b, market, goalies) in PICKS.items():
        g = by_id[gid]
        lead = b if b is not None else a
        pick = g['home'] if lead >= 0.5 else g['away']
        doc = {'game_id': gid, 'season': SEASON, 'slate': g['slate'], 'start_utc': g['start_utc'],
               'home': g['home'], 'away': g['away'], 'model_a': a, 'model_b': b, 'pick': pick,
               'pick_model': 'model_b' if b is not None else 'model_a',
               'market': None if market is None else {'book': 'DraftKings', 'home_price': market[0],
                                                     'away_price': market[1], 'home_prob': market[2]},
               'goalies': {side: {'player_id': i, 'name': n, 'status': st, 'basis': basis, 'report': None}
                           for i, (side, (n, st, basis)) in enumerate(zip(('home', 'away'), goalies))},
               'saved_utc': '2026-10-05T21:00:00Z'}
        (folder / f'{gid}.json').write_text(json.dumps(doc), encoding='utf-8')
        if g['status'] == 'final':
            winner = g['home'] if g['home_score'] > g['away_score'] else g['away']
            graded.append({'game_id': gid, 'pick': pick, 'result': 'correct' if pick == winner else 'wrong'})
    (paths.results / f'graded_{SEASON}.json').write_text(json.dumps(graded), encoding='utf-8')
    clubs = [t for d in standings.DIVISIONS.values() for t in d]
    table = [{'team': t, 'division': standings.TEAM_DIVISION[t], 'conference': standings.TEAM_CONFERENCE[t],
              'points_now': i % 5, 'projected_points': 70.0 + i * 1.5, 'playoff_pct': min(0.9992, i / 32),
              'division_pct': min(0.95, (i / 32) ** 2)} for i, t in enumerate(clubs)]
    (paths.results / f'standings_{SEASON}.json').write_text(json.dumps(
        {'as_of': '2026-10-06', 'simulations': 10000, 'overtime_share': 0.2484,
         'shootout_share_of_overtime': 0.3333, 'teams': table}), encoding='utf-8')
    (paths.results / f'ratings_{SEASON}.json').write_text(json.dumps(
        {'as_of': '2026-10-06', 'K_shots': 2000,
         'teams': [{'team': t, 'goal': round(1.0 - i / 16, 4), 'shot': round(5.0 - i / 4, 4)}
                   for i, t in enumerate(clubs)],
         'goalies': [{'player_id': str(i), 'name': n, 'rating': round(0.004 - i * 0.001, 5), 'weighted_shots': 400.0}
                     for i, n in enumerate(('Andrei Vasilevskiy', 'Juuse Saros', 'Joseph Woll', None))]}),
        encoding='utf-8')
    (paths.results / f'drift_{SEASON}.json').write_text(json.dumps(
        {'games': 3, 'mean_log_loss': 0.69, 'baseline': 0.6753, 'flagged': False}), encoding='utf-8')
    for rel in ('data/nhl/drift_baseline.json', 'experiments/nhl/stage56/results/confirmation.json'):
        dest = root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / rel, dest)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description='Build the NHL page from a sample week')
    ap.add_argument('--out', required=True)
    args = ap.parse_args(argv)
    with tempfile.TemporaryDirectory() as tmp:
        write_season(Path(tmp))
        site.PATHS = SportPaths('nhl', root=Path(tmp))
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        return site.main(['--out', args.out, '--season', str(SEASON)])


if __name__ == '__main__':
    raise SystemExit(main())
