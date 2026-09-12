"""Add the schedule's date fields to prediction files written before they existed.

WHY THIS IS ALLOWED TO TOUCH A WRITE-ONCE FILE, stated up front because the
rule it bends is load-bearing.

`predictions/` is write-once by design: weekly_update.py refuses to overwrite
an existing file, and that refusal is what makes "the prediction was saved
before kickoff" a claim anyone can trust. A model output that can be revised
after the game is not a prediction.

`gameday`, `gametime_et` and `weekday` are not model outputs. They are facts
about when a game was scheduled, they come from the same upstream source the
predictions were built against, and they are independently checkable by anyone
with a 2026 schedule. Adding them cannot flatter the model, cannot change a
probability, and cannot alter whether a pick was right.

So the exception is narrow and it is enforced rather than promised:

  * ONLY the three fields are ever written.
  * An existing key is never modified. If one is already present with a
    different value, the file is left alone and the run reports it -- a
    disagreement between a saved record and the schedule is a finding, not
    something to paper over.
  * The join is on (season, week, home, away), which is unique within a week.
    An unmatched record is reported, not guessed at.
  * --check makes no writes at all and exits non-zero if any file would
    change, so CI and the test suite can assert the corpus is settled.

tests/test_backfill_game_dates.py proves the additive property against a copy
rather than trusting this docstring.
"""
import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).parent.parent
PRED_DIR = REPO / 'predictions'

FIELDS = ('gameday', 'gametime_et', 'weekday')


def schedule_lookup(season, load_schedule=None):
    """{(week, home, away): {field: value}} for one season.

    `load_schedule` is injectable so the tests can exercise the join without
    reaching nflverse -- the suite has no network, and a backfill that could
    only be tested by hitting the internet would not be tested.
    """
    if load_schedule is None:
        sys.path.insert(0, str(REPO / 'src'))
        import data_loader
        load_schedule = data_loader.load_schedule

    import pandas as pd
    sched = load_schedule(season)
    out = {}
    for _, g in sched.iterrows():
        key = (int(g['week']), g['home_team'], g['away_team'])
        pick = lambda col: (str(g[col]) if col in sched.columns
                            and pd.notna(g.get(col)) else None)
        out[key] = {'gameday': pick('gameday'),
                    'gametime_et': pick('gametime'),
                    'weekday': pick('weekday')}
    return out


def plan_file(path, lookup):
    """(updated records, notes) for one predictions file. Pure: writes nothing."""
    records = json.loads(path.read_text(encoding='utf-8'))
    notes, changed = [], 0
    for rec in records:
        key = (int(rec['week']), rec['home'], rec['away'])
        found = lookup.get(key)
        if not found:
            notes.append(f"{path.name}: no schedule row for "
                         f"{rec['away']}@{rec['home']} week {rec['week']}")
            continue
        for field in FIELDS:
            value = found[field]
            if field in rec and rec[field] is not None:
                if rec[field] != value:
                    notes.append(
                        f"{path.name}: {rec['away']}@{rec['home']} already has "
                        f"{field}={rec[field]!r} but the schedule says "
                        f"{value!r} -- left alone, this is a finding")
                continue
            if value is None:
                continue
            rec[field] = value
            changed += 1
    return records, changed, notes


def seasons_on_disk():
    seasons = set()
    for path in sorted(PRED_DIR.glob('*_week*.json')):
        seasons.add(int(path.name.split('_')[0]))
    return sorted(seasons)


def run(check_only, load_schedule=None, pred_dir=None):
    """Returns (files_that_would_change, all notes). Writes unless check_only."""
    directory = pred_dir or PRED_DIR
    paths = sorted(directory.glob('*_week*.json'))
    if not paths:
        return [], ['no prediction files found']

    lookups, would_change, notes = {}, [], []
    for path in paths:
        season = int(path.name.split('_')[0])
        if season not in lookups:
            lookups[season] = schedule_lookup(season, load_schedule)
        records, changed, file_notes = plan_file(path, lookups[season])
        notes.extend(file_notes)
        if not changed:
            continue
        would_change.append((path.name, changed))
        if not check_only:
            # Trailing newline and 2-space indent to match what
            # weekly_update.py writes, so the diff is the added keys and
            # nothing else.
            path.write_text(json.dumps(records, indent=2) + '\n',
                            encoding='utf-8')
    return would_change, notes


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--check', action='store_true',
                    help='report what would change and write nothing; exit 1 '
                         'if anything would')
    args = ap.parse_args()

    would_change, notes = run(args.check)
    for note in notes:
        print(f'  NOTE {note}')
    if not would_change:
        print('Every saved prediction already carries its schedule dates.')
        return 0
    verb = 'would gain' if args.check else 'gained'
    for name, count in would_change:
        print(f'  {name}: {count} field(s) {verb}')
    if args.check:
        print('\n--check: nothing was written.')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
