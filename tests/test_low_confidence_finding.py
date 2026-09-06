"""
Keeps the low-confidence finding tied to the run that produced it.

This claim sat on the dashboard as a CONFIRMED FINDING with no script anywhere
in the repository that generated its numbers. Booth flagged it UNVERIFIABLE
while auditing PR #18. It has since been re-derived and it holds -- but the
reason it drifted loose in the first place was that nothing connected the words
on the page to a file on disk, and re-deriving it once does not fix that.
This is the connection.

Run with: pytest tests/test_low_confidence_finding.py -v
"""
import json
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
TEMPLATE = REPO_ROOT / 'src' / 'dashboard_template.html'
RESULTS = REPO_ROOT / 'data' / 'low_confidence_finding.json'


@pytest.fixture(scope='module')
def result():
    if not RESULTS.exists():
        pytest.skip("data/low_confidence_finding.json absent -- run "
                    "src/verify_low_confidence_finding.py")
    return json.loads(RESULTS.read_text())


def test_the_finding_actually_reproduced(result):
    """If a future re-run stops reproducing, this fails and forces the page to
    be corrected rather than left asserting something that no longer holds."""
    assert result['verdict'].startswith('CONFIRMED'), (
        f"the low-confidence finding no longer reproduces: {result['verdict']} "
        f"-- the Model Lab row and the pick-card comment must be corrected")
    r = result['reproduced']
    assert r['excludes_zero'], "the gap's interval now includes zero"
    assert r['gap_pt'] < 0, "the gap has changed direction"
    assert r['market_accuracy'] > r['model_a_accuracy']


def test_the_page_quotes_the_reproduced_figures_not_the_old_ones(result):
    """The specific decay this guards against. The old figures (52.5 / 64.4 /
    -11.95) came from somewhere nobody could point to; if they reappear on the
    page it means someone reverted to numbers with no provenance.

    Counted, not just searched. The finding is stated in TWO places -- the
    Model Lab row and the source comment above the pick-card code -- and an
    earlier version of this test only asked whether each figure appeared
    somewhere. A mutation that reverted one of the two locations passed
    cleanly, because the other copy still satisfied it. Requiring both means a
    half-revert, which leaves the page quietly contradicting itself, fails
    here instead of shipping."""
    page = TEMPLATE.read_text()
    r = result['reproduced']
    for value in (f"{r['model_a_accuracy']:.2f}",
                  f"{r['market_accuracy']:.2f}",
                  f"{abs(r['gap_pt']):.2f}"):
        count = page.count(value)
        assert count >= 2, (
            f"{value} appears {count} time(s) on the page; the finding is "
            f"stated in both the Model Lab row and the pick-card comment, so "
            f"a count below 2 means one of them has drifted off the "
            f"re-derived numbers in data/low_confidence_finding.json")


def test_the_page_names_the_script_that_produces_the_numbers(result):
    """A figure whose origin isn't stated is how this happened the first time."""
    page = TEMPLATE.read_text()
    assert 'verify_low_confidence_finding.py' in page, (
        "the page states the finding without naming what regenerates it")


def test_the_band_on_the_page_matches_the_band_that_was_measured(result):
    """'Within 0.05 of 50%' is the definition of the slice. If the script's
    band ever changes, the prose describing it has to change with it."""
    assert result['band'] == 0.05
    page = TEMPLATE.read_text()
    assert 'within 0.05 of a coin flip' in page


def test_the_slice_is_large_enough_to_carry_a_claim(result):
    """A finding stated in accuracy on a small subset would be exactly the
    thing this project has already confirmed you cannot do."""
    assert result['n_games_in_band'] >= 200, (
        f"only {result['n_games_in_band']} games in the band -- too few to "
        f"state an accuracy finding at this project's own standard")


def test_the_superseded_figures_survive_only_as_history():
    """Both places the old numbers appeared -- the Model Lab row and the
    pick-card source comment -- had to be updated. Missing one leaves the page
    contradicting itself.

    But the Model Lab row deliberately still names the old figures, in the
    sentence explaining that they were carried with no script behind them.
    That is worth keeping: it is the record of what changed and why, and this
    project's whole argument is that it reports its own corrections. So the
    rule is not "these digits must not appear" -- an earlier version of this
    test said exactly that and failed on the honest disclosure it was meant to
    protect. The rule is that wherever they appear, they must be marked as
    superseded."""
    page = TEMPLATE.read_text()

    for stale in re.finditer(r'(?:-|&minus;)11\.95pt', page):
        window = page[max(0, stale.start() - 200):stale.start()]
        assert 'previously carried' in window, (
            "the superseded gap figure appears without being marked as the "
            "old value -- if this is a revert, the page has lost its "
            "provenance again")

    # The old accuracy pair must never be stated as the live result. re.S
    # matters: the pick-card version of this sentence is a source comment that
    # wraps across lines, and without it a revert of that copy slips through
    # while the Model Lab copy still satisfies the "quotes the reproduced
    # figures" test above. A mutation reverting exactly that one location is
    # what exposed it.
    assert not re.search(
        r'it hits (?:just )?52\.5%[\s\S]{0,140}?(?:stays at|hits) 64\.4%', page, re.S), (
        "the superseded accuracy pair is still phrased as the current result")


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))
