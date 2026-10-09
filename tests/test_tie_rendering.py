"""
A tied game on the page: "Tie", never "Missed" with a red cross.

Stage 30 item 1, from the 2026-09-29 re-audit. grade_predictions has recorded
a tie as `result: 'tie'` with every `*_correct` null since Stage 25, but the
page never received `result`, and every place that drew a verdict treated
null as a miss:

  - the card's graded tag, `g.model_b_correct ?? g.model_a_correct ?
    'correct' : 'incorrect'`, said "Missed" in the warn colour;
  - pickBadge(picked, true, null) drew the red cross;
  - Team Deep-Dive, whose `won` is null for a tie, said "not yet played".

Now build_games_js carries `result`, and the three are small functions run
here in node over a win, a loss and a tie: gradedTagHtml, pickBadge, and
Team Deep-Dive's diveResultHtml and diveSummaryHtml. A tie counts as graded
(it was checked against the result, so accuracy.n_graded includes it) and
scores for no model (each model's count leaves it out).

Run with: pytest tests/test_tie_rendering.py -v
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from src.core.template_parts import JOINED_TEMPLATE

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = JOINED_TEMPLATE

from src.sports.nfl import generate_dashboard as gd

NODE = shutil.which('node')
FUNCTIONS = ('gradedTagHtml', 'pickBadge', 'diveResultHtml', 'diveSummaryHtml')


def template():
    return TEMPLATE.read_text(encoding='utf-8')


def function_source(src, name):
    m = re.search(r'function ' + name + r'\(.*?\n\}\n', src, re.S)
    assert m, f'{name} is not findable -- re-anchor this guard'
    return m.group(0)


def run(expr):
    if not NODE:
        pytest.skip('node not available')
    js = ''.join(function_source(template(), f) for f in FUNCTIONS) + \
        f'\nprocess.stdout.write(JSON.stringify({expr}));'
    r = subprocess.run([NODE, '-e', js], capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


WIN = {'graded': True, 'result': None, 'model_a_correct': 1, 'model_b_correct': 1}
LOSS = {'graded': True, 'result': None, 'model_a_correct': 0, 'model_b_correct': 0}
TIE = {'graded': True, 'result': 'tie', 'model_a_correct': None, 'model_b_correct': None}


# --- the Week Board card ------------------------------------------------------

def test_a_tie_is_tagged_tie_not_missed():
    tags = run(f'[{json.dumps(WIN)}, {json.dumps(LOSS)}, {json.dumps(TIE)}].map(gradedTagHtml)')
    assert 'Correct' in tags[0] and 'class="graded-tag correct"' in tags[0]
    assert 'Missed' in tags[1] and 'class="graded-tag incorrect"' in tags[1]
    assert tags[2] == '<span class="graded-tag tie">Tie</span>'


def test_a_graded_game_with_no_verdict_is_a_tie_even_without_the_field():
    """Weeks graded before `result` reached the page carry nulls and no
    `result`; they must not fall back to "Missed" either."""
    old = dict(TIE, result=None)
    assert run(f'gradedTagHtml({json.dumps(old)})') == '<span class="graded-tag tie">Tie</span>'


def test_an_ungraded_game_has_no_tag():
    assert run('gradedTagHtml({graded: false})') == ''


def test_a_tie_draws_neither_a_tick_nor_a_cross():
    badges = run('[pickBadge(true, true, 1), pickBadge(true, true, 0), '
                 'pickBadge(true, true, null), pickBadge(true, false, null)]')
    assert 'pick-badge correct' in badges[0]
    assert 'pick-badge incorrect' in badges[1]
    assert badges[2] == '<span class="pick-badge placeholder"></span>'
    assert 'pick-badge picked' in badges[3], "an ungraded pick still shows the model's lean"


def test_the_card_uses_the_tag_function():
    """Wiring: the card must call it, or the executed tests above test
    a function nothing draws."""
    body = function_source(template(), 'renderGames')
    assert 'gradedTagHtml(g)' in body
    assert "'correct':'incorrect'" not in body, 'the inline ternary that drew ties as misses is back'


# --- Team Deep-Dive -----------------------------------------------------------

def test_team_dive_calls_a_tie_a_tie():
    res = run('[diveResultHtml({won: true, tie: false}), diveResultHtml({won: false, tie: false}), '
              'diveResultHtml({won: null, tie: true}), diveResultHtml({won: null, tie: false})]')
    assert '>W<' in res[0] and '>L<' in res[1]
    assert res[2] == '<span class="dive-result tie">T</span>'
    assert 'not yet played' in res[3]


def test_team_dive_record_has_ties_as_a_third_figure_and_no_model_scores_them():
    games = [
        {'won': True, 'tie': False, 'modelACorrect': True, 'modelBCorrect': True},
        {'won': False, 'tie': False, 'modelACorrect': True, 'modelBCorrect': False},
        {'won': None, 'tie': True, 'modelACorrect': None, 'modelBCorrect': None},
        {'won': None, 'tie': False, 'modelACorrect': None, 'modelBCorrect': None},
    ]
    html = run(f'diveSummaryHtml("BUF", {json.dumps(games)})')
    text = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', html)).replace('&middot;', '|')
    assert 'BUF are 1-1-1 across 3 graded games' in text
    assert 'Model A called 2 of 2' in text and 'Model B called 1 of 2' in text


def test_team_dive_with_only_a_tie_still_has_a_record():
    html = run('diveSummaryHtml("BUF", [{won: null, tie: true}])')
    assert '0-0-1' in html and 'None of these games' not in html


def test_team_dive_marks_the_tie_from_the_card_data_and_draws_it():
    src = template()
    assert "tie: !!g.graded && g.result === 'tie'," in function_source(src, 'teamGamesFor')
    body = function_source(src, 'renderTeamGames')
    assert 'diveResultHtml(g)' in body and 'diveSummaryHtml(team, games)' in body


# --- the data -----------------------------------------------------------------

def test_the_page_data_carries_the_result():
    preds = [{'home': 'GB', 'away': 'ATL', 'model_a_home_win_prob': 0.6,
              'model_b_home_win_prob': 0.62, 'market_prob_home': 0.6}]
    tie = {('GB', 'ATL'): {'result': 'tie', 'actual_home_win': None,
                           'model_a_correct': None, 'model_b_correct': None}}
    [g] = gd.build_games_js(preds, tie)
    assert g['graded'] is True and g['result'] == 'tie'
    [g] = gd.build_games_js(preds, {})
    assert g['graded'] is False and g['result'] is None
