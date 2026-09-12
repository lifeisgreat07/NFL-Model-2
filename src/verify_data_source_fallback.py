"""
Re-execute the claim that nfl_data_py is still a working fallback.

data_loader.py's docstring says USE_NFLREADPY can be flipped to False to
"revert to the old, still-installable nfl_data_py path with zero other code
changes -- while nfl_data_py still works today". That is a present-tense claim
about a code path nothing exercises: every run, every test and every backtest
goes through nflreadpy. VERIFICATION.md is explicit that a claim about repo
state needs re-executed evidence, and this one has never been re-executed
since the migration.

It also has a live cost. requirements.txt is pinned to pandas 1.5.3 and numpy
1.26.4 for one reason: nfl_data_py 0.3.3 requires pandas<2.0 and numpy<2.0.
nflreadpy needs neither -- it returns Polars and treats pandas as optional. So
the fallback is what holds the whole project on the 1.x line, and "is it a
real fallback or cruft" is the question that decides whether pandas 2.x/3.x is
even available to consider.

Deliberately answers the cheap question first. If the fallback does not work,
there is nothing to trade off and no pandas experiment to run -- the revert
path is fiction and the pin is being paid for nothing. Only if it DOES work is
there a real decision, and only then is a backtest warranted.

Three things are checked, in increasing strength:

  1. Does it import and fetch at all?
  2. Does it carry every column this project actually depends on? (The same
     lists data_loader.py's __main__ uses, compiled from real usage.)
  3. Does it return the SAME VALUES as nflreadpy for the same games? A
     fallback that returns different numbers is not a fallback -- flipping to
     it would silently move the model, which is the failure mode the loud-fail
     rule in data_loader.py's own docstring exists to prevent.

Usage: python src/verify_data_source_fallback.py
Writes data/data_source_fallback.json and prints a verdict.
Needs network. Run it on a machine with nflverse access, not in CI.
"""
import json
import sys
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import data_loader

DATA_DIR = Path(__file__).parent.parent / 'data'

# The season and week the 2026-08 migration used for its own value comparison.
# Reusing it deliberately: if the two sources agreed here then and disagree
# now, that is the finding.
COMPARE_SEASON = 2025
COMPARE_WEEK = 10

REQUIRED_PBP_COLS = ['posteam', 'defteam', 'epa', 'pass', 'rush', 'season_type',
                     'week', 'season', 'qb_dropback', 'qb_epa',
                     'passer_player_id', 'passer_player_name']
# Keep in step with the list in src/data_loader.py's __main__ block. Two
# copies of the same required-columns list is the duplication this repo keeps
# getting bitten by, so tests/test_game_datetime_fields.py asserts they agree
# rather than trusting this comment to be read.
REQUIRED_SCHEDULE_COLS = ['home_team', 'away_team', 'home_score', 'away_score',
                          'spread_line', 'week', 'season', 'gameday',
                          'gametime', 'weekday']
REQUIRED_SNAP_COLS = ['team', 'season', 'week', 'position', 'offense_snaps',
                      'pfr_player_id', 'game_type']


def _with_source(use_nflreadpy, fn, *args, **kwargs):
    """Run a loader with the toggle forced, then always put it back.

    Sets the module attribute rather than editing the file: the committed
    value of USE_NFLREADPY is production configuration, and a script that
    leaves it flipped would be a far worse bug than the one it is checking.
    """
    original = data_loader.USE_NFLREADPY
    try:
        data_loader.USE_NFLREADPY = use_nflreadpy
        return fn(*args, **kwargs)
    finally:
        data_loader.USE_NFLREADPY = original


def _attempt(label, use_nflreadpy, fn, *args, **kwargs):
    """Returns (dataframe or None, error string or None). Never raises --
    a fallback that raises is the answer, not a crash to be fixed."""
    try:
        df = _with_source(use_nflreadpy, fn, *args, **kwargs)
        print(f"  {label}: {len(df)} rows")
        return df, None
    except Exception as e:
        detail = f"{type(e).__name__}: {e}"
        print(f"  {label}: FAILED -- {detail}")
        return None, detail


def check_columns(df, required, label):
    missing = [c for c in required if c not in df.columns]
    if missing:
        print(f"    [FAIL] {label}: missing {missing}")
    else:
        print(f"    [PASS] {label}: all {len(required)} required columns present")
    return missing


def compare_schedule_values(old, new):
    """The strongest of the three checks: same games, same numbers?

    Compared on the join key rather than by position -- two sources can agree
    completely and still order their rows differently, and a positional
    comparison would report that as a total mismatch.
    """
    keys = ['season', 'week', 'home_team', 'away_team']
    fields = ['home_score', 'away_score', 'spread_line']

    o = old[old['week'] == COMPARE_WEEK][keys + fields].copy()
    n = new[new['week'] == COMPARE_WEEK][keys + fields].copy()
    merged = o.merge(n, on=keys, how='outer', suffixes=('_old', '_new'), indicator=True)

    only_old = int((merged['_merge'] == 'left_only').sum())
    only_new = int((merged['_merge'] == 'right_only').sum())
    both = merged[merged['_merge'] == 'both']

    mismatches = {}
    for f in fields:
        a, b = both[f + '_old'], both[f + '_new']
        # NaN == NaN must count as agreement: an unplayed game has no score in
        # either source, and treating that as a difference would report every
        # future fixture as a mismatch.
        differs = ~((a == b) | (a.isna() & b.isna()))
        if differs.any():
            rows = both.loc[differs, keys + [f + '_old', f + '_new']]
            mismatches[f] = rows.head(5).to_dict(orient='records')
        print(f"    {f}: {int(differs.sum())} of {len(both)} games differ")

    return {
        'games_compared': int(len(both)),
        'only_in_nfl_data_py': only_old,
        'only_in_nflreadpy': only_new,
        'mismatched_fields': mismatches,
        'values_agree': not mismatches and only_old == 0 and only_new == 0,
    }


def main():
    result = {
        'compare_season': COMPARE_SEASON,
        'compare_week': COMPARE_WEEK,
        'pandas': pd.__version__,
        'numpy': np.__version__,
        'committed_use_nflreadpy': data_loader.USE_NFLREADPY,
    }

    print("1. Can nfl_data_py even be imported?")
    try:
        import nfl_data_py
        result['importable'] = True
        print(f"  imported OK ({getattr(nfl_data_py, '__version__', 'version not reported')})")
    except Exception as e:
        result['importable'] = False
        result['import_error'] = f"{type(e).__name__}: {e}"
        print(f"  FAILED -- {result['import_error']}")
        print("\nVERDICT: CRUFT. The fallback cannot even be imported, so the "
              "revert path documented in data_loader.py does not exist.")
        result['verdict'] = 'CRUFT -- not importable'
        _save(result)
        return

    print(f"\n2. Does each loader work through nfl_data_py? (season {COMPARE_SEASON})")
    old_sched, e_sched = _attempt('schedule   ', False, data_loader.load_schedule, COMPARE_SEASON)
    old_pbp,   e_pbp   = _attempt('play-by-play', False, data_loader.load_plays, [COMPARE_SEASON])
    old_snaps, e_snaps = _attempt('snap counts ', False, data_loader.load_snap_counts, [COMPARE_SEASON])

    result['loader_errors'] = {'schedule': e_sched, 'plays': e_pbp, 'snap_counts': e_snaps}
    failed = [k for k, v in result['loader_errors'].items() if v]

    print("\n3. Are the columns this project depends on present?")
    missing = {}
    if old_pbp is not None:
        missing['plays'] = check_columns(old_pbp, REQUIRED_PBP_COLS, 'play-by-play')
    if old_sched is not None:
        missing['schedule'] = check_columns(old_sched, REQUIRED_SCHEDULE_COLS, 'schedule')
    if old_snaps is not None:
        missing['snap_counts'] = check_columns(old_snaps, REQUIRED_SNAP_COLS, 'snap counts')
    result['missing_columns'] = {k: v for k, v in missing.items() if v}

    if failed:
        result['verdict'] = f"CRUFT -- loader(s) failed: {', '.join(failed)}"
        print(f"\nVERDICT: CRUFT. {', '.join(failed)} raised through the fallback path, "
              f"so flipping USE_NFLREADPY to False would not revert anything -- it "
              f"would break the pipeline.")
        _save(result)
        return

    print(f"\n4. Do the two sources agree on real values? (week {COMPARE_WEEK})")
    new_sched, e_new = _attempt('nflreadpy schedule', True, data_loader.load_schedule, COMPARE_SEASON)
    if new_sched is None:
        result['verdict'] = 'INCONCLUSIVE -- the live source failed, not the fallback'
        result['loader_errors']['nflreadpy_schedule'] = e_new
        print("\nVERDICT: INCONCLUSIVE. nflreadpy itself failed, so there is "
              "nothing to compare the fallback against.")
        _save(result)
        return

    result['comparison'] = compare_schedule_values(old_sched, new_sched)

    if result['missing_columns']:
        result['verdict'] = 'PARTIAL -- works but is missing columns this project uses'
    elif not result['comparison']['values_agree']:
        result['verdict'] = 'NOT A SAFE FALLBACK -- works but returns different values'
    else:
        result['verdict'] = 'REAL FALLBACK -- imports, loads, and agrees with nflreadpy'

    print(f"\nVERDICT: {result['verdict']}")
    if result['verdict'].startswith('REAL'):
        print("\nSo the pandas pin is buying something real, and dropping "
              "nfl_data_py is a genuine trade-off rather than hygiene. That "
              "makes the pandas 2.x/3.x unlock a real experiment: tune on "
              "2022-2023, confirm on 2024-2025, judge on log loss / Brier / "
              "AUC, never accuracy.")
    else:
        print("\nSo the pin on pandas<2.0 and numpy<2.0 is being paid for a "
              "revert path that does not work. Dropping nfl_data_py costs "
              "nothing that currently exists.")
    _save(result)


def _save(result):
    DATA_DIR.mkdir(exist_ok=True)
    out = DATA_DIR / 'data_source_fallback.json'
    with open(out, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\nSaved to {out}")


if __name__ == '__main__':
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
