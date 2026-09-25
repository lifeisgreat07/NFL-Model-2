"""
Notice when nflverse changes the shape of its data.

The model reads a dozen play-by-play columns and ten schedule columns
(data_loader.REQUIRED_*_COLS). nflverse renames and adds columns between
releases, and the project has already moved loaders once because of upstream
change (nfl_data_py's deprecation). A dropped column would surface as a
KeyError deep in the weekly run on a Thursday morning; a renamed one could
surface as nothing at all.

So a snapshot of the column names nflverse served is committed in
data/nflverse_schema.json, and the nightly canary compares today's data
against it:

  ERROR    a column the model reads is gone
  WARNING  any other column appeared or disappeared -- not a problem for the
           model, but the earliest sign that a release changed something,
           and the snapshot should be refreshed on purpose (`--update`) once
           someone has looked

Names only, not dtypes. The dtype a column arrives as depends on the pandas
version doing the conversion (pandas 3 reads text as `str` where 2.x said
`object`), so a dtype snapshot would flag the machine rather than the data.

    python src/schema_check.py --season 2026            compare with the snapshot
    python src/schema_check.py --season 2026 --update   rewrite the snapshot
"""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from data_loader import REQUIRED_PBP_COLS, REQUIRED_SCHEDULE_COLS  # noqa: E402
from data_quality import Report  # noqa: E402

SNAPSHOT = Path(__file__).resolve().parent.parent / 'data' / 'nflverse_schema.json'
REQUIRED = {'pbp': REQUIRED_PBP_COLS, 'schedule': REQUIRED_SCHEDULE_COLS}
LABEL = {'pbp': 'play-by-play', 'schedule': 'schedule'}


def columns_of(frames):
    """{'pbp': [...], 'schedule': [...]} from a dict of dataframes."""
    return {name: sorted(str(c) for c in df.columns) for name, df in frames.items()}


def compare(snapshot, current):
    """Today's columns against the committed snapshot."""
    report = Report()
    for name, cols in current.items():
        now = set(cols)
        gone_required = [c for c in REQUIRED[name] if c not in now]
        if gone_required:
            report.errors.append(
                f'{LABEL[name]} no longer has columns the model reads: {gone_required}')
        before = set(snapshot.get(name, []))
        if not before:
            report.warnings.append(f'the snapshot has no {LABEL[name]} columns to compare with')
            continue
        added = sorted(now - before)
        removed = sorted(before - now - set(gone_required))
        if added:
            report.warnings.append(f'{LABEL[name]} gained columns: {added}')
        if removed:
            report.warnings.append(f'{LABEL[name]} lost columns the model does not read: {removed}')
    return report


def load_snapshot(path=SNAPSHOT):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_snapshot(current, path=SNAPSHOT, sources=None):
    payload = {'recorded': date.today().isoformat(), 'sources': sources or {}}
    payload.update(current)
    Path(path).write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')


def fetch_current(season):
    """Columns from the same loads the weekly run and the canary make.

    Play-by-play is read for every season the weekly run asks for, not one:
    the frame nflreadpy returns is the union of each season's columns, so a
    snapshot of one season would report the others' extra columns as "gained"
    every night.
    """
    from config import TRAIN_SEASONS
    from data_loader import load_plays, load_schedule
    seasons = sorted(set(TRAIN_SEASONS) | {season})
    return columns_of({'pbp': load_plays(seasons),
                       'schedule': load_schedule(season)}), seasons


def main(argv=None):
    ap = argparse.ArgumentParser(description='Compare nflverse columns to the snapshot.')
    ap.add_argument('--season', type=int, required=True,
                    help='the target season, as the weekly run uses it')
    ap.add_argument('--update', action='store_true',
                    help='rewrite data/nflverse_schema.json from today')
    args = ap.parse_args(argv)
    current, seasons = fetch_current(args.season)
    if args.update:
        write_snapshot(current, sources={'pbp_seasons': seasons,
                                         'schedule_season': args.season})
        print(f'wrote {SNAPSHOT}')
        return 0
    report = compare(load_snapshot(), current)
    for line in report.lines() or ['no schema changes']:
        print(line)
    return 0 if report.ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
