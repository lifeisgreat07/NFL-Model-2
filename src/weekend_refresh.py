"""Refresh game status, final scores and the latest line between the
Thursday lock and Tuesday's grading. Never touches a saved pick.

Stage 15 (CLAUDE.md). Between Thursday's lock and Tuesday's grading the page
knows nothing new: a game played on Sunday still reads as upcoming until the
weekly run grades it. This fills that gap with a snapshot per unfinished week,
data/game_status/<season>_week<N>.json, read from nflverse's schedule:

    status       "upcoming" before kickoff, "started" once kicked off with no
                 final score yet, "final" once both scores are in
    home_score, away_score   null until final
    spread_line  the latest line, positive when the HOME team is favoured
                 (the stored convention everywhere in this repository)

TWO WRITERS OF PICKS IS TWO WAYS TO BREAK A LOCK (decided 2026-09-24). This
reads predictions/ and results/ only to learn which weeks are locked and not
yet fully graded, and writes nothing but data/game_status/. The weekly run
stays the only writer of picks, grades and the line archive
(data/line_history/, which it appends on its own schedule). The weekend
workflow's commit is limited to data/game_status/**, and tests hold both.

Only the games in the saved predictions are reported: the snapshot describes
the games the page shows. A predicted game the schedule no longer lists is
left out and printed, never filled in. A snapshot whose games did not change
is not rewritten, so a quiet run commits nothing and rebuilds nothing.

Run with: python src/weekend_refresh.py [--season 2026]
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

ROOT = Path(__file__).parent.parent
PRED_DIR = ROOT / 'predictions'
RESULTS_DIR = ROOT / 'results'
STATUS_DIR = ROOT / 'data' / 'game_status'
SOURCE = 'nflverse schedule, via nflreadpy.load_schedules'


def current_season(today):
    """January and February still belong to the season that kicked off the
    year before (the playoffs); the weekly workflow decides the same way."""
    return today.year - 1 if today.month <= 2 else today.year


def _count(path):
    if not path.exists():
        return 0
    with open(path) as f:
        return len(json.load(f))


def weeks_to_refresh(season, pred_dir=PRED_DIR, results_dir=RESULTS_DIR):
    """Every saved week of this season with fewer graded games than picks,
    oldest first. A week graded before it was played has an empty graded
    file, so it is still unfinished."""
    weeks = []
    for f in pred_dir.glob(f'{season}_week*.json'):
        try:
            week = int(f.stem.split('_week')[1])
        except (IndexError, ValueError):
            continue
        graded = results_dir / f'{season}_week{week}_graded.json'
        if _count(graded) < _count(f):
            weeks.append(week)
    return sorted(weeks)


def _number(value):
    return None if value is None or pd.isna(value) else float(value)


def _score(value):
    return None if value is None or pd.isna(value) else int(value)


def game_status(row, now):
    """'final', 'started' or 'upcoming' for one schedule row at `now` (UTC)."""
    from weekly_update import kickoff_utc
    if _score(row.get('home_score')) is not None and _score(row.get('away_score')) is not None:
        return 'final'
    kickoff = kickoff_utc(row)
    if kickoff is not None and kickoff <= pd.Timestamp(now).tz_convert('UTC'):
        return 'started'
    return 'upcoming'


def build_week(preds, week_rows, now):
    """(games, missing): one entry per predicted game, in the picks' order,
    and the (away, home) pairs the schedule no longer lists."""
    by_pair = {(r['away_team'], r['home_team']): r for _, r in week_rows.iterrows()}
    games, missing = [], []
    for p in preds:
        row = by_pair.get((p['away'], p['home']))
        if row is None:
            missing.append((p['away'], p['home']))
            continue
        status = game_status(row, now)
        final = status == 'final'
        games.append({
            'away': p['away'], 'home': p['home'],
            'status': status,
            'away_score': _score(row.get('away_score')) if final else None,
            'home_score': _score(row.get('home_score')) if final else None,
            'spread_line': _number(row.get('spread_line')),
        })
    return games, missing


def write_week(season, week, games, now, status_dir=STATUS_DIR):
    """Write the snapshot unless its games are unchanged. Returns True when
    it wrote. read_at alone changing is not a change."""
    path = status_dir / f'{season}_week{week}.json'
    if path.exists():
        with open(path) as f:
            if json.load(f).get('games') == games:
                return False
    status_dir.mkdir(parents=True, exist_ok=True)
    snapshot = {
        'season': season, 'week': week, 'source': SOURCE,
        'read_at': pd.Timestamp(now).tz_convert('UTC').strftime('%Y-%m-%dT%H:%M:%SZ'),
        'games': games,
    }
    with open(path, 'w') as f:
        json.dump(snapshot, f, indent=2)
        f.write('\n')
    return True


def main(argv=None, now=None, load=None, pred_dir=PRED_DIR, results_dir=RESULTS_DIR,
         status_dir=STATUS_DIR):
    ap = argparse.ArgumentParser()
    ap.add_argument('--season', type=int, default=None)
    args = ap.parse_args(argv)
    now = now or datetime.now(timezone.utc)
    season = args.season or current_season(now)
    weeks = weeks_to_refresh(season, pred_dir, results_dir)
    if not weeks:
        print(f'{season}: no locked week is waiting on grading; nothing to refresh.')
        return 0
    if load is None:
        from data_loader import load_schedule as load
    sched = load(season)
    for week in weeks:
        with open(pred_dir / f'{season}_week{week}.json') as f:
            preds = json.load(f)
        # Week alone, not game type: nflverse numbers playoff weeks on from
        # the regular season (19, 20, ...), so a week number is unique.
        rows = sched[sched['week'] == week]
        games, missing = build_week(preds, rows, now)
        counts = {s: sum(g['status'] == s for g in games) for s in ('final', 'started', 'upcoming')}
        wrote = write_week(season, week, games, now, status_dir)
        print(f"{season} week {week}: {counts['final']} final, {counts['started']} started, "
              f"{counts['upcoming']} upcoming -- {'written' if wrote else 'unchanged, not rewritten'}")
        for away, home in missing:
            print(f'  WARNING: {away} at {home} is in the picks but not in the schedule; left out')
    return 0


if __name__ == '__main__':
    sys.exit(main())
