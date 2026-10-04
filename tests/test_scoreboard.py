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

import pytest

from src.pipeline.template_parts import JOINED_TEMPLATE

TEMPLATE = JOINED_TEMPLATE
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


# scoreboardHtml run in node (Stage 31 item 12 moved these from text checks
# of its source): once with the visitor's own picks and a left-out sentence,
# once with neither. Percentages are chosen so no two rows share one.
BOARD_O = {'market': {'correct': 23, 'n': 32, 'pct': 71.9},
           'model_b': {'correct': 22, 'n': 32, 'pct': 68.8},
           'model_a': {'correct': 20, 'n': 32, 'pct': 62.5}}
BOARD_MINE = {'correct': 5, 'n': 9, 'pct': 55.6}
BOARD_LEFT = 'Two picks made after kickoff are left out.'
# One more game graded than any row decided: a tie, which is graded and
# decides nothing (the rule in tests/test_tie_rendering.py).
BOARD_GRADED = 33
# Every graded game a tie: each row has decided nothing, so pct is null,
# exactly as build_accuracy_js's totals() writes it when n is 0.
BOARD_ALL_TIES = {k: {'correct': 0, 'n': 0, 'pct': None} for k in ('market', 'model_b', 'model_a')}
ROW = re.compile(r'<span class="score-mark (\w+)" style="--series:var\(--series-(\w)\)"[^>]*></span>([^<]+)</div>'
                 r'\s*<div class="score-track"[^>]*><div class="score-fill" style="--series:var\(--series-\w\); '
                 r'width:([^%"]*)%"')


@pytest.fixture(scope='module')
def boards():
    """{'mine': html, 'none': html, 'ties': html} from scoreboardHtml itself, or {'error':
    stderr} if it threw. Not asserted here: a failing fixture errors every
    test that uses it, and none of them would then report which rule broke."""
    if not NODE:
        pytest.skip('node not available')
    src = template()
    js = (function_source(src, 'scoreboardVerdict') + function_source(src, 'scoreboardHtml') +
          f'const O={json.dumps(BOARD_O)};'
          f'process.stdout.write(JSON.stringify({{mine: scoreboardHtml(O, {json.dumps(BOARD_MINE)}, '
          f'{json.dumps(BOARD_LEFT)}, {BOARD_GRADED}), none: scoreboardHtml(O, null, "", {BOARD_GRADED}), '
          f'ties: scoreboardHtml({json.dumps(BOARD_ALL_TIES)}, null, "", 2)}}));')
    r = subprocess.run([NODE, '-e', js], capture_output=True, text=True, encoding='utf-8')
    if r.returncode != 0:
        return {'error': r.stderr[-800:]}
    return json.loads(r.stdout)


def ran(boards):
    assert 'error' not in boards, f"scoreboardHtml threw: {boards['error']}"
    return boards


def rows_of(html):
    """[(name, shape, series letter, bar width as written)] in the order
    drawn. The width stays text: a row with no record draws 'undefined'."""
    return [(name, shape, series, width) for shape, series, name, width in ROW.findall(html)]


def test_bars_start_at_zero_with_the_coin_flip_marked(boards):
    """Each bar's width is its record's percentage: measured from zero. A bar
    that started at the 50% coin-flip line would turn a one-game gap into a
    landslide."""
    ran(boards)
    got = {name: width for name, _, _, width in rows_of(boards['mine'])}
    assert got == {'Market': '71.9', 'Model B': '68.8', 'Model A': '62.5', 'My picks': '55.6'}, got
    css = template()
    assert re.search(r'\.score-coin\{[^}]*left:50%', css), 'the coin-flip line has moved off 50%'


def test_every_row_carries_its_series_colour_and_shape(boards):
    """Colour is series identity (Job 1) and is never alone: each row also
    carries its series' shape, and no two rows share one."""
    ran(boards)
    rows = rows_of(boards['mine'])
    assert sorted(series for _, _, series, _ in rows) == ['a', 'b', 'c', 'd'], rows
    shapes = [shape for _, shape, _, _ in rows]
    assert len(set(shapes)) == len(shapes), f'two rows share a shape: {shapes}'


def test_my_picks_joins_only_with_picks(boards):
    """With picks, the visitor's row joins the race, last; without, it is
    absent and the board invites them to pick instead."""
    ran(boards)
    with_picks, without = rows_of(boards['mine']), rows_of(boards['none'])
    assert [r[0] for r in with_picks][-1] == 'My picks', with_picks
    assert 'My picks' not in [r[0] for r in without], without
    assert len(without) == 3, without
    invite = 'Pick some games on the Week Board to join this race.'
    assert invite in boards['none'] and invite not in boards['mine']


def test_the_left_out_sentence_is_printed(boards):
    """renderAccuracy hands the scoreboard a sentence saying which picks it
    left out (tests/test_my_picks_kickoff_lock.py holds that wiring); the
    board must print it, and print nothing when there is nothing to say."""
    ran(boards)
    assert f'{BOARD_LEFT} Only picks made before kickoff are counted.' in boards['mine']
    assert 'Only picks made before kickoff' not in boards['none']



def test_the_eyebrow_counts_every_graded_game_a_tie_included(boards):
    """The eyebrow says how many games were graded, which by the recorded rule
    includes a tie. It printed the market row's n until Stage 35, one short on
    a tie week and disagreeing with the calibration text's accuracy.n_graded."""
    ran(boards)
    assert f'Picked the winner &middot; {BOARD_GRADED} games graded' in boards['none']
    assert 'Picked the winner &middot; 32 games' not in boards['none']


def test_a_board_of_only_ties_renders_without_a_record(boards):
    """Every graded game a tie: no row has decided a game, pct is null, and the
    board must still render -- no bar, a dash, "0 of 0", and a verdict that
    does not call three empty records "level". r.pct.toFixed(1) on null threw
    and took the whole Season Accuracy page down with it."""
    ran(boards)
    html = boards['ties']
    assert {w for *_, w in rows_of(html)} == {'0'}, rows_of(html)
    assert html.count('<span class="score-pct">&ndash;</span>') == 3, html
    assert html.count('0 of 0') == 3
    assert 'No graded game has a winner yet.' in html and 'level' not in html
    assert 'Picked the winner &middot; 2 games graded' in html
