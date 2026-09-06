"""
Ties the pandas-pin decision to the run that produced it.

requirements.txt now states a conclusion -- keep the pandas<2.0 pin, because
dropping nfl_data_py would move every EPA-derived metric beyond this project's
own reproducibility tolerance. That is a claim in a comment, sitting next to
the pins it justifies, which is exactly the shape of thing this repo has
watched drift before: the version history in config.py, the SOS column, the
figures on Model Lab.

So the numbers in that comment have to come from the experiment's own output.
If someone re-runs it and the result changes, this fails and the comment has
to be rewritten rather than quietly becoming false.

Note what is NOT asserted here: that pandas 2.x is bad, or that the pin is
permanent. The recorded finding is narrower than that -- the migration moves
published figures and would require regenerating them. A future run that
reaches a different verdict is not a regression, but it does have to update
the prose it invalidates.

Run with: pytest tests/test_pandas_version_experiment.py -v
"""
import json
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
RESULTS = REPO_ROOT / 'data' / 'pandas_version_experiment.json'
FALLBACK = REPO_ROOT / 'data' / 'data_source_fallback.json'
REQUIREMENTS = REPO_ROOT / 'requirements.txt'


@pytest.fixture(scope='module')
def result():
    if not RESULTS.exists():
        pytest.skip("data/pandas_version_experiment.json absent -- run "
                    "src/compare_pandas_versions.py")
    return json.loads(RESULTS.read_text())


@pytest.fixture(scope='module')
def fallback():
    if not FALLBACK.exists():
        pytest.skip("data/data_source_fallback.json absent -- run "
                    "src/verify_data_source_fallback.py")
    return json.loads(FALLBACK.read_text())


def test_the_experiment_had_valid_controls(result):
    """The load-bearing precondition. If either environment failed to
    reproduce itself, the cross-version deltas are run-to-run noise and the
    whole finding evaporates -- so this is checked before the finding is."""
    controls = result.get('controls')
    assert controls, (
        "no controls recorded -- the comparison was run without proving each "
        "environment is deterministic, so its verdict cannot be trusted")
    assert controls['baseline_reproduces'], (
        "the baseline environment did not reproduce itself")
    assert controls['candidate_reproduces'], (
        "the candidate environment did not reproduce itself")


def test_both_versions_scored_the_same_games(result):
    """backtest() calls dropna(subset=features), so two runs can silently
    evaluate different game sets -- the trap this repo documents. A metric
    comparison across different row sets would be meaningless."""
    assert result['same_row_sets'], (
        "the two environments did not evaluate the same games, so the deltas "
        "compare different populations")
    assert result['n_games'] == 1087, (
        f"expected the canonical 1087-game backtest, got {result['n_games']}")


def test_the_recorded_verdict_is_the_one_requirements_txt_argues_from(result):
    """requirements.txt keeps the pin on the strength of this verdict."""
    assert result['verdict'].startswith('REFUTED'), (
        f"the experiment now says {result['verdict']!r}, but requirements.txt "
        f"still argues from a REFUTED result -- rewrite the comment")


def test_the_figures_quoted_in_requirements_txt_match_the_experiment(result):
    """The specific decay this guards. Someone re-runs the experiment, the
    numbers move, the JSON updates -- and the comment beside the pins keeps
    quoting the old ones with total confidence."""
    text = REQUIREMENTS.read_text()
    auc = result['max_abs_delta']['auc']
    ll = result['max_abs_delta']['log_loss']

    assert f"{auc:.5f}".rstrip('0') in text or f"{auc:.5f}" in text, (
        f"requirements.txt does not quote the measured AUC delta {auc:.5f}")
    assert f"{ll:.5f}" in text, (
        f"requirements.txt does not quote the measured log-loss delta {ll:.5f}")

    m = re.search(r'(\d+)x that threshold', text)
    assert m, "requirements.txt no longer states how far past tolerance the shift is"
    stated = int(m.group(1))
    measured = round(auc / result['tolerance'])
    assert stated == measured, (
        f"requirements.txt says {stated}x tolerance; the recorded result is "
        f"{measured}x")


def test_the_market_only_model_is_the_one_that_does_not_move(result):
    """The finding that localises the cause. Every model built on EPA
    aggregation shifts; the one model reading a raw schedule column does not.
    If that stopped being true the explanation in requirements.txt -- that
    this is float aggregation over ~48k plays, not the modelling or the
    metrics -- would no longer be supported by anything."""
    market = [k for k in result['per_model'] if 'Market alone' in k]
    assert market, "the market-only reference model is gone from the backtest"
    deltas = result['per_model'][market[0]]
    for metric in ('log_loss', 'brier', 'auc'):
        assert deltas[metric]['delta'] == 0.0, (
            f"the market-only model now moves on {metric} "
            f"({deltas[metric]['delta']:+.6f}). It reads spread_line and does "
            f"no EPA aggregation, so requirements.txt's explanation of WHERE "
            f"the difference comes from no longer holds")


def test_the_fallback_was_verified_by_execution_not_assumption(fallback):
    """The other half of the decision. Keeping the pin is only justified if
    the thing it pins for actually works."""
    assert fallback['verdict'].startswith('REAL FALLBACK'), (
        f"the fallback now reports {fallback['verdict']!r} -- if nfl_data_py "
        f"has stopped working, the pandas pin is being paid for nothing and "
        f"requirements.txt's reasoning needs revisiting")
    assert fallback['importable']
    assert not fallback.get('missing_columns'), fallback.get('missing_columns')
    assert fallback['comparison']['values_agree'], (
        "nfl_data_py and nflreadpy no longer return the same values, so "
        "flipping USE_NFLREADPY would silently move the model")
    assert fallback['comparison']['games_compared'] > 0


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))
