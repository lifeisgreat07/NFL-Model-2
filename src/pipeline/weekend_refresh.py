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

A CANCELLED GAME (Stage 39; Mark's call, 2026-10-05) kicks off on the
schedule and never gets a score, so on its own it read "started" for the rest
of the season and held its week open forever. nflverse gives no cancelled
flag (2022's Bills-Bengals game is a row with no score), and "no score some
hours after kickoff" is also what a late data feed looks like, so the call
is not inferred: data/cancelled_games.json lists each cancelled game with a
link to the league's announcement, as a QB override does. A listed game
reads "cancelled", is never graded, counts for nothing, and no longer holds
its week open. A game with no score a day and a half after kickoff that is
NOT listed is printed as a warning, so the file gets written.

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
    CANCELLED_FILE,
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


class CancelledGamesError(ValueError):
    """data/cancelled_games.json exists but cannot be trusted."""


def load_cancelled(path=CANCELLED_FILE):
    """{(season, week, away, home)} for every game the league cancelled.

    A missing file means none. A malformed one FAILS the run: a cancellation
    removes a game from every count, which is not something to do on an
    entry with no source."""
    if not path.exists():
        return set()
    with open(path, encoding='utf-8') as f:
        entries = json.load(f)
    if not isinstance(entries, list):
        raise CancelledGamesError(f'{path.name}: expected a list of games')
    out = set()
    for e in entries:
        missing = [k for k in ('season', 'week', 'away', 'home', 'source') if not e.get(k)]
        if missing:
            raise CancelledGamesError(f'{path.name}: {e!r} is missing {missing}')
        if not str(e['source']).startswith(('http://', 'https://')):
            raise CancelledGamesError(f"{path.name}: {e['away']} at {e['home']}'s source must be a link")
        out.add((int(e['season']), int(e['week']), e['away'], e['home']))
    return out


def _cancelled_in(season, week, cancelled):
    return sum(1 for s, w, _, _ in cancelled if (s, w) == (season, week))


def weeks_to_refresh(season, pred_dir=PRED_DIR, results_dir=RESULTS_DIR, cancelled=None):
    """Every saved week of this season with fewer graded games than picks,
    oldest first, a cancelled game counting as finished. A week graded
    before it was played has an empty graded file, so it is still
    unfinished."""
    cancelled = load_cancelled() if cancelled is None else cancelled
    weeks = []
    for f in pred_dir.glob(f'{season}_week*.json'):
        key = parse_week(f.stem)
        if key is None:
            continue
        week = key[1]
        graded = results_dir / f'{season}_week{week}_graded.json'
        if _count(graded) + _cancelled_in(season, week, cancelled) < _count(f):
            weeks.append(week)
    return sorted(weeks)


def _number(value):
    return None if value is None or pd.isna(value) else float(value)


def _score(value):
    return None if value is None or pd.isna(value) else int(value)


#: How long after kickoff a game with no score is worth a warning: past any
#: overtime and any late feed, short of the next scheduled refresh's lateness.
NO_SCORE_WARNING = pd.Timedelta(hours=36)


def game_status(row, now, cancelled=False):
    """'final', 'cancelled', 'started' or 'upcoming' for one schedule row at
    `now` (UTC). A score wins over a cancellation: a listed game that has one
    was played after all, and is reported as it ended."""
    from src.pipeline.weekly_update import kickoff_utc
    if _score(row.get('home_score')) is not None and _score(row.get('away_score')) is not None:
        return 'final'
    if cancelled:
        return 'cancelled'
    kickoff = kickoff_utc(row)
    if kickoff is not None and kickoff <= pd.Timestamp(now).tz_convert('UTC'):
        return 'started'
    return 'upcoming'


def build_week(preds, week_rows, now, cancelled=frozenset()):
    """(games, missing): one entry per predicted game, in the picks' order,
    and the (away, home) pairs the schedule no longer lists. `cancelled`
    holds this week's cancelled (away, home) pairs."""
    from src.pipeline.weekly_update import _venue, site_is_neutral
    by_pair = {(r['away_team'], r['home_team']): r for _, r in week_rows.iterrows()}
    games, missing = [], []
    for p in preds:
        row = by_pair.get((p['away'], p['home']))
        if row is None:
            missing.append((p['away'], p['home']))
            continue
        status = game_status(row, now, cancelled=(p['away'], p['home']) in cancelled)
        final = status == 'final'
        games.append({
            'away': p['away'], 'home': p['home'],
            'status': status,
            'away_score': _score(row.get('away_score')) if final else None,
            'home_score': _score(row.get('home_score')) if final else None,
            'spread_line': _number(row.get('spread_line')),
            # Stage 37 item 6, for weeks locked before the pick carried it.
            'neutral_site': site_is_neutral(row),
            'venue': _venue(row),
        })
    return games, missing


def overdue(preds, week_rows, now, cancelled=frozenset()):
    """(away, home) for each picked game with no score NO_SCORE_WARNING after
    kickoff that is not listed as cancelled."""
    from src.pipeline.weekly_update import kickoff_utc
    by_pair = {(r['away_team'], r['home_team']): r for _, r in week_rows.iterrows()}
    out = []
    for p in preds:
        pair = (p['away'], p['home'])
        row = by_pair.get(pair)
        if row is None or pair in cancelled:
            continue
        kickoff = kickoff_utc(row)
        has_score = _score(row.get('home_score')) is not None and _score(row.get('away_score')) is not None
        if kickoff is not None and not has_score and pd.Timestamp(now).tz_convert('UTC') - kickoff > NO_SCORE_WARNING:
            out.append(pair)
    return out


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
         status_dir=STATUS_DIR, snapshot=None, cancelled=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--season', type=int, default=None)
    ap.add_argument('--status-only', action='store_true',
                    help='write data/game_status/ only, no line snapshot (the weekly run)')
    ap.add_argument('--weeks', type=int, nargs='+',
                    help='these locked weeks, graded or not (a backfill)')
    args = ap.parse_args(argv)
    now = now or datetime.now(UTC)
    season = args.season or current_season(now)
    cancelled_all = load_cancelled() if cancelled is None else cancelled
    if args.weeks:
        weeks = sorted(w for w in args.weeks if (pred_dir / f'{season}_week{w}.json').exists())
        for w in sorted(set(args.weeks) - set(weeks)):
            log.warning(f'{season} week {w}: no locked picks, so no snapshot')
    else:
        weeks = weeks_to_refresh(season, pred_dir, results_dir, cancelled_all)
    if not weeks:
        log.info(f'{season}: no locked week is waiting on grading; nothing to refresh.')
        return 0
    if load is None:
        from src.pipeline.data_loader import load_schedule as load
    sched = load(season)
    from src.pipeline.weekly_update import with_usual_stadium
    if snapshot is None and not args.status_only:
        from src.pipeline.weekly_update import log_line_snapshot as snapshot
    for week in weeks:
        with open(pred_dir / f'{season}_week{week}.json') as f:
            preds = json.load(f)
        # Week alone, not game type: nflverse numbers playoff weeks on from
        # the regular season (19, 20, ...), so a week number is unique.
        rows = with_usual_stadium(sched, sched[sched['week'] == week])
        this_week = {(a, h) for s, w, a, h in cancelled_all if (s, w) == (season, week)}
        games, missing = build_week(preds, rows, now, this_week)
        counts = {s: sum(g['status'] == s for g in games) for s in ('final', 'started', 'upcoming')}
        for away, home in overdue(preds, rows, now, this_week):
            log.warning(f'  WARNING: {away} at {home} kicked off over {NO_SCORE_WARNING.total_seconds() / 3600:.0f} hours '
                        f'ago with no score. If the league cancelled it, list it in data/cancelled_games.json '
                        f'with a link to the announcement; until then it reads "started".')
        wrote = write_week(season, week, games, now, status_dir)
        n_cancelled = sum(g['status'] == 'cancelled' for g in games)
        log.info(f"{season} week {week}: {counts['final']} final, {counts['started']} started, "
              f"{counts['upcoming']} upcoming" + (f", {n_cancelled} cancelled" if n_cancelled else '')
              + f" -- {'written' if wrote else 'unchanged, not rewritten'}")
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
