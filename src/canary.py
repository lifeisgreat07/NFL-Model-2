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
  3. the data-quality checks the weekly run enforces (src/data_quality.py)
  4. today's columns against the committed snapshot (src/schema_check.py)
  5. work out the next week to predict, as the weekly run does

A step that raises is recorded as an error and the rest still run, so one
report says everything that is wrong tonight. Exit 1 on any error; the
workflow turns that into an issue (src/alerts.py).

    python src/canary.py [--season 2026] [--report canary-report.md]
"""
import argparse
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from data_quality import Report  # noqa: E402


def current_season(now=None):
    """The season the weekly workflow would run for. Its bash does the same:
    January and February still belong to the season that kicked off the
    previous year."""
    now = now or datetime.now(timezone.utc)
    return now.year - 1 if now.month <= 2 else now.year


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
    from config import TRAIN_SEASONS
    from data_loader import load_plays, load_schedule
    import data_quality
    import schema_check

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
        from weekly_update import determine_next_week
        return f"next week to predict: {determine_next_week(state['season'])}"

    return [('load play-by-play', plays), ('load schedule', schedule),
            ('data quality', quality), ('schema', schema),
            ('next week', next_week)]


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
