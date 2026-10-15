"""The NHL's and NBA's day boards open with one plain line (Stage 77 item 14, the 2026-10-13 UI/UX audit's copy fix 3).

The lede was four lines ending in the Model A/B rule. It is now "Today's
games, each model's pick, and how it did. Tap a game for the details.", and
each card says which model made its pick, beside the market it depends on.

Run with: pytest tests/test_board_lede.py -v
"""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEDE = '<div class="desc">Today&#39;s games, each model&#39;s pick, and how it did. Tap a game for the details.</div>'


@pytest.mark.parametrize('sport', ('nhl', 'nba'))
def test_the_day_boards_lede_is_one_plain_line(sport):
    body = (ROOT / 'src' / 'sports' / sport / 'pages' / 'body.html').read_text(encoding='utf-8')
    board = body[body.index('id="page-board"'):body.index('</section>', body.index('id="page-board"'))]
    assert LEDE in board and 'when the market posted a price' not in board


@pytest.mark.parametrize('sport', ('nhl', 'nba'))
def test_each_card_says_which_model_made_its_pick(sport):
    js = (ROOT / 'src' / 'sports' / sport / 'pages' / f'{sport}.js').read_text(encoding='utf-8')
    assert js.count('; with a price, Model B made the pick`') == (1 if sport == 'nhl' else 2), 'every priced line, the Kalshi fallback included'
    assert 'so Model A made' in js
