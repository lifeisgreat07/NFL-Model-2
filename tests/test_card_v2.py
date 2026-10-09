"""The Week Board card's probability line (Stage 17, card v2).

Mark chose "B refined" on 2026-09-27 from rendered side-by-sides: the
team-colour bar is kept and split by Model B; the three probabilities sit on
one line beneath it, on the same scale, in the shapes Season Accuracy uses;
markers that would hide one another take fixed lanes; a line names a
disagreement only when Model A picks the other team. The functions are run
in node over real week-3 numbers rather than read.

Run with: pytest tests/test_card_v2.py -v
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


def src():
    return TEMPLATE.read_text(encoding='utf-8').replace('\r\n', '\n')


def fn(s, name):
    m = re.search(r'function ' + name + r'\(.*?\n\}\n', s, re.S)
    assert m, f'{name} is not findable -- re-anchor this guard'
    return m.group(0)


def const(s, name):
    m = re.search(r'const ' + name + r' = .*?;\n', s, re.S)
    assert m, f'{name} is not findable -- re-anchor this guard'
    return m.group(0)


def run(expr):
    if not NODE:
        pytest.skip('node not available')
    s = src()
    js = ''.join(const(s, c) for c in ('CARD_EVEN_BAND', 'CARD_SERIES', 'CARD_NEAR', 'CARD_LANE',
                                       'ESPN_CODE'))
    js += ''.join(fn(s, f) for f in ('cardSide', 'cardLanes', 'cardSideText', 'cardAria',
                                     'modelsSplit', 'cardDisagreement', 'gameHasScore', 'cardProvisional', 'cardProbHtml', 'pickBadge',
                                     'markerPath', 'teamLogo', 'barTeam'))
    r = subprocess.run([NODE, '-e', js + f'\nprocess.stdout.write(JSON.stringify({expr}));'],
                       capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


# Real week-3 games, home-side percentages as the page stores them.
ATL_GB = {'away': 'ATL', 'home': 'GB', 'fbA_home': 75.4, 'mktB_home': 68.4, 'mkt_home': 74.9}
KC_MIA = {'away': 'KC', 'home': 'MIA', 'fbA_home': 57.4, 'mktB_home': 13.8, 'mkt_home': 11.0}
LAC_BUF = {'away': 'LAC', 'home': 'BUF', 'fbA_home': 64.8, 'mktB_home': 74.3, 'mkt_home': 78.1}


def test_both_bar_ends_carry_their_team():
    """Executed: the card draws each end of the bar through barTeam(), logo
    then abbreviation. A bare abbreviation on either end fails here (Stage 31
    item 12 moved this from a text check in test_game_card_header.py)."""
    html = run(f'cardProbHtml({json.dumps(dict(ATL_GB, graded=False))}, "#a00", "#fb1")')
    ends = re.findall(r'<span class="card-end-team">.*?</span>', html)
    assert len(ends) == 2, ends
    assert ends[0].endswith('ATL</span>') and ends[1].endswith('GB</span>'), ends
    assert all('<img' in e for e in ends), 'an end of the bar lost its logo'


def test_a_side_is_named_by_the_half_of_the_line_it_falls_in():
    got = run(f'[cardSide(68.4, {json.dumps(ATL_GB)}), cardSide(13.8, {json.dumps(KC_MIA)}), '
              f'cardSide(51.0, {json.dumps(ATL_GB)}), cardSide(null, {json.dumps(ATL_GB)})]')
    assert got[0] == {'team': 'GB', 'pct': 68.4}
    assert got[1]['team'] == 'KC' and got[1]['pct'] == pytest.approx(86.2)
    assert got[2] == {'team': None, 'pct': 51.0}, 'within two points of 50 nobody is picked'
    assert got[3] is None


def test_the_threshold_clears_a_marker_on_the_narrowest_line():
    """176px is the narrowest line measured (a 360px screen); a 12px marker
    is 6.8 points of it, so markers further apart than CARD_NEAR share a lane
    without touching."""
    near = float(re.search(r'const CARD_NEAR = ([\d.]+);', src()).group(1))
    size = float(re.search(r'class="card-mk"[^`]*width="(\d+)"', src()).group(1))
    assert near >= size / 176 * 100


def test_markers_that_would_touch_take_fixed_lanes():
    lanes = run('cardLanes({b: 68.4, a: 75.4, market: 74.9})')
    assert lanes == {'b': 0, 'a': 1, 'market': -1}, 'the market goes above, Model A below'
    # 3.8 points apart: close enough to touch on a phone, so the market moves up.
    assert run('cardLanes({b: 74.3, a: 64.8, market: 78.1})') == {'b': 0, 'a': 0, 'market': -1}
    assert run('cardLanes({b: 60, a: 70, market: 80})') == {'b': 0, 'a': 0, 'market': 0}
    assert run('cardLanes({b: 70, a: 60, market: null})') == {'b': 0, 'a': 0}


def test_disagreement_is_named_only_when_model_a_picks_the_other_team():
    assert run(f'cardDisagreement({json.dumps(KC_MIA)})') == (
        'Model A picks <b>MIA</b>; Model B and the market pick <b>KC</b>.')
    assert run(f'cardDisagreement({json.dumps(ATL_GB)})') == ''
    even = dict(KC_MIA, fbA_home=50.5)
    assert run(f'cardDisagreement({json.dumps(even)})') == '', 'an even call is not a disagreement'
    market_other = dict(KC_MIA, mkt_home=60.0)
    assert run(f'cardDisagreement({json.dumps(market_other)})') == (
        'Model A picks <b>MIA</b>; Model B picks <b>KC</b>.')


def test_the_card_leads_with_model_b_and_keys_b_market_a_in_that_order():
    html = run(f'cardProbHtml(Object.assign({json.dumps(ATL_GB)}, {{graded:false}}), "#a00", "#fb1")')
    assert '<span class="card-hl-label">Model B</span> <b>GB 68%</b>' in html
    keys = re.findall(r'</svg>(Model B|Market|Model A) <b>', html)
    assert keys == ['Model B', 'Market', 'Model A']
    assert 'aria-label="Model B GB 68%. Market GB 75%. Model A GB 75%."' in html


def test_the_bar_is_split_by_model_b():
    html = run(f'cardProbHtml(Object.assign({json.dumps(ATL_GB)}, {{graded:false}}), "#a00", "#fb1")')
    segs = re.findall(r'class="tele-bar-seg" style="width:([\d.]+)%', html)
    assert [float(x) for x in segs] == pytest.approx([31.6, 68.4])


def test_a_card_with_no_market_figure_leaves_the_market_out():
    g = dict(ATL_GB, mkt_home=None, graded=False)
    html = run(f'cardProbHtml({json.dumps(g)}, "#a00", "#fb1")')
    assert 'Market' not in html and html.count('class="card-mk"') == 2


def test_too_close_to_call_is_said_rather_than_picked():
    g = dict(ATL_GB, mktB_home=50.8, graded=False)
    html = run(f'cardProbHtml({json.dumps(g)}, "#a00", "#fb1")')
    assert '<b>Too close to call</b>' in html and 'to win' not in html


def test_the_cards_series_are_season_accuracys():
    s = src()
    series = re.search(r'const SERIES = \{(.*?)\n\};', s, re.S).group(1)
    card = re.search(r'const CARD_SERIES = \{(.*?)\n\};', s, re.S).group(1)
    for key in ('a', 'b', 'market'):
        row = re.search(rf"\n  {key}:\s*\{{label:'([^']+)',\s*color:'([^']+)',\s*shape:'([^']+)'", series).groups()
        crow = re.search(rf"\n  {key}:\s*\{{label:'([^']+)',\s*color:'([^']+)',\s*shape:'([^']+)'", card).groups()
        assert row == crow, (key, row, crow)


def test_the_board_draws_one_card_body_and_no_model_rows():
    body = fn(src(), 'renderGames')
    assert '${cardProbHtml(g, awayC, homeC)}' in body
    assert 'model-row' not in body


def test_the_market_probability_reaches_the_page():
    games = gd.build_games_js([{'away': 'ATL', 'home': 'GB', 'model_a_home_win_prob': 0.754,
                                'model_b_home_win_prob': 0.684, 'market_prob_home': 0.7493},
                               {'away': 'LAC', 'home': 'BUF', 'model_a_home_win_prob': 0.6}], {})
    assert games[0]['mkt_home'] == 74.9
    assert games[1]['mkt_home'] is None, 'absent stays absent'
