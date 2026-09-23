"""
Season Accuracy's scoreboard: Stage 10's one "stop and look" moment (2026-09-23).

Mark chose it from three rendered candidates. It opens the page on a sentence
-- today, "The betting market leads by 1 game." -- and the race that backs it.
A headline sentence generated from numbers is the riskiest copy on the page:
this repo shipped "the betting line agrees" with the sign inverted on all
sixteen cards once (CLAUDE.md, "A sign error in generated prose is
invisible"). So the verdict is executed over ties, leads and unequal game
counts rather than read.

The bars are held to a true zero. "Picked the winner" has a natural baseline
at 50%, and the coin-flip line marks it, but a bar that STARTED at 50% would
turn a one-game gap into a landslide.

Run with: pytest tests/test_scoreboard.py -v
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

TEMPLATE = Path(__file__).parent.parent / 'src' / 'dashboard_template.html'
NODE = shutil.which('node')

MARKET = {'subject': 'The betting market'}
B = {'subject': 'Model B'}
A = {'subject': 'Model A'}

CASES = {
    'market_by_one':  [dict(MARKET, correct=23, n=32), dict(B, correct=22, n=32), dict(A, correct=22, n=32)],
    'b_by_two':       [dict(MARKET, correct=20, n=32), dict(B, correct=22, n=32), dict(A, correct=19, n=32)],
    'two_level':      [dict(MARKET, correct=22, n=32), dict(B, correct=22, n=32), dict(A, correct=19, n=32)],
    'all_level':      [dict(MARKET, correct=22, n=32), dict(B, correct=22, n=32), dict(A, correct=22, n=32)],
    'unequal_counts': [dict(MARKET, correct=23, n=32), dict(B, correct=22, n=31), dict(A, correct=22, n=32)],
}


def template():
    return TEMPLATE.read_text(encoding='utf-8')


def function_source(src, name):
    m = re.search(r'function ' + name + r'\(.*?\n\}\n', src, re.S)
    assert m, f'{name} is not findable -- re-anchor this guard'
    return m.group(0)


@pytest.fixture(scope='module')
def verdicts():
    if not NODE:
        pytest.skip('node not available')
    js = function_source(template(), 'scoreboardVerdict') + \
        f'\nconst C={json.dumps(CASES)};const o={{}};for(const k in C)o[k]=scoreboardVerdict(C[k]);' \
        'process.stdout.write(JSON.stringify(o));'
    r = subprocess.run([NODE, '-e', js], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_a_one_game_lead_is_singular(verdicts):
    assert verdicts['market_by_one'] == 'The betting market leads by 1 game.'


def test_a_bigger_lead_is_plural_and_names_the_leader(verdicts):
    assert verdicts['b_by_two'] == 'Model B leads by 2 games.'


def test_a_shared_lead_says_level_not_leads(verdicts):
    """The case a "leads by N" template gets wrong: a gap of zero is not a
    lead, and 'leads by 0 games' is a sentence that has picked a winner the
    numbers did not."""
    assert verdicts['two_level'] == 'The betting market and Model B are level at the top.'
    assert verdicts['all_level'] == 'All three are level so far.'


def test_unequal_game_counts_do_not_get_a_game_margin(verdicts):
    """A margin in games is only meaningful over the same games."""
    assert verdicts['unequal_counts'] == 'The betting market has the best record so far.'


def test_the_four_cards_are_gone():
    # The element and its rule, not the word: the stylesheet's comment still
    # names the old class to say what replaced it.
    src = template()
    assert not re.search(r'class="[^"]*\baccuracy-cards?\b', src)
    assert not re.search(r'\.accuracy-cards?\s*\{', src)


def test_bars_start_at_zero_with_the_coin_flip_marked():
    body = function_source(template(), 'scoreboardHtml')
    assert re.search(r'width:\$\{r\.pct\}%', body), (
        'the bar width is no longer the percentage itself -- a bar measured '
        'from 50% turns a one-game gap into a landslide')
    css = template()
    assert re.search(r'\.score-coin\{[^}]*left:50%', css), 'the coin-flip line has moved off 50%'


def test_every_row_carries_its_series_colour_and_shape():
    """Colour is series identity (Job 1) and is never alone: each row also
    carries its series' shape, and no two rows share one."""
    body = function_source(template(), 'scoreboardHtml')
    rows = re.findall(r"series: 'var\(--series-(\w)\)', shape: '(\w+)'", body)
    assert sorted(s for s, _ in rows) == ['a', 'b', 'c', 'd'], rows
    shapes = [sh for _, sh in rows]
    assert len(set(shapes)) == len(shapes), f'two rows share a shape: {shapes}'


def test_my_picks_joins_only_with_picks():
    body = function_source(template(), 'scoreboardHtml')
    assert re.search(r"if\(mine\) race\.push\(", body)
    assert "mine ? '' : '<div class=\"score-foot\">" in body
