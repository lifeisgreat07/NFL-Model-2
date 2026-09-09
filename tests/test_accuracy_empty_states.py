"""Season Accuracy must not render absent data as a result.

Observed live on 2026-09-09, on the published dashboard:

  MODEL A 64.3%   MODEL B 57.1%   MARKET 57.1%
  Cumulative Accuracy Trend: three flat horizontal lines
  Weekly Trend: 2025 Wk 10  9/14 8/14 8/14
                2026 Wk 1   0/0  0/0  0/0

Every part of that was misleading, and none of it was a rendering bug in the
ordinary sense -- each number was computed correctly from what it was given.

2026 Week 1 had been graded before it was played, so results/ held an empty
list for it. That empty week became a row reading "0/0", which is not "no games
yet" but "we got none of none right", and it became a second point for the
trend chart to draw to. The three flat lines looked like a considered finding
and were an artifact of charting a week with nothing in it.

Underneath that, the whole page rested on a single week from the PREVIOUS
season -- so a page headed "Season Accuracy", read in September 2026, reported
2025 Week 10 as the season's record. That file has been removed; the page now
correctly reports having nothing yet, and fills in for real as 2026 is played.

The durable shape, and the reason these are tests rather than a fix: this is
the `return {}` failure the traps section already records -- a missing input
that arrives as a well-formed empty value and is then rendered as though it
were a measurement. Correct arithmetic on absent data still produces a lie.
"""

import json
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / 'src'))

import generate_dashboard as gd  # noqa: E402

TEMPLATE = REPO_ROOT / 'src' / 'dashboard_template.html'
BUILT = REPO_ROOT / 'index.html'


def _game(a=1, b=1, m=1):
    return {'model_a_correct': a, 'model_b_correct': b, 'market_correct': m,
            'prob_home_b': 0.7, 'prob_home_a': 0.7}


def test_a_week_with_nothing_graded_is_not_a_week():
    """The 0/0 row. A week present in results/ but holding no games must not
    reach the page as a data point at all."""
    summary = gd.build_accuracy_summary({
        (2026, 1): [_game(), _game()],
        (2026, 2): [],
    })
    labelled = [(w['season'], w['week']) for w in summary['weeks']]
    assert (2026, 2) not in labelled, (
        f"an empty week reached the weekly trend: {labelled}. It renders as "
        f"'0/0', which reads as a result rather than as 'not played yet'")
    assert labelled == [(2026, 1)]


def test_an_empty_week_cannot_extend_the_trend():
    """The flat-lines defect, stated as the property that actually matters:
    weeks[] is what the cumulative chart plots, so one real week must give it
    exactly one point no matter how many empty weeks sit beside it."""
    summary = gd.build_accuracy_summary({
        (2026, 1): [_game()],
        (2026, 2): [],
        (2026, 3): [],
    })
    assert len(summary['weeks']) == 1, (
        f"{len(summary['weeks'])} points for one graded week -- the extra ones "
        f"are empty weeks, and a line drawn between them is an artifact")


def test_no_graded_games_at_all_reports_nothing_rather_than_zero():
    summary = gd.build_accuracy_summary({(2026, 1): [], (2026, 2): []})
    assert summary['weeks'] == []
    assert summary['overall'] is None, (
        "overall must be None, not a zeroed record. A '0.0%' headline is a "
        "claim about the model; None is the absence of one")


def test_the_totals_still_count_a_real_week():
    """The other direction. Dropping empty weeks must not drop real games with
    them -- a guard that over-filters is as wrong as one that under-filters."""
    summary = gd.build_accuracy_summary({
        (2026, 1): [_game(a=1), _game(a=0), _game(a=1)],
        (2026, 2): [],
    })
    assert summary['overall']['model_a'] == {'correct': 2, 'n': 3, 'pct': 66.7}


def test_the_trend_chart_says_why_it_is_absent_below_two_weeks():
    """An empty space invites 'is it broken?'. The calibration section on this
    same page already answers that question in words when it lacks data; the
    trend chart now does the same instead of returning an empty string."""
    src = TEMPLATE.read_text(encoding='utf-8')
    fn = src[src.index('function buildCumulativeTrendChart'):]
    fn = fn[:fn.index('\nfunction ')]
    assert 'accuracy.weeks.length < 2' in fn, (
        'the trend chart no longer requires two graded weeks. One point drawn '
        'as a line suggests a direction that has not been measured')
    assert 'graded' in fn.lower(), (
        'the not-enough-data branch renders no explanation, so the reader sees '
        'a gap where a chart was')


@pytest.mark.skipif(not BUILT.exists(), reason='index.html not built')
def test_the_built_page_does_not_show_a_zero_of_zero_week():
    """Against the real artifact, not just the generator. This is the exact
    string a reader saw on the published site."""
    html = BUILT.read_text(encoding='utf-8', errors='ignore')
    m = re.search(r'__ACCURACY_JSON__|const\s+accuracy\s*=\s*(\{.*?\});\n',
                  html, re.S)
    assert m, 'could not find the injected accuracy data in index.html'
    if m.group(0).startswith('__'):
        pytest.skip('template placeholder, not a built page')
    data = json.loads(m.group(1))
    empties = [w for w in data.get('weeks', [])
               if w.get('model_a_n', 0) == 0 and w.get('market_n', 0) == 0]
    assert not empties, (
        f"the built page carries {len(empties)} week(s) with no graded games: "
        f"{[(w['season'], w['week']) for w in empties]}")


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))
