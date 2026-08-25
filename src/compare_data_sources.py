"""
Value-level comparison between the old (nfl_data_py) and new (nflreadpy)
data sources -- schema/column-name matching (already verified) doesn't
guarantee matching VALUES if there's any subtle processing difference
upstream in how nflverse packages the two libraries' releases.

Run this from inside src/ after both nfl_data_py and nflreadpy are
installed. Uses 2025 Week 10 -- a real, fully-completed week we already
have historical predictions for from much earlier in this project.
"""
import sys
sys.path.insert(0, '.')
import data_loader

TEST_SEASON = 2025
TEST_WEEK = 10

def fetch_both(fetch_fn, *args):
    data_loader.USE_NFLREADPY = True
    new = fetch_fn(*args)
    data_loader.USE_NFLREADPY = False
    old = fetch_fn(*args)
    return old, new

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
old_wk_pbp = old_pbp[(old_pbp['season_type']=='REG') & (old_pbp['week']==TEST_WEEK) &
                      ((old_pbp['pass']==1)|(old_pbp['rush']==1)) & (old_pbp['epa'].notna())]
new_wk_pbp = new_pbp[(new_pbp['season_type']=='REG') & (new_pbp['week']==TEST_WEEK) &
                      ((new_pbp['pass']==1)|(new_pbp['rush']==1)) & (new_pbp['epa'].notna())]
print(f"Old: {len(old_wk_pbp)} plays, New: {len(new_wk_pbp)} plays")
print(f"Old avg EPA: {old_wk_pbp['epa'].mean():.5f}")
print(f"New avg EPA: {new_wk_pbp['epa'].mean():.5f}")
diff = abs(old_wk_pbp['epa'].mean() - new_wk_pbp['epa'].mean())
print(f"Difference: {diff:.6f} -- {'PASS (negligible)' if diff < 0.001 else 'INVESTIGATE -- real difference found'}")

print(f"\n=== Comparing snap counts, season {TEST_SEASON} week {TEST_WEEK} ===")
old_snaps, new_snaps = fetch_both(data_loader.load_snap_counts, [TEST_SEASON])
old_wk_snaps = old_snaps[(old_snaps['season']==TEST_SEASON) & (old_snaps['week']==TEST_WEEK) & (old_snaps['game_type']=='REG')]
new_wk_snaps = new_snaps[(new_snaps['season']==TEST_SEASON) & (new_snaps['week']==TEST_WEEK) & (new_snaps['game_type']=='REG')]
print(f"Old: {len(old_wk_snaps)} rows, New: {len(new_wk_snaps)} rows")
print(f"Old total offense_snaps: {old_wk_snaps['offense_snaps'].sum()}")
print(f"New total offense_snaps: {new_wk_snaps['offense_snaps'].sum()}")

print("\n=== SUMMARY ===")
print("If all three sections show PASS/identical, the migration is safe to merge to main.")
print("If any show a real difference, report the exact numbers back before merging.")
