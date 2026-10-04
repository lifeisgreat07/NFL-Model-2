"""
Season Accuracy's "How sure, and how right" score (Stage 19, 2026-09-28).

Picking the winner treats a 51% pick and a 95% pick the same. This score is
the average log loss of each forecast's probability for what actually
happened, so a confident miss costs more than a timid one -- the proper
scoring rule this project judges by, shown to a casual reader in plain words
(Mark chose plain wording over an exception to the plain-language guard).

What can go wrong, and is held here:
  - shown too early: one confident miss outweighs the models' differences
    below 50 games, so the score is None until then;
  - scored against the wrong side: a sign slip reads exactly as well;
  - averaged over different games: three forecasts must be scored over one
    set, or the smallest set wins by leaving games out;
  - an extreme probability that lost: infinity must not reach the page;
  - ranked the wrong way round: lower is better.

Run with: pytest tests/test_forecast_score.py -v
"""
import json
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

from src.pipeline import generate_dashboard as gd
from src.pipeline.template_parts import JOINED_TEMPLATE

TEMPLATE = JOINED_TEMPLATE
NODE = shutil.which('node')


def game(a=0.6, b=0.6, m=0.6, won=1):
    return {'model_a_home_win_prob': a, 'model_b_home_win_prob': b,
            'market_prob_home': m, 'actual_home_win': won}


def test_nothing_is_shown_below_fifty_games():
    assert gd.FORECAST_SCORE_MIN_GAMES == 50, (
        'the floor moved off the 50 games Stage 19 planned; change the plan '
        'in CLAUDE.md first, then this')
    assert gd.build_forecast_score([game()] * 49) is None, (
        '49 games produced a score. Below the floor one confident miss moves '
        'it more than the forecasts differ, so it must not reach the page')
    assert gd.build_forecast_score([game()] * 50) is not None


def test_each_forecast_is_scored_on_the_side_that_happened():
    """Mirrored inputs, so a sign slip cannot pass: 0.8 on a home win and 0.2
    on an away win are the same forecast quality and must score the same."""
    home_wins = gd.build_forecast_score([game(a=0.8, won=1)] * 50)
    away_wins = gd.build_forecast_score([game(a=0.2, won=0)] * 50)
    expected = round(-math.log(0.8), 3)
    assert home_wins['model_a'] == expected, home_wins
    assert away_wins['model_a'] == expected, away_wins


def test_a_confident_miss_costs_more_than_a_timid_one():
    """The point of the score, and the sentence the page says about it."""
    s = gd.build_forecast_score([game(a=0.9, b=0.55, won=0)] * 50)
    assert s['model_a'] > s['model_b'], s


def test_all_three_are_scored_over_the_same_games():
    """A game only two forecasts priced is dropped for all three. Otherwise
    the forecast missing it is averaged over fewer games -- here, the one
    game it would have got badly wrong."""
    games = [game(a=0.6, b=0.6, m=0.6, won=1)] * 50
    games.append(game(a=0.95, b=0.95, m=None, won=0))
    s = gd.build_forecast_score(games)
    assert s['n'] == 50, s
    assert s['model_a'] == s['market'] == round(-math.log(0.6), 3), s


def test_a_game_without_a_winner_is_left_out():
    games = [game(won=1)] * 50 + [game(won=None), game(won=0.5)]
    assert gd.build_forecast_score(games)['n'] == 50


def test_a_certain_forecast_that_lost_still_gets_a_finite_score():
    """Unclamped, math.log(0) raises and stops the build; a clamp that let
    infinity through would write a token browsers cannot parse."""
    s = gd.build_forecast_score([game(a=1.0, won=0)] * 50)
    assert math.isfinite(s['model_a']), s
    # And the result survives the trip into the page's JSON.
    json.dumps(s, allow_nan=False)


def test_the_coin_flip_reference_is_what_fifty_fifty_scores():
    s = gd.build_forecast_score([game(a=0.5, won=1)] * 50)
    assert s['coin_flip'] == s['model_a'] == 0.693, s


def test_the_summary_carries_it():
    graded = {(2026, 1): [dict(game(), model_a_correct=1, model_b_correct=1,
                               market_correct=1)] * 50}
    assert gd.build_accuracy_summary(graded)['forecast_score']['n'] == 50
    assert gd.build_accuracy_summary({})['forecast_score'] is None


# ---- the page half, executed in node over the real function ----

def function_source(src, name):
    m = re.search(r'function ' + name + r'\(.*?\n\}\n', src, re.S)
    assert m, f'{name} is not findable -- re-anchor this guard'
    return m.group(0)


@pytest.fixture(scope='module')
def rendered():
    if not NODE:
        pytest.skip('node not available')
    cases = {
        'none': None,
        'b_best': {'n': 64, 'coin_flip': 0.693, 'model_a': 0.671,
                   'model_b': 0.598, 'market': 0.612},
    }
    # Each case is caught separately, so a case that throws fails ITS test
    # with the error in hand, rather than breaking the fixture and every
    # test with it (CLAUDE.md: a guard must fail on its own assertion).
    js = function_source(TEMPLATE.read_text(encoding='utf-8'), 'forecastScoreHtml') + \
        f'\nconst C={json.dumps(cases)};const o={{}};' \
        'for(const k in C){try{o[k]=forecastScoreHtml(C[k]);}catch(e){o[k]="THREW: "+e.message;}}' \
        'process.stdout.write(JSON.stringify(o));'
    r = subprocess.run([NODE, '-e', js], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_no_score_renders_nothing(rendered):
    assert rendered['none'] == '', (
        'a missing score rendered markup; below 50 games the block must be '
        'absent, not an empty table')


def test_best_score_is_listed_first(rendered):
    names = re.findall(r'</span>(Market|Model A|Model B)</td>', rendered['b_best'])
    assert names == ['Model B', 'Market', 'Model A'], (
        f'rows read {names}; lower is better, so the lowest score leads')


def test_the_block_says_which_way_is_better_and_what_a_coin_flip_scores(rendered):
    html = rendered['b_best']
    assert 'Lower is better' in html
    assert '0.693' in html
    assert 'Over the 64 games' in html


def test_the_accuracy_page_draws_it_under_the_scoreboard():
    body = function_source(TEMPLATE.read_text(encoding='utf-8'), 'renderAccuracy')
    assert 'cardsHtml + forecastScoreHtml(accuracy.forecast_score) +' in body


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))
