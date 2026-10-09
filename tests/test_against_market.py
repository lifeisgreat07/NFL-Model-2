"""How each model did when it picked against the market's favourite
(Stage 46 item 9; Mark approved it 2026-10-09).

Checked first that no page showed it: Season Accuracy had the record, the
forecast score and calibration, and Methodology the backtest against the
market, but nothing for the live games where a model sided with the
underdog. `build_against_market` in src/sports/nfl/generate_dashboard.py
counts them per model; the page leads with the 95% Wilson interval, because
at a few games a season the interval is the finding (Mark: an interval, not
a headline).

Run with: pytest tests/test_against_market.py -v
"""
import re
from pathlib import Path

import pytest

from src.core.template_parts import JOINED_TEMPLATE
from src.sports.nfl import generate_dashboard as gd
from src.sports.nfl.research.calibration import wilson_interval as research_wilson

ROOT = Path(__file__).resolve().parents[1]


def game(a, b, market, home_won, graded=True):
    g = {'model_a_home_win_prob': a, 'model_b_home_win_prob': b, 'market_prob_home': market}
    if graded:
        g['model_a_correct'] = int((a >= 0.5) == bool(home_won))
        g['model_b_correct'] = None if b is None else int((b >= 0.5) == bool(home_won))
    return g


def test_a_pick_against_the_favourite_is_counted_and_graded():
    games = [game(0.45, 0.55, 0.60, home_won=0),   # A against, right
             game(0.40, 0.45, 0.65, home_won=1),   # both against, wrong
             game(0.60, 0.62, 0.70, home_won=1)]   # with the market
    m = gd.build_against_market(games)
    assert (m['model_a']['n'], m['model_a']['right']) == (2, 1)
    assert (m['model_b']['n'], m['model_b']['right']) == (1, 0)
    assert m['priced'] == 3


def test_a_market_at_exactly_even_has_no_favourite():
    m = gd.build_against_market([game(0.40, 0.40, 0.5, home_won=0)])
    assert m['model_a']['n'] == 0 and m['priced'] == 1


def test_a_model_at_exactly_even_picks_home_as_its_grade_does():
    m = gd.build_against_market([game(0.5, None, 0.4, home_won=1)])
    assert (m['model_a']['n'], m['model_a']['right']) == (1, 1)


def test_games_with_no_price_no_grade_or_no_model_b_are_left_out():
    games = [game(0.4, 0.4, None, home_won=1), game(0.4, 0.4, 0.6, home_won=1, graded=False),
             game(0.4, None, 0.6, home_won=0)]
    m = gd.build_against_market(games)
    assert m['model_b']['n'] == 0 and m['model_a']['n'] == 1 and m['priced'] == 1


@pytest.mark.parametrize('k, n', [(0, 0), (0, 1), (1, 1), (3, 7), (8, 20), (50, 100)])
def test_the_interval_is_the_research_modules_wilson(k, n):
    assert gd.wilson_interval(k, n) == pytest.approx(research_wilson(k, n))


def test_the_interval_is_what_the_summary_carries():
    m = gd.build_against_market([game(0.45, 0.45, 0.6, home_won=0)] * 3 + [game(0.45, 0.45, 0.6, home_won=1)] * 4)
    lo, hi = research_wilson(3, 7)
    assert (m['model_a']['lo'], m['model_a']['hi']) == (round(100 * lo, 1), round(100 * hi, 1))


def test_the_season_summary_carries_it():
    summary = gd.build_accuracy_summary({(2026, 1): [dict(game(0.45, 0.55, 0.6, home_won=0), actual_home_win=0,
                                                          market_correct=0)]})
    assert summary['against_market']['model_a']['n'] == 1
    assert gd.build_accuracy_summary({})['against_market'] is None


def page():
    return JOINED_TEMPLATE.read_text(encoding='utf-8')


def test_the_page_leads_each_row_with_its_interval_and_shows_no_bare_rate():
    fn = re.search(r'function againstMarketHtml\(m\)\{.*?\n\}\n', page(), re.S)
    assert fn, 'againstMarketHtml is not findable'
    body = fn.group(0)
    assert '${r.right} of ${r.n} right <span class="against-ci">(95% interval ${r.lo}% to ${r.hi}%)</span>' in body
    assert 'r.right / r.n' not in body and 'r.right/r.n' not in body, 'a bare rate reads as a headline'
    assert "No game yet" in body


def test_season_accuracy_shows_it():
    assert '+ againstMarketHtml(accuracy.against_market);' in page()
