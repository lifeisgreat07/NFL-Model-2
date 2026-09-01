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

Consolidated 2026-09-01 from two independently-written suites that landed
in parallel (one here, one on a separate branch): kept both of this file's
original QB-change-lookup tests (the other suite never covered that code
path at all), replaced this file's OL-continuity/team-ratings tests with
the other suite's stronger versions (exact mutate-and-diff equality checks
instead of "plant one extreme value and assert the result looks
reasonable"), and added the other suite's QB-rating shrinkage-target leak
test, which doesn't exist here at all and is the one that actually caught
a real bug (see ratings_engine.py). Also fixed this file's sys.path setup,
which pointed at a nonexistent tests/src and made every real import here
fail silently down to a skip -- confirmed by actually running it.

Run with: pytest tests/test_leak_free.py -v
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


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
# Test 2: team ratings at a given cutoff never include that
# cutoff week's own plays (the fundamental walk-forward property
# the entire model depends on).
# ============================================================
def _synthetic_team_plays(rng, n_week0=260, n_week1=40):
    """gwidx=0 is the only week that should ever feed a cutoff_i=1 fit;
    gwidx=1 is 'the future' relative to that cutoff and must never leak in."""
    teams = ["AAA", "BBB", "CCC", "DDD"]

    def make_week(n, gwidx, epa_fn):
        off = rng.choice(teams, size=n)
        deft = np.array([rng.choice([t for t in teams if t != o]) for o in off])
        epa = epa_fn(n)
        return pd.DataFrame({"posteam": off, "defteam": deft, "epa": epa, "gwidx": gwidx})

    week0 = make_week(n_week0, 0, lambda n: rng.normal(0, 1.5, size=n))
    week1 = make_week(n_week1, 1, lambda n: rng.normal(0, 1.5, size=n))
    plays = pd.concat([week0, week1], ignore_index=True)
    week_keys = [(2023, 1), (2023, 2)]
    return plays, week_keys


def test_team_ratings_cutoff_excludes_current_week():
    """This is the single most important leak-free property in the whole
    project -- if this breaks, every downstream feature is compromised.
    Proof: mutate the cutoff week's own data into something wildly
    different and confirm the rating computed *as of* that cutoff doesn't
    move at all -- a stronger check than "the rating still looks
    reasonable," since even a real leak can produce a plausible-looking
    number."""
    from ratings_engine import build_team_ratings
    from config import MIN_PLAYS_FOR_RATING

    rng = np.random.default_rng(42)
    plays, week_keys = _synthetic_team_plays(rng, n_week0=260, n_week1=40)
    assert (plays["gwidx"] == 0).sum() >= MIN_PLAYS_FOR_RATING

    before = build_team_ratings(plays, week_keys, upto_cutoff_i=1)
    assert before is not None

    mutated = plays.copy()
    mutated.loc[mutated["gwidx"] == 1, "epa"] = 500.0  # absurd outlier, week-1 (the cutoff week) only
    after = build_team_ratings(mutated, week_keys, upto_cutoff_i=1)

    assert before.keys() == after.keys()
    for team in before:
        assert before[team] == after[team], f"{team} rating changed when only cutoff-week data was mutated -- leak"


# ============================================================
# Test 3: the QB rating's shrinkage target must be scoped to the
# same cutoff as everything else -- this is the actual bug this
# suite caught (see ratings_engine.py): league_avg was computed
# once over the whole input, silently leaking future weeks into
# every "as of" prediction's shrinkage anchor.
# ============================================================
def test_qb_rating_cutoff_excludes_current_week():
    """Same leak-free property as team ratings, but for build_qb_ratings'
    trailing_rating closure: prior plays AND the shrinkage target must
    both satisfy gwidx < cutoff_gwidx."""
    from ratings_engine import build_qb_ratings

    rng = np.random.default_rng(7)
    n_week0, n_week1 = 30, 10
    week0 = pd.DataFrame({
        "season": 2023, "week": 1, "season_type": "REG", "posteam": "AAA",
        "qb_dropback": 1, "qb_epa": rng.normal(0, 1, size=n_week0),
        "passer_player_id": "QB1", "passer_player_name": "Test QB",
    })
    week1 = pd.DataFrame({
        "season": 2023, "week": 2, "season_type": "REG", "posteam": "AAA",
        "qb_dropback": 1, "qb_epa": rng.normal(0, 1, size=n_week1),
        "passer_player_id": "QB1", "passer_player_name": "Test QB",
    })
    raw_pbp = pd.concat([week0, week1], ignore_index=True)

    ctx = build_qb_ratings(raw_pbp)
    cutoff_gwidx_for_week2 = ctx["week_to_idx"][(2023, 2)]  # rating "as of" week 2, i.e. before week 2's own plays
    before = ctx["trailing_rating"]("QB1", cutoff_gwidx_for_week2)

    mutated_pbp = raw_pbp.copy()
    mutated_pbp.loc[mutated_pbp["week"] == 2, "qb_epa"] = 500.0
    ctx_mutated = build_qb_ratings(mutated_pbp)
    after = ctx_mutated["trailing_rating"]("QB1", cutoff_gwidx_for_week2)

    assert before == after, "trailing_rating changed when only the cutoff week's own plays were mutated -- leak"


# ============================================================
# Test 4: O-line continuity never compares to a bye-week gap or
# season boundary as if it were a genuine consecutive week, and
# respects the REG-season game_type filter.
# ============================================================
def _snap_row(team, season, week, player, snaps, position="OT", game_type="REG"):
    return {
        "team": team, "season": season, "week": week, "game_type": game_type,
        "position": position, "pfr_player_id": player, "offense_snaps": snaps,
    }


def test_ol_continuity_bye_week_gets_no_score():
    """Team AAA plays weeks 1, 2, then 4 (bye in week 3). Week 2 should get
    a real continuity score against week 1. Week 4 must get NO score at all
    (excluded from the lookup) rather than being silently compared against
    week 2's lineup just because it's the next row in sorted order."""
    from ol_continuity import compute_ol_continuity_lookup

    starters = ["L1", "L2", "L3", "L4", "L5"]
    rows = []
    for wk in (1, 2, 4):
        for i, p in enumerate(starters):
            rows.append(_snap_row("AAA", 2023, wk, p, snaps=60 - i))
        # a 6th OL body with fewer snaps -- must not displace the top-5
        rows.append(_snap_row("AAA", 2023, wk, "BENCH", snaps=5))
    # a QB row -- must never be treated as an OL starter
    for wk in (1, 2, 4):
        rows.append(_snap_row("AAA", 2023, wk, "QB1", snaps=65, position="QB"))
    # a second team with a real week 3, proving the lookup is keyed per-team
    # and doesn't let AAA borrow BBB's week-3 adjacency
    for p in starters:
        rows.append(_snap_row("BBB", 2023, 3, p, snaps=50))

    snap_counts = pd.DataFrame(rows)
    lookup = compute_ol_continuity_lookup(snap_counts)

    assert lookup[("AAA", 2023, 2)] == 5  # identical top-5 vs week 1 -> full continuity
    assert ("AAA", 2023, 4) not in lookup  # week 3 (prev) doesn't exist for AAA -> no score, not compared to week 2
    assert ("AAA", 2023, 1) not in lookup  # season opener -> no prior week to compare


def test_ol_continuity_respects_game_type_filter():
    """A POST-season row for the 'previous' week number must not be treated
    as a real adjacency for REG-season continuity."""
    from ol_continuity import compute_ol_continuity_lookup

    starters = ["L1", "L2", "L3", "L4", "L5"]
    rows = []
    for p in starters:
        rows.append(_snap_row("AAA", 2023, 18, p, snaps=60, game_type="POST"))
        rows.append(_snap_row("AAA", 2023, 19, p, snaps=60, game_type="REG"))
    snap_counts = pd.DataFrame(rows)
    lookup = compute_ol_continuity_lookup(snap_counts)
    assert ("AAA", 2023, 19) not in lookup  # week 18 was POST, filtered out before the adjacency check


# ============================================================
# Test 5: continuity lookup helpers never fabricate or leak a
# value the caller shouldn't have yet.
# ============================================================
def test_most_recent_continuity_boundary_excludes_current_week():
    """get_most_recent_continuity(..., before_week=W) must only consider
    weeks strictly less than W. Asking 'as of week 5' must never see week
    5's own (not-yet-known) continuity value."""
    from ol_continuity import get_most_recent_continuity

    lookup = {("AAA", 2023, 2): 3.0, ("AAA", 2023, 5): 7.0}

    # as-of week 5: only week 2 is strictly before it -> must return week 2's value, not week 5's own
    assert get_most_recent_continuity(lookup, "AAA", 2023, before_week=5) == 3.0

    # as-of week 2: nothing is strictly before it -> falls back to default
    assert get_most_recent_continuity(lookup, "AAA", 2023, before_week=2) == 0.0
    assert get_most_recent_continuity(lookup, "AAA", 2023, before_week=2, default=-1.0) == -1.0

    # as-of week 6: both prior weeks qualify, most recent (week 5) wins
    assert get_most_recent_continuity(lookup, "AAA", 2023, before_week=6) == 7.0

    # different team/season must not leak into the candidate set
    assert get_most_recent_continuity(lookup, "ZZZ", 2023, before_week=6) == 0.0
    assert get_most_recent_continuity(lookup, "AAA", 2024, before_week=6) == 0.0


def test_get_continuity_exact_match_and_default():
    from ol_continuity import get_continuity

    lookup = {("AAA", 2023, 3): 2}
    assert get_continuity(lookup, "AAA", 2023, 3) == 2
    assert get_continuity(lookup, "AAA", 2023, 2) is None  # off-by-one week must not match
    assert get_continuity(lookup, "AAA", 2023, 4) is None
    assert get_continuity(lookup, "AAA", 2023, 3, default=0) == 2  # exact match wins over default regardless
    assert get_continuity(lookup, "BBB", 2023, 3, default=0) == 0


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))
