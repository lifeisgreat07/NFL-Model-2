"""
Leak-free tests for the rating/continuity pipeline.

These don't hit the network -- everything is built from small synthetic
DataFrames shaped exactly like what data_loader.py hands to these
functions, so each test isolates one specific leak-free property instead
of depending on real season data (which changes shape from week to week
and can't prove a negative -- "this future data had no effect" -- as
cleanly as a synthetic before/after mutation can).

Run: python -m pytest test_leak_free.py -v
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent / "src"))

from ratings_engine import build_team_ratings, build_qb_ratings
from ol_continuity import compute_ol_continuity_lookup, get_continuity, get_most_recent_continuity
from config import MIN_PLAYS_FOR_RATING


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


def test_team_ratings_cutoff_excludes_current_and_future_weeks():
    """fit_at(cutoff_i) must use gwidx < cutoff_i, never <=. Proof: mutate
    the cutoff week's own data into something wildly different and confirm
    the rating computed *as of* that cutoff doesn't move at all."""
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


def test_qb_rating_cutoff_excludes_current_and_future_weeks():
    """Same leak-free property as team ratings, but for build_qb_ratings'
    trailing_rating closure: prior plays must satisfy gwidx < cutoff_gwidx."""
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
    starters = ["L1", "L2", "L3", "L4", "L5"]
    rows = []
    for p in starters:
        rows.append(_snap_row("AAA", 2023, 18, p, snaps=60, game_type="POST"))
        rows.append(_snap_row("AAA", 2023, 19, p, snaps=60, game_type="REG"))
    snap_counts = pd.DataFrame(rows)
    lookup = compute_ol_continuity_lookup(snap_counts)
    assert ("AAA", 2023, 19) not in lookup  # week 18 was POST, filtered out before the adjacency check


def test_most_recent_continuity_boundary_excludes_current_week():
    """get_most_recent_continuity(..., before_week=W) must only consider
    weeks strictly less than W. Asking 'as of week 5' must never see week
    5's own (not-yet-known) continuity value."""
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
    lookup = {("AAA", 2023, 3): 2}
    assert get_continuity(lookup, "AAA", 2023, 3) == 2
    assert get_continuity(lookup, "AAA", 2023, 2) is None  # off-by-one week must not match
    assert get_continuity(lookup, "AAA", 2023, 4) is None
    assert get_continuity(lookup, "AAA", 2023, 3, default=0) == 2  # exact match wins over default regardless
    assert get_continuity(lookup, "BBB", 2023, 3, default=0) == 0


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
