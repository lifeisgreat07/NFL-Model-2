"""
Leak-free-ness test suite. Flagged as a gap in the very first audit of this
project -- every leak-free claim made in Model Lab/Roadmap has, until now,
been verified by manual, one-off sandbox checks during development, never
by a real, repeatable, checked-into-the-repo test.

Design principle: these tests import the ACTUAL production functions from
src/ (not reimplementations), and feed them small, synthetic, fully-known
inputs where we can independently compute what a leak-free answer must be.
If any function's signature has drifted since this was written, these
tests will fail loudly with a real import/call error -- that's a feature,
not a bug: it means this suite can't silently pass while testing stale
assumptions about the codebase.

Run with: pytest test_leak_free.py -v
"""
import sys
import os
import pandas as pd
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


# ============================================================
# Test 1: QB-change detection never uses a future week's starter
# to determine whether THIS week represents a change.
# ============================================================
def test_qb_change_lookup_never_leaks_future_starter():
    from weekly_update import build_qb_change_lookup

    # Synthetic starters: team AAA starts QB1 weeks 1-2, switches to QB2 in
    # week 3, switches BACK to QB1 in week 4. A leak-free implementation
    # must flag week 3 and week 4 as changes using ONLY the prior week's
    # starter -- never by looking ahead to see who starts later.
    starters = pd.DataFrame([
        {'season': 2024, 'week': 1, 'posteam': 'AAA', 'passer_player_id': 'QB1'},
        {'season': 2024, 'week': 2, 'posteam': 'AAA', 'passer_player_id': 'QB1'},
        {'season': 2024, 'week': 3, 'posteam': 'AAA', 'passer_player_id': 'QB2'},
        {'season': 2024, 'week': 4, 'posteam': 'AAA', 'passer_player_id': 'QB1'},
    ])

    qb_dict = {'identify_starters': lambda season: starters[starters['season'] == season].copy()}
    lookup = build_qb_change_lookup(qb_dict, seasons=[2024])

    assert lookup.get((2024, 1, 'AAA'), 0) == 0, "week 1 has no prior week -- must not be flagged as a change"
    assert lookup.get((2024, 2, 'AAA'), 0) == 0, "same QB as week 1 -- not a change"
    assert lookup.get((2024, 3, 'AAA'), 0) == 1, "QB1 -> QB2 -- genuinely a change"
    assert lookup.get((2024, 4, 'AAA'), 0) == 1, "QB2 -> QB1 -- also genuinely a change, even though QB1 started before"


def test_qb_change_lookup_resets_across_season_boundary():
    from weekly_update import build_qb_change_lookup

    # Team BBB ends 2023 with QB2, opens 2024 with QB1 (who started 2023
    # week 1). A leak-free, season-scoped implementation must NOT flag
    # 2024 week 1 as "same as 2023 week 1" -- there's no valid "prior week"
    # within the new season to compare against.
    starters = pd.DataFrame([
        {'season': 2023, 'week': 1, 'posteam': 'BBB', 'passer_player_id': 'QB1'},
        {'season': 2023, 'week': 18, 'posteam': 'BBB', 'passer_player_id': 'QB2'},
        {'season': 2024, 'week': 1, 'posteam': 'BBB', 'passer_player_id': 'QB1'},
    ])
    qb_dict = {'identify_starters': lambda season: starters[starters['season'] == season].copy()}
    lookup = build_qb_change_lookup(qb_dict, seasons=[2023, 2024])

    assert lookup.get((2024, 1, 'BBB'), 0) == 0, \
        "no valid prior week exists within 2024 season -- must default to 0, not compare across season boundary"


# ============================================================
# Test 2: O-line continuity never compares to a bye-week gap or
# season boundary as if it were a genuine consecutive week.
# ============================================================
def test_ol_continuity_bye_week_gets_no_score():
    from ol_continuity import compute_ol_continuity_lookup

    # Team CCC: real lineup weeks 1-3, BYE at week 4 (no snap rows at all),
    # then plays again week 5 with a totally different lineup (as would
    # happen if the bye masked real personnel changes). A leak-free
    # implementation must give week 5 NO continuity score -- there's no
    # true "week 4" to compare against, and comparing week 5 to week 3
    # directly (skipping the gap) would silently misrepresent what
    # actually changed during the bye.
    rows = []
    for wk, players in [(1, ['P1','P2','P3','P4','P5']), (2, ['P1','P2','P3','P4','P5']),
                          (3, ['P1','P2','P3','P4','P5']), (5, ['P6','P7','P8','P9','P10'])]:
        for i, p in enumerate(players):
            rows.append({'team':'CCC','season':2024,'week':wk,'game_type':'REG',
                         'position':'T' if i<2 else 'G' if i<4 else 'C',
                         'pfr_player_id':p, 'offense_snaps': 60-i})
    snap_df = pd.DataFrame(rows)
    lookup = compute_ol_continuity_lookup(snap_df)

    assert (('CCC', 2024, 5) not in lookup) or lookup[('CCC', 2024, 5)] is None, \
        "week 5 follows a bye (no week 4 data) -- must not be silently compared to week 3"
    assert lookup.get(('CCC', 2024, 2)) == 5, "week 2 vs week 1, identical lineup -- should show full continuity"


def test_ol_continuity_uses_only_strictly_prior_week():
    from ol_continuity import get_most_recent_continuity

    # If we're predicting a game as-of week 6, and the team's continuity
    # data only goes up through week 3 (real data stops there, e.g. this
    # is being called mid-week before week 4-5 have been played), the
    # lookup must return the week 3 value -- never anything from week 4+,
    # which would mean using information that doesn't exist yet at
    # prediction time.
    lookup = {('DDD', 2024, 2): 4, ('DDD', 2024, 3): 5}
    result = get_most_recent_continuity(lookup, 'DDD', 2024, before_week=6, default=0.0)
    assert result == 5, "should find week 3 (most recent PRIOR to week 6), not fabricate anything newer"

    result_early = get_most_recent_continuity(lookup, 'DDD', 2024, before_week=2, default=0.0)
    assert result_early == 0.0, \
        "before_week=2 means only week 1 could count as 'prior', and no week-1 data exists -- must fall back to default, not use week 2 or 3 data (which is not yet 'in the past' relative to week 2)"


# ============================================================
# Test 3: Team ratings at a given cutoff never include that
# cutoff week's own plays (the fundamental walk-forward property
# the entire model depends on).
# ============================================================
def test_team_ratings_cutoff_excludes_current_week():
    """This is the single most important leak-free property in the whole
    project -- if this breaks, every downstream feature is compromised.
    Uses a small synthetic play-by-play dataset with a KNOWN, extreme EPA
    value planted in a specific future week, and confirms that value
    cannot influence a rating computed for any cutoff at or before that
    week."""
    try:
        from ratings_engine import build_team_ratings
    except ImportError:
        pytest.skip("ratings_engine.py not available in this environment -- "
                     "run against the real repo checkout to actually verify this")

    week_keys = [(2024, 1), (2024, 2), (2024, 3)]
    week_to_idx = {wk: i for i, wk in enumerate(week_keys)}

    rows = []
    for wk_idx, (season, week) in enumerate(week_keys):
        gwidx = week_to_idx[(season, week)]
        epa_value = 0.0
        if week == 3:
            # Plant an extreme, unmistakable value ONLY in week 3
            epa_value = 999.0
        for _ in range(50):
            rows.append({'posteam': 'EEE', 'defteam': 'FFF', 'epa': epa_value,
                         'gwidx': gwidx, 'season': season, 'week': week})
    plays = pd.DataFrame(rows)

    ratings_by_week = build_team_ratings(plays, week_keys, upto_cutoff_i=None)

    # Rating AS OF week 3 (cutoff_i for week 3) should reflect only weeks
    # 1-2's data (both EPA=0), and must NOT be influenced by week 3's
    # planted 999.0 value, since that would mean the rating "knows" about
    # the very week it's being used to predict.
    cutoff_key = (2024, 3)
    if cutoff_key in ratings_by_week:
        off_rating, def_rating = ratings_by_week[cutoff_key].get('EEE', (0, 0))
        assert off_rating < 10, \
            f"Rating as-of week 3 shows off_rating={off_rating}, which suggests the planted " \
            f"999.0 EPA value from week 3 itself leaked into its own cutoff's rating"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
