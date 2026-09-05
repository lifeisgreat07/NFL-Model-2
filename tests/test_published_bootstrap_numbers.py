"""
Every confidence interval printed on the dashboard must exist in the data.

The reliability panel and three Model Lab rows quote bootstrap intervals as
hand-typed text. That is the right way to write prose about a result, but it
creates a specific failure this project has already been burned by once: the
QB-shrinkage entry sat on the page for weeks asserting a number that no longer
reproduced, because nothing tied the words to the file. This is that tie.

It works in the direction that matters. Rather than asserting the page quotes
some fixed list of numbers -- which would fight every future edit to the prose
-- it takes every "CI [x, y]" the page prints and requires it to be a real
interval in data/bootstrap_brier_gap.json. Rewording is free; inventing a
number, or leaving a stale one behind after a re-run, is not.

Run with: pytest tests/test_published_bootstrap_numbers.py -v
"""
import json
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
TEMPLATE = REPO_ROOT / 'src' / 'dashboard_template.html'
RESULTS = REPO_ROOT / 'data' / 'bootstrap_brier_gap.json'

# The page writes negatives as the HTML entity and positives with a sign, e.g.
# "CI [&minus;0.002395, +0.001141]".
#
# Deliberately scoped to SIX-decimal intervals. Model Lab also carries older
# intervals from experiments that predate this analysis -- "CI [-3.13, +0.09]"
# on the margin-of-victory row, for instance -- and those are accuracy
# PERCENTAGE POINTS, not probability-scale scores. They have their own
# provenance and are not in this file. Matching everything shaped like an
# interval would drag them in and fail for a reason that has nothing to do
# with what this test is checking. Six decimals is the format
# bootstrap_brier_gap.py writes and nothing else on the page uses.
NUM = r'(?:&minus;|-|\+)?\d+\.\d{6}'
CI_RE = re.compile(rf'CI \[({NUM}), ({NUM})\]')


def _value(text):
    return float(text.replace('&minus;', '-').replace('+', ''))


@pytest.fixture(scope='module')
def results():
    if not RESULTS.exists():
        pytest.skip("data/bootstrap_brier_gap.json absent -- run src/bootstrap_brier_gap.py")
    return json.loads(RESULTS.read_text())


@pytest.fixture(scope='module')
def known_intervals(results):
    out = set()
    for comp in results['comparisons'].values():
        for m in comp['metrics'].values():
            out.add((round(m['ci_lo'], 6), round(m['ci_hi'], 6)))
        b = comp['metrics'].get('brier', {})
        if 'analytic_ci_lo' in b:
            out.add((round(b['analytic_ci_lo'], 6), round(b['analytic_ci_hi'], 6)))
    return out


def test_the_page_quotes_at_least_one_interval():
    """If the prose stops citing intervals entirely, this whole file would
    pass vacuously while the page silently loses its evidence."""
    found = CI_RE.findall(TEMPLATE.read_text())
    assert len(found) >= 6, f"only {len(found)} intervals quoted on the page"


def test_every_quoted_interval_is_a_real_result(known_intervals):
    for lo_s, hi_s in CI_RE.findall(TEMPLATE.read_text()):
        pair = (round(_value(lo_s), 6), round(_value(hi_s), 6))
        assert pair in known_intervals, (
            f"the dashboard quotes CI [{lo_s}, {hi_s}], which is not in "
            f"data/bootstrap_brier_gap.json -- either the prose is stale after "
            f"a re-run, or the number was typed rather than read")


def test_the_page_does_not_call_an_inconclusive_gap_a_finding(results):
    """The specific error this work corrected. Model B vs the market is
    inconclusive on every metric, and the reliability panel used to imply
    otherwise. If a future re-run ever makes it real, this test is what forces
    someone to revisit the wording deliberately instead of leaving whichever
    version happens to be there."""
    metrics = results['comparisons']['model_b_vs_market']['metrics']
    any_real = any(m['excludes_zero'] for m in metrics.values())
    page = TEMPLATE.read_text()
    if not any_real:
        assert 'the lead did not survive' in page, (
            "Model B vs the market is inconclusive on every metric, but the "
            "reliability panel no longer says so")
    else:
        pytest.fail(
            "a Model B vs market gap now excludes zero -- the reliability "
            "panel's wording was written for the inconclusive case and needs "
            "rewriting by hand, not silently passing")


def test_confirmed_findings_on_the_page_really_exclude_zero(results):
    """Two Model Lab rows are tagged CONFIRMED FINDING. That tag is load-bearing
    in this project, so it has to be backed by an interval that excludes zero."""
    for comparison, metric in (('model_b_vs_model_a', 'brier'),
                               ('model_a_vs_market', 'brier')):
        m = results['comparisons'][comparison]['metrics'][metric]
        assert m['excludes_zero'], (
            f"{comparison} {metric} is tagged as a confirmed finding on Model "
            f"Lab but its CI [{m['ci_lo']}, {m['ci_hi']}] includes zero")


def test_bootstrap_run_is_big_enough_and_reproducible(results):
    """The project's stated convention is 5,000 resamples, and a published
    interval that cannot be regenerated is not evidence."""
    assert results['n_resamples'] >= 5000
    assert isinstance(results['seed'], int)
    assert results['n_games'] > 1000


def test_all_models_were_compared_on_the_same_games(results):
    """Pairing is the whole basis of these intervals. If the models ever stop
    covering the same rows, the comparison silently becomes unpaired and every
    interval on the page is wrong."""
    cov = results['coverage']
    per_model = {k: v for k, v in cov.items() if k != 'common'}
    assert len(set(per_model.values())) == 1, (
        f"models no longer see the same games: {per_model}")
    assert cov['common'] == min(per_model.values())


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))
