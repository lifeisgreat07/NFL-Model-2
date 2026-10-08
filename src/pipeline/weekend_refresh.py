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
yet fully graded. It never writes either: the weekly run stays the only
writer of picks and grades. The weekend workflow's commit is limited to
data/game_status/**, data/line_history/**, data/tv/** and data/team_news/**,
and tests hold that list exactly.

LINE SNAPSHOTS FOR LOCKED WEEKS (Stage 33 item 23, Mark, 2026-10-01). The
weekly run sees a week's lines only before it locks, so on its own the line
archive stops at the lock and the closing line the Stage 28 backtest needs
is never captured. So for every locked, ungraded week, this also appends
the schedule's current spreads to data/line_history/ -- through the weekly
run's own log_line_snapshot, so there is one format and one de-duplication
rule (a row when a game's line moves, a game with no spread skipped). It
appends and never rewrites a past capture, and it touches no week that is
not locked. Two writers of the archive are safe where two writers of picks
are not: an archive row is a dated observation, nothing reads it to make a
pick, and the two workflows' schedules cannot meet (a test holds that).

Only the games in the saved predictions are reported: the snapshot describes
the games the page shows. A predicted game the schedule no longer lists is
left out and printed, never filled in. A snapshot whose games did not change
is not rewritten, so a quiet run commits nothing and rebuilds nothing.

THE WEEKLY RUN USES THIS TOO (Stage 37 item 3). Tuesday's run grades a week
whose last snapshot was taken before Monday night's game, and once graded the
week leaves `weeks_to_refresh`, so Monday night's score never reached the
page. So the weekly run calls this with --status-only just before it grades:
the week about to be graded gets its final snapshot in the same commit as its
grades. --status-only writes data/game_status/ and nothing else (no line
snapshot), so the line archive keeps its two writers' schedules apart.
--weeks names the weeks outright, graded or not: the one-off backfill of the
weeks graded before this existed.

Run with: python -m src.pipeline.weekend_refresh [--season 2026] [--status-only] [--weeks 1 2 3]
"""
import argparse
import json
import sys
from datetime import UTC, datetime

import pandas as pd

# The folders and the season rule are defined once, in src/pipeline/paths.py
# (Stage 32 item 15). team_news and tv_channels import current_season from
# here, so the name stays.
from src.pipeline.paths import (
    PRED_DIR,
    RESULTS_DIR,
    STATUS_DIR,
    current_season,
    parse_week,
)
from src.pipeline.runlog import get_logger

log = get_logger(__name__)
SOURCE = 'nflverse schedule, via nflreadpy.load_schedules'


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
        key = parse_week(f.stem)
        if key is None:
            continue
        week = key[1]
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
    from src.pipeline.weekly_update import kickoff_utc
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
         status_dir=STATUS_DIR, snapshot=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--season', type=int, default=None)
    ap.add_argument('--status-only', action='store_true',
                    help='write data/game_status/ only, no line snapshot (the weekly run)')
    ap.add_argument('--weeks', type=int, nargs='+',
                    help='these locked weeks, graded or not (a backfill)')
    args = ap.parse_args(argv)
    now = now or datetime.now(UTC)
    season = args.season or current_season(now)
    if args.weeks:
        weeks = sorted(w for w in args.weeks if (pred_dir / f'{season}_week{w}.json').exists())
        for w in sorted(set(args.weeks) - set(weeks)):
            log.warning(f'{season} week {w}: no locked picks, so no snapshot')
    else:
        weeks = weeks_to_refresh(season, pred_dir, results_dir)
    if not weeks:
        log.info(f'{season}: no locked week is waiting on grading; nothing to refresh.')
        return 0
    if load is None:
        from src.pipeline.data_loader import load_schedule as load
    sched = load(season)
    if snapshot is None and not args.status_only:
        from src.pipeline.weekly_update import log_line_snapshot as snapshot
    for week in weeks:
        with open(pred_dir / f'{season}_week{week}.json') as f:
            preds = json.load(f)
        # Week alone, not game type: nflverse numbers playoff weeks on from
        # the regular season (19, 20, ...), so a week number is unique.
        rows = sched[sched['week'] == week]
        games, missing = build_week(preds, rows, now)
        counts = {s: sum(g['status'] == s for g in games) for s in ('final', 'started', 'upcoming')}
        wrote = write_week(season, week, games, now, status_dir)
        log.info(f"{season} week {week}: {counts['final']} final, {counts['started']} started, "
              f"{counts['upcoming']} upcoming -- {'written' if wrote else 'unchanged, not rewritten'}")
        for away, home in missing:
            log.warning(f'  WARNING: {away} at {home} is in the picks but not in the schedule; left out')
        # Item 23: the line archive for a locked week (see the docstring).
        # `weeks` holds locked, ungraded weeks only, so no other week is touched.
        # Not on --status-only (the weekly run) or a --weeks backfill.
        if not args.status_only and not args.weeks:
            snapshot(season, week, rows)
    return 0


if __name__ == '__main__':
    sys.exit(main())
