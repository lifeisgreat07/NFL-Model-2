"""
O-line continuity feature. Validated via backtest (2026-08-19): a real,
small, consistent improvement across all 4 metrics when added to the
existing team+QB model (accuracy +0.11pt, log loss/Brier/AUC all improved
too, on an apples-to-apples same-sample comparison). See METHODOLOGY.md.

Mechanism: an offense's continuity of its starting 5 offensive linemen
week-to-week is a leading indicator of blocking performance, independent
of the linemen's individual talent -- this is a real, established finding
in sports analytics, unlike rest/weather/travel/divisional-game effects
which we tested and rejected the same night.
"""
import pandas as pd

OL_POSITIONS = {'C', 'C/G', 'G', 'G/C', 'G/OT', 'G/T', 'OG', 'OL', 'OT', 'T', 'T/G'}
# Deliberately excludes FB/T -- a fullback occasionally used at tackle in
# short-yardage packages, not a real O-line starter. Including it would
# add noise, not signal.


def compute_ol_continuity_lookup(snap_counts_df):
    """Returns {(team, season, week): continuity_score} where the score is
    how many of that week's starting-5 O-linemen (by offense_snaps) were
    also in the starting 5 the immediately preceding week (same team, same
    season, week-1). Requires TRUE week-adjacency -- bye weeks and season
    openers correctly get no score (None) rather than being compared
    against whatever row happens to sit before them in sorted order.
    """
    ol = snap_counts_df[snap_counts_df['position'].isin(OL_POSITIONS)].copy()
    ol = ol[ol['game_type'] == 'REG']

    rows = []
    for (team, season, week), grp in ol.groupby(['team', 'season', 'week']):
        top5 = grp.nlargest(5, 'offense_snaps')['pfr_player_id'].tolist()
        rows.append({'team': team, 'season': season, 'week': week,
                      'starters': ','.join(sorted(top5))})
    sw = pd.DataFrame(rows)

    starters_lookup = sw.set_index(['team', 'season', 'week'])['starters'].to_dict()

    continuity_lookup = {}
    for (team, season, week), starters in starters_lookup.items():
        prev_key = (team, season, week - 1)
        if prev_key not in starters_lookup:
            continue  # bye week, season opener, or otherwise not truly consecutive
        cur_set = set(starters.split(','))
        prev_set = set(starters_lookup[prev_key].split(','))
        continuity_lookup[(team, season, week)] = len(cur_set & prev_set)

    return continuity_lookup


def get_continuity(lookup, team, season, week, default=None):
    """Look up a team's continuity score for a given week, with an
    explicit, honest default (None or 0) when unavailable -- never
    silently fabricated."""
    return lookup.get((team, season, week), default)


def get_most_recent_continuity(lookup, team, season, before_week, default=0.0):
    """For 'current' predictions: find this team's continuity score from
    the most recent week strictly before `before_week` in this season.
    Falls back to `default` (neutral, 0.0) if nothing found -- e.g. it's
    week 1, or the team was on bye the prior week."""
    candidates = [(w, v) for (t, s, w), v in lookup.items() if t == team and s == season and w < before_week]
    if not candidates:
        return default
    candidates.sort(key=lambda x: x[0])
    return candidates[-1][1]
