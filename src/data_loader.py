"""
Data loading. Migrated 2026-08 from nfl_data_py to nflreadpy -- nfl_data_py
was officially deprecated by nflverse ("No further maintenance or updates
are planned"), discovered during a routine production-safety check, not
because of any actual failure. nflreadpy is the actively-maintained
successor with a confirmed 1:1 function mapping for everything we use:
  import_pbp_data()   -> load_pbp()
  import_schedules()  -> load_schedules()
  import_snap_counts() -> load_snap_counts()

The one real difference: nflreadpy returns Polars DataFrames, not pandas.
Converted immediately via .to_pandas() so every downstream module
(ratings_engine.py, weekly_update.py, ol_continuity.py, backtest.py)
keeps working completely unchanged -- they were never touched, and don't
need to be.

USE_NFLREADPY below is a deliberate safety toggle, not just a comment.
If nflreadpy's schema drifts or breaks something, set it to False to
revert to the old, still-installable nfl_data_py path with zero other
code changes -- while nfl_data_py still works today, it just won't get
fixed if something breaks later. This is intentionally NOT a silent
try/except fallback: a real fetch failure should fail loudly (per this
project's own data-quality rule: "the pipeline should fail loudly when
critical data is wrong rather than silently generating unreliable
predictions"), not quietly degrade to a different data source that
might have subtly different values.

Before flipping USE_NFLREADPY to False<->True in production, run this
file directly (python data_loader.py) to verify every column this
project actually depends on is present -- see the checklist in
__main__ below, compiled directly from grepping the codebase's real
column usage, not assumed.

Install: pip install nflreadpy   (or: pip install nfl_data_py, if reverting)
"""
import pandas as pd
from config import TRAIN_SEASONS

USE_NFLREADPY = True  # flip to False to revert to nfl_data_py -- see docstring


def load_plays(seasons=None):
    """Fetch play-by-play for the given seasons (defaults to TRAIN_SEASONS).
    Returns the raw nflverse play-by-play dataframe, regular season only
    pre-filtered is NOT done here -- callers filter as needed."""
    seasons = seasons or TRAIN_SEASONS
    if USE_NFLREADPY:
        import nflreadpy as nfl
        df = nfl.load_pbp(seasons)
        return df.to_pandas()
    else:
        import nfl_data_py as nfl
        return nfl.import_pbp_data(seasons, downcast=True)


def load_schedule(season):
    """Fetch the full schedule (with spread_line etc.) for a season,
    including future/unplayed games -- this is how we get next week's
    matchups and current lines without hardcoding them."""
    if USE_NFLREADPY:
        import nflreadpy as nfl
        sched = nfl.load_schedules(season)
        return sched.to_pandas()
    else:
        import nfl_data_py as nfl
        return nfl.import_schedules([season])


def load_snap_counts(seasons=None):
    """Fetch player-level snap counts (with position) for the given
    seasons -- used for the O-line continuity feature. Same nflverse
    source as play-by-play, no auth needed."""
    seasons = seasons or TRAIN_SEASONS
    if USE_NFLREADPY:
        import nflreadpy as nfl
        df = nfl.load_snap_counts(seasons)
        return df.to_pandas()
    else:
        import nfl_data_py as nfl
        return nfl.import_snap_counts(seasons)


if __name__ == '__main__':
    # Real verification, not a vague smoke test -- checks every column
    # this project's actual code depends on, compiled by grepping the
    # real usage in ratings_engine.py, weekly_update.py, ol_continuity.py.
    # Run this BEFORE trusting USE_NFLREADPY=True in production.
    REQUIRED_PBP_COLS = ['posteam', 'defteam', 'epa', 'pass', 'rush', 'season_type',
                          'week', 'season', 'qb_dropback', 'qb_epa',
                          'passer_player_id', 'passer_player_name']
    REQUIRED_SCHEDULE_COLS = ['home_team', 'away_team', 'home_score', 'away_score',
                               'spread_line', 'week', 'season', 'gameday']
    REQUIRED_SNAP_COLS = ['team', 'season', 'week', 'position', 'offense_snaps',
                           'pfr_player_id', 'game_type']

    def check(df, required, label):
        missing = [c for c in required if c not in df.columns]
        if missing:
            print(f"  [FAIL] {label}: MISSING columns: {missing}")
            return False
        print(f"  [PASS] {label}: all {len(required)} required columns present")
        return True

    print(f"Testing with USE_NFLREADPY={USE_NFLREADPY}\n")

    print("Fetching play-by-play (2025)...")
    pbp = load_plays([2025])
    print(f"  {len(pbp)} rows")
    ok1 = check(pbp, REQUIRED_PBP_COLS, "play-by-play")

    print("\nFetching schedule (2026)...")
    sched = load_schedule(2026)
    print(f"  {len(sched)} rows")
    ok2 = check(sched, REQUIRED_SCHEDULE_COLS, "schedule")
    week1 = sched[sched['week'] == 1]
    if len(week1):
        print(week1[['away_team', 'home_team', 'spread_line']].head(3))

    print("\nFetching snap counts (2025)...")
    snaps = load_snap_counts([2025])
    print(f"  {len(snaps)} rows")
    ok3 = check(snaps, REQUIRED_SNAP_COLS, "snap counts")

    print(f"\n{'ALL CHECKS PASSED' if (ok1 and ok2 and ok3) else 'SOME CHECKS FAILED -- do not deploy until fixed'}")
