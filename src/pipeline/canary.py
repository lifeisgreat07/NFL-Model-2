"""
The nightly canary: run the weekly job's data path every night, so a break
upstream shows up the day it happens rather than on the next locking run.

The case this exists for: in the 2026 offseason nflreadpy began rejecting
play-by-play requests for a season it did not yet consider current, and the
weekly run crashed on it (PR #6). Nothing ran between the scheduled weekly
runs, so the first sign was the crash itself. A nightly run of the same loads
would have shown it days early.

So this does what the weekly run does up to the point of fitting, and nothing
it writes is kept:

  1. load play-by-play for the same seasons the weekly run asks for
     (TRAIN_SEASONS plus the target season), through the same loader
  2. load the target season's schedule
  3. the data-quality checks the weekly run enforces (src/pipeline/data_quality.py)
  4. today's columns against the committed snapshot (src/pipeline/schema_check.py)
  5. work out the next week to predict, as the weekly run does
  6. read that week's page on nfl.com, the TV-channel source (Stage 15),
     and check its shape (check_schedule_page below)
  7. ask every source the scheduled jobs read whether it answers, one line
     each (Stage 41 item 5): a failed load above says THAT something broke,
     this says WHICH host. An unreachable source the picks depend on is an
     error; one that only feeds context (injuries, depth charts, TV) is a
     warning, because neither ever costs a pick

A step that raises is recorded as an error and the rest still run, so one
report says everything that is wrong tonight. Exit 1 on any error; the
workflow turns that into an issue (src/pipeline/alerts.py).

    python -m src.pipeline.canary [--season 2026] [--report canary-report.md]
"""
import argparse
import traceback
from pathlib import Path

from src.pipeline.data_quality import Report
from src.pipeline.paths import (
    current_season,
)


def run(season, steps=None):
    """Run every step; return (report, notes). `steps` is injectable so the
    tests can drive the error paths without a network."""
    steps = steps or default_steps()
    report, notes, state = Report(), [], {'season': season}
    for name, step in steps:
        try:
            result = step(state)
        except Exception as exc:  # the crash is the finding
            report.errors.append(f'{name} raised {type(exc).__name__}: {exc}')
            notes.append(f'{name}: FAILED\n\n```\n{traceback.format_exc(limit=3)}```')
            continue
        if isinstance(result, Report):
            report.extend(result)
            notes.append(f'{name}: {len(result.errors)} error(s), '
                         f'{len(result.warnings)} warning(s)')
        else:
            notes.append(f'{name}: {result}')
    return report, notes


def default_steps():
    from src.pipeline import data_quality, schema_check
    from src.pipeline.config import TRAIN_SEASONS
    from src.pipeline.data_loader import load_plays, load_schedule

    def plays(state):
        seasons = sorted(set(TRAIN_SEASONS) | {state['season']})
        state['raw'] = load_plays(seasons)
        return f"{len(state['raw'])} plays for {seasons}"

    def schedule(state):
        state['sched'] = load_schedule(state['season'])
        return f"{len(state['sched'])} games"

    def quality(state):
        if 'sched' not in state:
            return 'skipped: the schedule did not load'
        return data_quality.run_checks(state.get('raw'), state['sched'], state['season'])

    def schema(state):
        if 'raw' not in state or 'sched' not in state:
            return 'skipped: play-by-play or the schedule did not load'
        current = schema_check.columns_of({'pbp': state['raw'], 'schedule': state['sched']})
        return schema_check.compare(schema_check.load_snapshot(), current)

    def next_week(state):
        from src.pipeline.weekly_update import determine_next_week
        state['next_week'] = determine_next_week(state['season'])
        return f"next week to predict: {state['next_week']}"

    def nfl_schedule(state):
        from src.pipeline import nfl_schedule_probe as probe
        week = state.get('next_week')
        if week is None:
            return 'skipped: the next week is not known'
        if week > LAST_REGULAR_WEEK:
            return f'skipped: week {week} is past the regular season'
        return check_schedule_page(probe.fetch(week, state['season']), state['season'], week)

    def sources(state):
        return reachability(state['season'], state.get('next_week'))

    return [('load play-by-play', plays), ('load schedule', schedule),
            ('data quality', quality), ('schema', schema),
            ('next week', next_week), ('nfl.com schedule', nfl_schedule),
            ('sources', sources)]


NFLVERSE = 'https://github.com/nflverse/nflverse-data/releases/download/'

#: (name, url template, whether a pick depends on it). The nflverse paths are
#: the ones nflreadpy's downloader builds (load_pbp, load_schedules,
#: load_injuries, load_depth_charts); nfl.com's is the TV source's.
SOURCES = (
    ('nflverse play-by-play', NFLVERSE + 'pbp/play_by_play_{season}.parquet', True),
    ('nflverse schedules', NFLVERSE + 'schedules/games.parquet', True),
    ('nflverse injuries', NFLVERSE + 'injuries/injuries_{season}.parquet', False),
    ('nflverse depth charts', NFLVERSE + 'depth_charts/depth_charts_{season}.parquet', False),
    ('nfl.com schedule', 'https://www.nfl.com/schedules/{season}/by-week/week-{week}', False),
)


def _head(url, timeout=20):
    """(HTTP status, None) or (None, the error). A HEAD that redirects is
    followed: nflverse's release assets answer 302 to a storage host."""
    import urllib.error
    import urllib.request
    req = urllib.request.Request(url, method='HEAD', headers={'User-Agent': 'NFL-Model-2 canary'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, None
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception as e:  # unreachable: DNS, TLS, timeout -- the point is to name it
        return None, f'{type(e).__name__}: {e}'


def reachability(season, week, head=_head):
    """One line per source: does it answer? (Stage 41 item 5)"""
    report = Report()
    for name, template, critical in SOURCES:
        if '{week}' in template and (week is None or week > LAST_REGULAR_WEEK):
            report.warnings.append(f'{name}: not checked (no regular-season week to ask for)')
            continue
        url = template.format(season=season, week=week)
        status, error = head(url)
        if status is not None and 200 <= status < 400:
            continue
        problem = f'{name}: ' + (f'HTTP {status}' if status is not None else f'unreachable ({error})') + f' -- {url}'
        (report.errors if critical else report.warnings).append(problem)
    return report


#: nfl.com's by-week pages are regular-season weeks; the playoffs are not.
LAST_REGULAR_WEEK = 18

#: What a game on nfl.com's page cannot lack without the FEED having changed.
#: The rest (a kickoff, a network, a territory) can be missing for a real
#: reason -- week 18's kickoffs are not set until late December -- so those
#: are warnings: a missing or failed channel never fails the canary.
SHAPE = ('elias id', 'two teams')


def check_schedule_page(page, season, week):
    """The canary's view of one nfl.com week (Stage 15, item 6). ERRORS mean
    the feed changed: no games in the payload, a game missing its id or its
    teams, or a game from another week. WARNINGS are a game missing its
    kickoff, territory or network, which the TV code already holds back."""
    from src.pipeline.nfl_schedule_probe import check_game, elias_id, extract_games
    report = Report()
    games = extract_games(page)
    if not games:
        report.errors.append(f'nfl.com week {week}: no games in the page payload -- '
                             f'the page or its embedded data has changed')
        return report
    for g in games:
        missing = check_game(g, season, week)
        name = elias_id(g) or g.get('id', '?')
        hard = [m for m in missing if m in SHAPE or m.startswith('this week')]
        soft = [m for m in missing if m not in hard]
        if hard:
            report.errors.append(f'nfl.com week {week}, game {name}: missing {", ".join(hard)}')
        if soft:
            report.warnings.append(f'nfl.com week {week}, game {name}: missing {", ".join(soft)}')
    return report


def render(season, report, notes):
    status = 'FAILING' if report.errors else 'OK'
    lines = [f'## Nightly canary, {season} season: {status}', '']
    lines += [f'- {n}' for n in notes]
    if report.lines():
        lines += ['', '### Findings', ''] + [f'- {line}' for line in report.lines()]
    return '\n'.join(lines) + '\n'


def main(argv=None):
    ap = argparse.ArgumentParser(description='Run the weekly data path as a canary.')
    ap.add_argument('--season', type=int, default=None)
    ap.add_argument('--report', default=None, help='also write the report here')
    args = ap.parse_args(argv)
    season = args.season or current_season()
    report, notes = run(season)
    text = render(season, report, notes)
    print(text)
    if args.report:
        Path(args.report).write_text(text, encoding='utf-8')
    return 0 if report.ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
