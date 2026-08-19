"""
Data loading. Uses nfl_data_py, which reads directly from nflverse's
public GitHub release data -- no manual CSV upload needed. This is what
makes weekly automation possible: a Routine can call load_plays() fresh
every week and get whatever games have completed so far.

Install: pip install nfl_data_py
"""
import pandas as pd
from config import TRAIN_SEASONS


def load_plays(seasons=None):
    """Fetch play-by-play for the given seasons (defaults to TRAIN_SEASONS).
    Returns the raw nflverse play-by-play dataframe, regular season only
    pre-filtered is NOT done here -- callers filter as needed."""
    import nfl_data_py as nfl
    seasons = seasons or TRAIN_SEASONS
    df = nfl.import_pbp_data(seasons, downcast=True)
    return df


def load_schedule(season):
    """Fetch the full schedule (with spread_line etc.) for a season,
    including future/unplayed games -- this is how we get next week's
    matchups and current lines without hardcoding them."""
    import nfl_data_py as nfl
    sched = nfl.import_schedules([season])
    return sched


def load_snap_counts(seasons=None):
    """Fetch player-level snap counts (with position) for the given
    seasons -- used for the O-line continuity feature. Same nflverse
    source as play-by-play, no auth needed."""
    import nfl_data_py as nfl
    seasons = seasons or TRAIN_SEASONS
    df = nfl.import_snap_counts(seasons)
    return df


if __name__ == '__main__':
    # Smoke test -- run this after `pip install nfl_data_py` to confirm
    # network access works in whatever environment this executes in
    # (a Claude Code Routine's cloud environment must have network access
    # enabled for this to succeed).
    df = load_plays([2025])
    print(f"Loaded {len(df)} plays for 2025")
    sched = load_schedule(2026)
    print(f"Loaded {len(sched)} scheduled games for 2026")
    print(sched[sched['week'] == 1][['away_team', 'home_team', 'spread_line']])
