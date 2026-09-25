"""
Data-quality checks on what nflverse hands the weekly run, before any pick
is made from it.

This project's rule is that "the pipeline should fail loudly when critical
data is wrong rather than silently generating unreliable predictions". Until
Stage 4 nothing enforced it: a schedule missing a column, a team abbreviation
nflverse renamed, or a week of play-by-play that never arrived would flow
straight into the ratings, and the first sign would be a strange pick.

Two severities, on purpose:

  ERROR    the data is wrong in a way that makes a pick untrustworthy --
           a required column missing, a game listed twice, a team the model
           has never heard of, a score on one side only, a whole completed
           week with no plays behind it. The run stops.
  WARNING  worth a line in the log and in the weekly summary, but not worth
           losing a week's picks over -- chiefly the LATEST completed week
           missing play-by-play, because nflverse rebuilds nightly and the
           Tuesday run can land before Monday night's game is in. Stopping
           there would make a normal Tuesday a failure.

Failing the run is a real cost: a failure on a locking run means that week
has no picks. So the ERROR list is kept to things that would corrupt a pick
anyway, and each one has a test built to trip it (tests/test_data_quality.py).

Run standalone: python src/data_quality.py --season 2026
"""
import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from data_loader import REQUIRED_PBP_COLS, REQUIRED_SCHEDULE_COLS  # noqa: E402

#: The 32 franchises under the abbreviations nflverse uses for current
#: seasons. Older seasons use OAK/SD/STL; the checks below only look at the
#: target season's schedule, so those never appear here.
NFL_TEAMS = frozenset({
    'ARI', 'ATL', 'BAL', 'BUF', 'CAR', 'CHI', 'CIN', 'CLE', 'DAL', 'DEN',
    'DET', 'GB', 'HOU', 'IND', 'JAX', 'KC', 'LA', 'LAC', 'LV', 'MIA',
    'MIN', 'NE', 'NO', 'NYG', 'NYJ', 'PHI', 'PIT', 'SEA', 'SF', 'TB',
    'TEN', 'WAS',
})

#: Regular-season games since the 17-game schedule began in 2021.
REG_GAMES_SINCE_2021 = 272


class DataQualityError(RuntimeError):
    """Raised when the data would make a pick untrustworthy."""


@dataclass
class Report:
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    def extend(self, other):
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        return self

    @property
    def ok(self):
        return not self.errors

    def lines(self):
        return ([f'ERROR: {e}' for e in self.errors]
                + [f'WARNING: {w}' for w in self.warnings])


def _regular_season(sched):
    if 'game_type' in sched.columns:
        return sched[sched['game_type'] == 'REG']
    return sched


def completed_weeks(sched):
    """Regular-season weeks in which at least one game has a final score."""
    reg = _regular_season(sched)
    done = reg.dropna(subset=['home_score', 'away_score'])
    return sorted(int(w) for w in done['week'].unique())


def check_schedule(sched, season):
    report = Report()
    if len(sched) == 0:
        # The offseason, before nflverse publishes the season's schedule. The
        # weekly run already exits cleanly here ("No games found"); failing it
        # instead would turn every spring Tuesday and Thursday red.
        report.warnings.append(f'{season} schedule has no rows yet')
        return report
    missing = [c for c in REQUIRED_SCHEDULE_COLS if c not in sched.columns]
    if missing:
        report.errors.append(f'{season} schedule is missing required columns: {missing}')
        return report  # everything below reads those columns

    reg = _regular_season(sched)
    if season >= 2021 and len(reg) != REG_GAMES_SINCE_2021:
        # A WARNING, not an ERROR (decided with Mark, 2026-09-24). An odd
        # count does not by itself corrupt any one pick -- a cancelled or
        # added game changes the total and nothing else -- and an ERROR on a
        # locking run costs the whole week its picks. A duplicated game,
        # which is the count going wrong in a way that DOES corrupt a pick,
        # has its own ERROR below.
        report.warnings.append(
            f'{season} schedule lists {len(reg)} regular-season games; '
            f'expected {REG_GAMES_SINCE_2021}')

    key = ['week', 'away_team', 'home_team']
    named = sched.dropna(subset=key)
    dupes = named[named.duplicated(subset=key, keep=False)]
    if len(dupes):
        pairs = sorted({f"wk{int(r.week)} {r.away_team}@{r.home_team}"
                        for r in dupes.itertuples()})
        report.errors.append(f'{season} schedule lists games twice: {pairs}')

    teams = set(reg['home_team'].dropna()) | set(reg['away_team'].dropna())
    unknown = sorted(teams - NFL_TEAMS)
    if unknown:
        report.errors.append(
            f'{season} schedule has team abbreviations the model does not know: '
            f'{unknown}. nflverse may have renamed a team.')

    half = sched[sched['home_score'].isna() != sched['away_score'].isna()]
    if len(half):
        pairs = sorted(f"wk{int(r.week)} {r.away_team}@{r.home_team}"
                       for r in half.itertuples())
        report.errors.append(f'{season} schedule has a score on one side only: {pairs}')
    return report


def check_plays(raw, sched, season):
    """Play-by-play against the schedule that says which weeks are done."""
    report = Report()
    missing = [c for c in REQUIRED_PBP_COLS if c not in raw.columns]
    if missing:
        report.errors.append(f'play-by-play is missing required columns: {missing}')
        return report

    done = completed_weeks(sched)
    if not done:
        return report
    this = raw[(raw['season'] == season) & (raw['season_type'] == 'REG')]
    have = set(int(w) for w in this['week'].unique())
    latest = done[-1]
    for week in done:
        if week in have:
            continue
        msg = (f'{season} week {week} is complete in the schedule but has no '
               f'play-by-play')
        if week == latest:
            report.warnings.append(
                msg + ' yet. This is the latest completed week, and nflverse '
                'rebuilds nightly, so it may simply not have landed.')
        else:
            report.errors.append(msg + '. Every rating after it is built without it.')

    if 'play_type' in this.columns:
        scrimmage = this[this['play_type'].isin(['pass', 'run'])]
        if len(scrimmage):
            share = scrimmage['epa'].isna().mean()
            if share > 0.05:
                report.warnings.append(
                    f'{share:.1%} of {season} pass/run plays have no EPA '
                    f'(over 5%); team ratings rest on EPA')
    return report


def run_checks(raw, sched, season):
    return check_schedule(sched, season).extend(
        check_plays(raw, sched, season) if raw is not None else Report())


def enforce(raw, sched, season, out=print):
    """Print every finding, then stop the run if any is an error."""
    report = run_checks(raw, sched, season)
    for line in report.lines():
        out(f'  data quality {line}')
    if not report.ok:
        raise DataQualityError(
            f'{len(report.errors)} data-quality error(s) for {season}; no picks '
            f'are made from data this wrong. See the lines above.')
    if not report.lines():
        out('  data quality: no findings')
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description='Check nflverse data for a season.')
    ap.add_argument('--season', type=int, required=True)
    args = ap.parse_args(argv)
    from data_loader import load_plays, load_schedule
    sched = load_schedule(args.season)
    raw = load_plays([args.season]) if completed_weeks(sched) else None
    try:
        enforce(raw, sched, args.season)
    except DataQualityError as exc:
        print(exc)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
