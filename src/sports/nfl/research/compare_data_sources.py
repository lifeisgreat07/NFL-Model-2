"""
Value-level comparison between the old (nfl_data_py) and new (nflreadpy)
data sources -- schema/column-name matching (already verified) doesn't
guarantee matching VALUES if there's any subtle processing difference
upstream in how nflverse packages the two libraries' releases.

This is the second half of the USE_NFLREADPY revert path in data_loader.py:
`python -m src.sports.nfl.data_loader` checks every column the project uses is present,
and this script checks the VALUES agree, on 2025 week 10 -- a real,
fully-completed week. It is the evidence behind CLAUDE.md's finding that
nfl_data_py is a verified fallback, and the check to re-run before flipping
the toggle. Needs both libraries installed.

    python -m src.sports.nfl.research.compare_data_sources

Until Stage 31 (the 2026-09-29 re-audit) this ran at import and put the
current directory on sys.path, so it worked only when started from src/ and
importing it fetched a season of play-by-play twice. The re-audit listed it
as dead; it is not dead, it had no entry point.
"""

from src.sports.nfl import data_loader

TEST_SEASON = 2025
TEST_WEEK = 10


def fetch_both(fetch_fn, *args):
    data_loader.USE_NFLREADPY = True
    new = fetch_fn(*args)
    data_loader.USE_NFLREADPY = False
    old = fetch_fn(*args)
    return old, new


def main():
    print(f"=== Comparing schedule data, season {TEST_SEASON} ===")
    old_sched, new_sched = fetch_both(data_loader.load_schedule, TEST_SEASON)
    old_wk = old_sched[old_sched['week'] == TEST_WEEK].sort_values('home_team').reset_index(drop=True)
    new_wk = new_sched[new_sched['week'] == TEST_WEEK].sort_values('home_team').reset_index(drop=True)
    print(f"Old: {len(old_wk)} games, New: {len(new_wk)} games")
    cols = ['home_team', 'away_team', 'home_score', 'away_score', 'spread_line']
    merged = old_wk[cols].merge(new_wk[cols], on=['home_team', 'away_team'], suffixes=('_old', '_new'))
    mismatches = merged[
        (merged['home_score_old'] != merged['home_score_new']) |
        (merged['away_score_old'] != merged['away_score_new']) |
        (merged['spread_line_old'].round(1) != merged['spread_line_new'].round(1))
    ]
    print(f"Games with ANY value mismatch: {len(mismatches)} of {len(merged)}")
    if len(mismatches):
        print(mismatches)
    else:
        print("PASS -- scores and spread lines identical between sources.")

    print(f"\n=== Comparing play-by-play, season {TEST_SEASON} week {TEST_WEEK} ===")
    old_pbp, new_pbp = fetch_both(data_loader.load_plays, [TEST_SEASON])
    old_wk_pbp = old_pbp[(old_pbp['season_type'] == 'REG') & (old_pbp['week'] == TEST_WEEK) &
                         ((old_pbp['pass'] == 1) | (old_pbp['rush'] == 1)) & (old_pbp['epa'].notna())]
    new_wk_pbp = new_pbp[(new_pbp['season_type'] == 'REG') & (new_pbp['week'] == TEST_WEEK) &
                         ((new_pbp['pass'] == 1) | (new_pbp['rush'] == 1)) & (new_pbp['epa'].notna())]
    print(f"Old: {len(old_wk_pbp)} plays, New: {len(new_wk_pbp)} plays")
    print(f"Old avg EPA: {old_wk_pbp['epa'].mean():.5f}")
    print(f"New avg EPA: {new_wk_pbp['epa'].mean():.5f}")
    diff = abs(old_wk_pbp['epa'].mean() - new_wk_pbp['epa'].mean())
    print(f"Difference: {diff:.6f} -- {'PASS (negligible)' if diff < 0.001 else 'INVESTIGATE -- real difference found'}")

    print(f"\n=== Comparing snap counts, season {TEST_SEASON} week {TEST_WEEK} ===")
    old_snaps, new_snaps = fetch_both(data_loader.load_snap_counts, [TEST_SEASON])
    old_wk_snaps = old_snaps[(old_snaps['season'] == TEST_SEASON) & (old_snaps['week'] == TEST_WEEK) & (old_snaps['game_type'] == 'REG')]
    new_wk_snaps = new_snaps[(new_snaps['season'] == TEST_SEASON) & (new_snaps['week'] == TEST_WEEK) & (new_snaps['game_type'] == 'REG')]
    print(f"Old: {len(old_wk_snaps)} rows, New: {len(new_wk_snaps)} rows")
    print(f"Old total offense_snaps: {old_wk_snaps['offense_snaps'].sum()}")
    print(f"New total offense_snaps: {new_wk_snaps['offense_snaps'].sum()}")

    print("\n=== SUMMARY ===")
    print("If all three sections show PASS/identical, the loaders agree and the toggle is safe to flip.")
    print("If any show a real difference, report the exact numbers back before flipping it.")


if __name__ == '__main__':
    main()
