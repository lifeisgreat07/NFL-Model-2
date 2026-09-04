"""
Tests for the live weekly pipeline's data dependencies.

Context: O-line continuity was removed from the model at v2.1 after two
independent negative tests, but weekly_update.main() kept loading snap
counts every run to compute ol_continuity_diff and write it into every
saved prediction. Nothing live read that field -- the dashboard renders
`why.ol_continuity` only when present, and real predictions' `why` block
contains only off_matchup, def_matchup, qb_matchup and qb_change.

That made an entire upstream data source (load_snap_counts) a hard
dependency of the unattended Tuesday job for no benefit. load_snap_counts
is in the same family as the call that produced the 2026 Week 1 offseason
crash (see tests/test_data_loader.py), so removing it from the live path
removes a real failure mode from the automation.

What these tests pin down:

  1. The live path must not reach for snap counts again. This is a
     structural check on main()'s source -- it can't run main() for real
     (that needs six seasons of network data), and it says so rather than
     pretending to be a behavioural test.
  2. The removal is only safe BECAUSE neither fitted model uses
     ol_continuity_diff. If someone ever adds it back as a feature, that
     assumption breaks and this test should fail loudly.
  3. build_historical_features must still honour ol_lookup. backtest.py
     depends on it for the "[reference only] + OL continuity" rows, which
     are the live evidence behind the published REJECT of the feature.
     Deleting the live path must not quietly break the evidence.

Run with: pytest tests/test_weekly_pipeline.py -v
"""
import inspect
import io
import sys
import tokenize
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def _code_only(src: str) -> str:
    """Source with comments stripped.

    These tests assert on what main() *does*, and the code they guard is
    deliberately commented with the names being forbidden (explaining why
    the dependency was removed). Grepping raw source would flag those
    comments as violations -- a test that can't tell a comment from a call
    is worse than no test. Tokenising drops COMMENT tokens properly,
    including inline ones, without mangling strings.

    Line structure is preserved: one of the tests below scans individual
    lines for `.fit(` calls, so rebuilding the source from tokens alone
    would break it.
    """
    lines = src.splitlines()
    cut_at = {}
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type == tokenize.COMMENT:
            row, col = tok.start
            cut_at[row] = min(cut_at.get(row, col), col)
    return "\n".join(
        line[:cut_at[i]] if i in cut_at else line
        for i, line in enumerate(lines, start=1)
    )


# ============================================================
# 1. The live weekly path must not depend on snap counts
# ============================================================
def test_weekly_main_does_not_load_snap_counts():
    """Structural guard, not a behavioural one: main() needs six seasons of
    real play-by-play to run, so this asserts on its source instead. It
    exists to stop the dependency being reintroduced by accident."""
    import weekly_update

    src = _code_only(inspect.getsource(weekly_update.main))

    for forbidden in ('load_snap_counts', 'compute_ol_continuity_lookup',
                      'get_most_recent_continuity'):
        assert forbidden not in src, (
            f"weekly_update.main() references {forbidden!r} again -- the live "
            "weekly job should not depend on snap counts for a feature no "
            "fitted model uses. See this module's docstring."
        )


def test_saved_predictions_no_longer_carry_ol_continuity_diff():
    """The saved-prediction dict should not write a field nothing reads."""
    import weekly_update

    src = _code_only(inspect.getsource(weekly_update.main))
    assert "'ol_continuity_diff'" not in src, (
        "main() still writes ol_continuity_diff into saved predictions"
    )


# ============================================================
# 2. The removal is only safe because no model uses the feature
# ============================================================
def test_neither_fitted_model_uses_ol_continuity():
    """If ol_continuity_diff ever becomes a real model input again, dropping
    it from the live path would silently change predictions. Pin the
    assumption that makes the removal safe."""
    import weekly_update

    src = _code_only(inspect.getsource(weekly_update.main))

    fit_lines = [ln for ln in src.splitlines() if '.fit(' in ln]
    assert fit_lines, "expected to find model .fit( calls in main()"
    for ln in fit_lines:
        assert 'ol_continuity_diff' not in ln, (
            "a fitted model now uses ol_continuity_diff -- removing it from "
            "the live path is no longer safe"
        )


# ============================================================
# 3. The backtest's reference comparison must keep working
# ============================================================
def _minimal_inputs(ol_lookup):
    """Smallest real inputs build_historical_features accepts. `plays` and
    `week_keys` are unused by the function body, so they're passed as None
    deliberately rather than faked into something misleading."""
    season, week = 2024, 2

    sched = pd.DataFrame([{
        'season': season, 'week': week,
        'home_team': 'AAA', 'away_team': 'BBB',
        'home_score': 24, 'away_score': 17, 'spread_line': -3.0,
    }])

    starters = pd.DataFrame([
        {'season': season, 'week': week, 'posteam': 'AAA', 'passer_player_id': 'QB-A'},
        {'season': season, 'week': week, 'posteam': 'BBB', 'passer_player_id': 'QB-B'},
    ])

    qb = {
        'identify_starters': lambda s, w: starters,
        'trailing_rating': lambda pid, cutoff: {'QB-A': 0.20, 'QB-B': 0.05}[pid],
        'week_to_idx': {(season, week): 1},
    }

    return dict(
        plays=None,
        week_keys=None,
        week_to_idx={(season, week): 1},
        team_ratings_by_week={(season, week): {'AAA': (0.10, 0.02), 'BBB': (0.04, 0.06)}},
        qb=qb,
        schedules_by_season={season: sched},
        ol_lookup=ol_lookup,
    )


def test_build_historical_features_still_honours_ol_lookup():
    """backtest.py's '[reference only] + OL continuity' rows depend on this.
    A real lookup must produce a real, non-zero difference."""
    from weekly_update import build_historical_features

    ol_lookup = {('AAA', 2024, 2): 0.8, ('BBB', 2024, 2): 0.2}
    hist = build_historical_features(**_minimal_inputs(ol_lookup))

    assert len(hist) == 1
    assert hist.iloc[0]['ol_continuity_diff'] == pytest.approx(0.6)


def test_build_historical_features_defaults_ol_to_zero_without_lookup():
    """And with no lookup it must stay neutral rather than blowing up --
    this is the path the live weekly job now takes."""
    from weekly_update import build_historical_features

    hist = build_historical_features(**_minimal_inputs(None))

    assert len(hist) == 1
    assert hist.iloc[0]['ol_continuity_diff'] == pytest.approx(0.0)
    # The features the live models actually fit on must still be real.
    assert hist.iloc[0]['off_matchup'] == pytest.approx(0.10 - 0.06)
    assert hist.iloc[0]['qb_matchup'] == pytest.approx(0.20 - 0.05)


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))
