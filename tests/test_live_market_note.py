"""Methodology says how the live market probability is made (Stage 25 item 6).

The 2026-09-28 audit: the backtest's "Vegas market alone" is a fitted model,
but the market probability saved with each live pick (and scored in Season
Accuracy) is weekly_update.market_prob(), a fixed curve with a hand-picked
5.5. Nothing on the page said so. The note is held to the function it
describes, so changing the constant without the sentence fails here.
"""
import inspect
import re
from pathlib import Path

from src.pipeline.template_parts import read_template  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]

TEMPLATE = read_template()


def note():
    m = re.search(r'<p[^>]*id="live-market-note"[^>]*>(.*?)</p>', TEMPLATE, re.S)
    assert m, 'the live-market note is gone from Methodology'
    return m.group(1)


def test_the_note_names_the_constant_the_code_uses():
    from src.pipeline import weekly_update
    src = inspect.getsource(weekly_update.market_prob)
    m = re.search(r'home_spread\s*/\s*([\d.]+)', src)
    assert m, 'market_prob no longer divides the spread by a constant -- rewrite the note'
    assert f'spread / {m.group(1)}' in note(), (
        f'market_prob uses {m.group(1)}; the Methodology note says otherwise')


def test_the_note_says_which_line_and_that_it_is_not_fitted():
    text = note()
    assert 'chosen by hand rather than fitted' in text
    assert 'the line when the pick was locked' in text


def test_the_note_is_on_the_methodology_page():
    page = re.search(r'<section[^>]*id="page-method".*?</section>', TEMPLATE, re.S)
    assert page and 'id="live-market-note"' in page.group(0)
