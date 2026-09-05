"""
Tests for src/ats_evaluation.py, plus a guard on the shared column it needed.

The cover rule is one subtraction, and getting it backwards would produce a
confident, completely inverted result that still looks like a plausible hit
rate. Most of what follows exists to make that impossible to ship quietly.

Run with: pytest tests/test_ats_evaluation.py -v
"""
import ast
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / 'src'))

from ats_evaluation import (  # noqa: E402
    BREAK_EVEN, add_ats_columns, assess, bootstrap_rate, hit_rate,
)


def frame(rows):
    """rows: (spread_line, home_margin) -> a hist-shaped frame."""
    return pd.DataFrame([
        {'spread_line': s, 'home_margin': m, 'home_win': int(m > 0)}
        for s, m in rows
    ])


def realistic(n=400, seed=0):
    """Spreads that actually predict margins, as real ones do."""
    rng = np.random.default_rng(seed)
    spread = rng.integers(-10, 11, n).astype(float)
    margin = np.round(spread + rng.normal(0, 13, n)).astype(int)
    return frame(list(zip(spread, margin)))


# ============================================================
# The cover rule
# ============================================================
def test_a_favourite_must_win_by_more_than_the_line():
    """Home favoured by 3. Winning by 7 covers; by 3 is a push; by 1 does not."""
    h, _ = add_ats_columns(pd.concat([realistic(), frame([(3, 7), (3, 3), (3, 1)])],
                                     ignore_index=True))
    tail = h.tail(3).reset_index(drop=True)
    assert tail.loc[0, 'home_covered'] == 1 and not tail.loc[0, 'push']
    assert tail.loc[1, 'push']
    assert tail.loc[2, 'home_covered'] == 0 and not tail.loc[2, 'push']


def test_an_underdog_can_cover_while_losing():
    """The case that separates ATS from picking winners: home is a 7-point dog
    and loses by 3, which covers. A rule that only looked at who won would get
    this backwards."""
    h, _ = add_ats_columns(pd.concat([realistic(), frame([(-7, -3)])],
                                     ignore_index=True))
    last = h.iloc[-1]
    assert last['home_win'] == 0
    assert last['home_covered'] == 1


def test_an_inverted_spread_convention_is_rejected_loudly():
    """If spread_line ever came in negated, every result in this file would
    flip while still printing plausible numbers. It must raise, not compute."""
    good = realistic()
    flipped = good.copy()
    flipped['spread_line'] = -flipped['spread_line']
    with pytest.raises(ValueError, match='inverted|correlates'):
        add_ats_columns(flipped)


def test_pushes_are_flagged_separately_from_losses():
    """A push returns the stake. Scoring it as a loss would understate every
    hit rate on this page."""
    h, _ = add_ats_columns(pd.concat([realistic(), frame([(3, 3), (-6, -6)])],
                                     ignore_index=True))
    assert h.tail(2)['push'].all()


# ============================================================
# Hit rate and intervals
# ============================================================
def test_hit_rate_counts_a_correct_away_pick():
    """picked_home=0 is right when the home team did NOT cover. An
    implementation that only scored home picks would silently halve the away
    side's contribution."""
    covered = np.array([1, 0, 1, 0])
    picked = np.array([0, 0, 1, 1])   # wrong, right, right, wrong
    rate, correct = hit_rate(picked, covered)
    assert list(correct) == [0, 1, 1, 0]
    assert rate == pytest.approx(0.5)


def test_a_perfect_and_a_hopeless_strategy_score_as_expected():
    covered = np.array([1, 1, 0, 0, 1])
    assert hit_rate(covered, covered)[0] == pytest.approx(1.0)
    assert hit_rate(1 - covered, covered)[0] == pytest.approx(0.0)


def test_bootstrap_and_wilson_intervals_agree():
    """A hit rate is a binomial proportion with a closed form, so the
    resampling has an independent check available. Two routes disagreeing
    means the bootstrap is wired wrong."""
    rng = np.random.default_rng(3)
    covered = (rng.random(900) < 0.5).astype(int)
    picked = (rng.random(900) < 0.5).astype(int)
    r = assess('test', picked, covered)
    assert r['ci_lo'] == pytest.approx(r['wilson_lo'], abs=0.02)
    assert r['ci_hi'] == pytest.approx(r['wilson_hi'], abs=0.02)


def test_the_bar_is_break_even_not_a_coin_flip():
    """A strategy can clear 50% and still lose money. The two flags must be
    able to disagree, or the headline verdict is meaningless."""
    assert BREAK_EVEN == pytest.approx(110 / 210)
    assert 0.50 < BREAK_EVEN < 0.53
    # 51.5% over a large sample: above a coin flip, below break-even.
    n = 40000
    correct = np.zeros(n, dtype=int)
    correct[:int(n * 0.515)] = 1
    lo, _ = bootstrap_rate(correct, n_resamples=300, seed=1)
    assert lo > 0.50, "a 51.5% strategy should clear the coin-flip bar"
    assert lo < BREAK_EVEN, "...but must not be reported as profitable"


def test_a_coin_flip_strategy_is_not_reported_as_an_edge():
    rng = np.random.default_rng(11)
    covered = (rng.random(1100) < 0.5).astype(int)
    picked = (rng.random(1100) < 0.5).astype(int)
    r = assess('coin flip', picked, covered)
    assert not r['beats_break_even']


# ============================================================
# The shared column this needed
# ============================================================
def test_home_margin_was_added_without_disturbing_the_feature_columns():
    """build_historical_features is shared by backtest.py, calibration.py and
    the live weekly path. Adding home_margin must not change what any model
    trains on -- this reads the row literal itself rather than trusting that
    an additive edit stayed additive."""
    src = (REPO_ROOT / 'src' / 'weekly_update.py').read_text()
    tree = ast.parse(src)
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == 'build_historical_features')
    dicts = [n for n in ast.walk(fn) if isinstance(n, ast.Dict)]
    built = max(dicts, key=lambda d: len(d.keys))
    keys = {k.value for k in built.keys if isinstance(k, ast.Constant)}

    expected = {
        'season', 'week', 'home_win', 'home_margin',
        'off_matchup', 'def_matchup', 'qb_matchup',
        'ol_continuity_diff', 'qb_change_diff', 'spread_line',
    }
    assert keys == expected, (
        f"the historical feature row changed shape: {keys ^ expected}")


def test_no_model_trains_on_home_margin():
    """home_margin is the outcome's own scoreline. A model fitted on it is
    leaking the answer -- the single worst failure this project has had (the
    snap-share leak, caught only after it produced a promising result), and
    worth a permanent guard.

    Scoped to module-level CONSTANTS that name features. An earlier version of
    this test scanned every list literal and flagged
    `dropna(subset=['spread_line', 'home_margin', 'home_win'])` in
    ats_evaluation.py -- which is how that module legitimately requires the
    column to exist before deriving the cover outcome from it. Reading a
    column is not training on one, and a guard that cannot tell those apart
    gets switched off the first time it cries wolf.
    """
    feature_names = {'off_matchup', 'def_matchup', 'qb_matchup',
                     'qb_change_diff', 'spread_line', 'ol_continuity_diff'}
    checked = 0
    for name in ('backtest.py', 'calibration.py', 'ats_evaluation.py',
                 'weekly_update.py', 'bootstrap_brier_gap.py'):
        path = REPO_ROOT / 'src' / name
        if not path.exists():
            continue
        tree = ast.parse(path.read_text())
        for node in tree.body:                       # module level only
            if not isinstance(node, ast.Assign):
                continue
            targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
            if not any(t.isupper() for t in targets):
                continue
            strings = {n.value for n in ast.walk(node)
                       if isinstance(n, ast.Constant) and isinstance(n.value, str)}
            if strings & feature_names:
                checked += 1
                assert 'home_margin' not in strings, (
                    f"{name}: the feature constant {targets} contains "
                    f"home_margin, which is the scoreline the model is "
                    f"supposed to be predicting")
    assert checked >= 3, (
        f"only found {checked} feature constants to check -- this guard has "
        f"stopped looking at anything and would pass on a real leak")


# ============================================================
# The page must not overstate the result
# ============================================================
def _results():
    import json
    p = REPO_ROOT / 'data' / 'ats_evaluation.json'
    if not p.exists():
        pytest.skip("data/ats_evaluation.json absent -- run src/ats_evaluation.py")
    return json.loads(p.read_text())


def test_the_page_quotes_the_real_ats_numbers():
    """Same tie as the bootstrap prose: the hit rate and interval printed on
    the dashboard have to be the ones in the results file."""
    d = _results()
    r = d['results']['model']
    page = (REPO_ROOT / 'src' / 'dashboard_template.html').read_text()
    for value in (f"{r['rate']*100:.2f}%",
                  f"{r['ci_lo']*100:.2f}%",
                  f"{r['ci_hi']*100:.2f}%"):
        assert value in page, f"the dashboard does not quote {value} from ats_evaluation.json"
    assert f"{d['n_games']:,}" in page or str(d['n_games']) in page


def test_the_page_does_not_claim_an_ats_edge_that_the_data_denies():
    """The failure worth guarding: a future re-run nudges the rate up, someone
    reads 51.6% as 'slightly profitable', and the page starts implying an edge
    the interval never supported."""
    d = _results()
    r = d['results']['model']
    page = (REPO_ROOT / 'src' / 'dashboard_template.html').read_text()
    if not r['beats_break_even']:
        assert 'would not have made money' in page, (
            "the ATS result does not clear break-even, but the page no longer "
            "says so plainly")
    else:
        pytest.fail(
            "the ATS strategy now clears break-even -- the page's wording was "
            "written for the no-edge case and needs rewriting by hand")


def test_controls_were_sane_in_the_published_run():
    """A published ATS number is only meaningful if the trivial controls landed
    near 50%. If they did not, the arithmetic was wrong and the headline is
    noise dressed as a result."""
    d = _results()
    assert d['controls_sane'], "the published run had a control far from 50%"
    for k in ('always_home', 'always_away', 'always_favourite'):
        assert abs(d['results'][k]['rate'] - 0.5) <= 0.06


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))
