"""
Guards on the track-record line each pick now carries.

The display itself is JavaScript, so what is checkable from Python is the data
it stands on and the structure of the code that reads it. Both have a failure
mode that produces no error and no visible break -- just a line that quietly
stops appearing, or appears saying the opposite of the truth.

Run with: pytest tests/test_pick_track_record.py -v
"""
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
TEMPLATE = REPO_ROOT / 'src' / 'dashboard_template.html'
CALIBRATION = REPO_ROOT / 'data' / 'calibration.json'


@pytest.fixture(scope='module')
def calibration():
    if not CALIBRATION.exists():
        pytest.skip("data/calibration.json absent -- run src/calibration.py")
    return json.loads(CALIBRATION.read_text())


# ============================================================
# The data the display stands on
# ============================================================
def test_bins_tile_the_whole_probability_range_without_gaps(calibration):
    """Every stated probability must land in exactly one bin.

    The lookup does `bins.find(...)` and renders nothing when that returns
    undefined. So a gap in the bin edges doesn't raise -- the track record just
    silently disappears for whichever games fall in the hole, and the page
    looks fine. This is the test that would catch it."""
    for name, model in calibration['models'].items():
        edges = [(b['lo'], b['hi']) for b in model['bins']]
        assert edges == sorted(edges), f"{name}: bins are not in ascending order"
        assert edges[0][0] == 0.0, f"{name}: bins start at {edges[0][0]}, not 0"
        assert edges[-1][1] == 1.0, f"{name}: bins end at {edges[-1][1]}, not 1"
        for (_, prev_hi), (lo, _) in zip(edges, edges[1:]):
            assert lo == prev_hi, (
                f"{name}: gap or overlap between bins at {prev_hi} and {lo} -- "
                f"probabilities in between would render no track record at all")


def test_every_bin_interval_actually_brackets_its_own_rate(calibration):
    """A Wilson interval that doesn't contain the observed rate would render a
    nonsensical claim on a pick card."""
    for name, model in calibration['models'].items():
        for b in model['bins']:
            assert b['ci_lo'] <= b['observed'] <= b['ci_hi'], (
                f"{name} bin {b['label']}: observed {b['observed']} outside "
                f"CI [{b['ci_lo']}, {b['ci_hi']}]")


def test_the_complement_of_an_interval_stays_a_valid_interval(calibration):
    """An away pick shows 100 minus the bin's home-win figures. Flipping an
    interval reverses its ends, so [lo, hi] becomes [100-hi, 100-lo]. Writing
    it the other way round yields lo > hi, which renders as a backwards range
    instead of failing -- this asserts the arithmetic the template does."""
    for model in calibration['models'].values():
        for b in model['bins']:
            lo, hi = 100 - b['ci_hi'], 100 - b['ci_lo']
            rate = 100 - b['observed']
            assert lo <= hi, f"complemented interval is backwards: [{lo}, {hi}]"
            assert lo <= rate <= hi


# ============================================================
# The code that reads it
# ============================================================
def _fn(name):
    src = TEMPLATE.read_text()
    start = src.index(f'function {name}(')
    depth, i = 0, src.index('{', start)
    for j in range(i, len(src)):
        if src[j] == '{':
            depth += 1
        elif src[j] == '}':
            depth -= 1
            if depth == 0:
                return src[start:j + 1]
    raise AssertionError(f"could not find the end of {name}()")


def test_away_picks_are_read_as_the_complement():
    """The bins are over the probability of a HOME win. An away pick at 65% is
    a 35% home probability, and that bin's rate has to be flipped before it
    says anything about the away side. Getting this backwards would show a
    confident pick as though it historically lost -- wrong in the most
    misleading possible direction, with no error anywhere."""
    body = _fn('pickTrackRecord')
    assert 'pickedHome' in body, "the picked side is no longer distinguished"
    assert '100 - bin.observed' in body, "the away rate is not complemented"
    assert '100 - bin.ci_hi' in body and '100 - bin.ci_lo' in body, (
        "the away interval is not complemented")
    # The ends must swap. lo takes ci_hi's complement; hi takes ci_lo's.
    lo_line = next(l for l in body.splitlines() if l.strip().startswith('const lo'))
    hi_line = next(l for l in body.splitlines() if l.strip().startswith('const hi'))
    assert 'ci_hi' in lo_line, f"lo must come from ci_hi when flipped: {lo_line.strip()}"
    assert 'ci_lo' in hi_line, f"hi must come from ci_lo when flipped: {hi_line.strip()}"


def test_underpowered_bands_report_their_count_instead_of_a_rate():
    """Same rule the live calibration panel and the reliability diagram already
    follow: a thin bin keeps its real count and is never dressed up as a
    measurement."""
    body = _fn('trackRecordHtml')
    assert 'underpowered' in body
    assert 'too few' in body


def test_a_band_whose_interval_spans_fifty_is_called_a_coin_flip():
    """The point of putting this on a pick card at all. A 52% pick reads as
    'slightly favoured' unless the reader is told its band has never actually
    beaten a coin flip."""
    body = _fn('pickTrackRecord')
    assert 'coinFlip' in body and 'lo <= 50 && hi >= 50' in body


def test_the_track_record_appears_on_both_places_a_pick_is_shown():
    """The board is where picks are read; the Picks page is where they're
    chosen. Showing the record on only one of them means the decision screen is
    the one missing it."""
    src = TEMPLATE.read_text()
    assert src.count('${trackRecordHtml(g.mktB_home)}') >= 2, (
        "the track record is rendered in fewer than both pick views")


def test_season_range_does_not_render_every_year(calibration):
    """A four-season backtest rendered as '2022-2023-2024-2025' is noise. It
    collapses to a range only when the seasons are actually contiguous, since
    collapsing a gap would misstate the span."""
    body = _fn('seasonRange')
    assert 'contiguous' in body
    seasons = calibration['backtest_seasons']
    assert seasons == list(range(seasons[0], seasons[-1] + 1)), (
        "backtest seasons are no longer contiguous -- check the rendered range "
        "still reads correctly on the pick cards")


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))
