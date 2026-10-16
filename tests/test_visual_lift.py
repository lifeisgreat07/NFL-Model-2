"""The numbers' face, the logo watermark, compact spacing and each sport's print (Stage 80 item 64,
the 2026-10-13 UI/UX audit's V1, V2, V4 and V5).

Measured 2026-10-15 on the site built from main, at 390 and 1440 px in both
themes:
- V1: every figure ending in % on a card was set in proportional digits
  (NFL: "DAL 80%", the 50% mark and the three forecasts; NHL: the pick, the
  50% mark, Model A's side, the side column's odds), so a column of them
  did not line up; the card's pick was 20 px, the scoreboard's 24.
- V2: no card carried its team's logo except the two small end logos.
- V4: one spacing only; a day board's row was 52 px.
- V5: the NHL's and NBA's Day Board printed its rows and none of its cards
  (the cards are inside closed rows), with no header saying which sport or
  when; the bars printed in team colours that a black-and-white printer
  turns into the same grey.

Now (styles.css, each sport's body and script, src/core/sheet.js):
every figure takes even-width digits and the big ones the display size; a
card carries the logo of the side it picks, grey and faint; the Settings
sheet's Spacing makes the larger steps half and rows 40 px; and a printed
sheet has a header, the cards two to a page, and grey bars.

Run with: pytest tests/test_visual_lift.py -v
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CSS = (ROOT / 'src' / 'dashboard' / 'styles.css').read_text(encoding='utf-8')
RULES = re.sub(r'\s+', '', CSS)
HOME_CSS = re.sub(r'\s+', '', (ROOT / 'src' / 'site' / 'home' / 'home.css').read_text(encoding='utf-8'))
APP = (ROOT / 'src' / 'dashboard' / 'app.js').read_text(encoding='utf-8')
SPORT_JS = {'nhl': (ROOT / 'src' / 'sports' / 'nhl' / 'pages' / 'nhl.js').read_text(encoding='utf-8'),
            'nba': (ROOT / 'src' / 'sports' / 'nba' / 'pages' / 'nba.js').read_text(encoding='utf-8')}
SHEET = (ROOT / 'src' / 'core' / 'sheet.js').read_text(encoding='utf-8')
SPORT_CSS = {s: re.sub(r'\s+', '', (ROOT / 'src' / 'sports' / s / 'pages' / f'{s}.css').read_text(encoding='utf-8')) for s in ('nhl', 'nba')}
BODIES = {'nfl': ROOT / 'src' / 'dashboard' / 'body.html', 'nhl': ROOT / 'src' / 'sports' / 'nhl' / 'pages' / 'body.html',
          'nba': ROOT / 'src' / 'sports' / 'nba' / 'pages' / 'body.html'}
HEADS = [ROOT / 'src' / 'dashboard' / 'page.html', ROOT / 'src' / 'sports' / 'nhl' / 'pages' / 'page.html',
         ROOT / 'src' / 'sports' / 'nba' / 'pages' / 'page.html', ROOT / 'src' / 'site' / 'home' / 'page.html']
NODE = shutil.which('node')


def node(code):
    if not NODE:
        pytest.skip('node not available')
    r = subprocess.run([NODE, '-e', code], capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def function_source(src, name):
    m = re.search(r'function ' + name + r'\(.*?\n\}\n', src, re.S)
    assert m, f'{name} is not findable -- re-anchor this guard'
    return m.group(0)


def print_block():
    start = CSS.index('@media print{')
    return re.sub(r'\s+', '', CSS[start:CSS.index('@page{', start)])


# ---------- V1 ----------

def test_every_figure_has_even_width_digits():
    assert 'body{font-variant-numeric:tabular-nums;}' in RULES, 'a % anywhere on any page inherits it'


def test_the_big_figures_take_the_display_size():
    assert '--fs-display:24px;' in RULES
    assert '.card-hlb{font-weight:800;font-size:var(--fs-display);font-variant-numeric:tabular-nums;}' in RULES
    assert '.score-pct{font-size:var(--fs-display);font-weight:800;' in RULES
    assert '.home-tileb{font-size:var(--fs-display);font-weight:800;' in HOME_CSS


# ---------- V2 ----------

def test_the_watermark_is_grey_faint_and_behind_everything():
    rule = re.search(r'\.game-card\[style\*="--wm"\]::before\{[^}]*\}', RULES)
    assert rule, 'no watermark rule'
    r = rule.group(0)
    for want in ('filter:grayscale(1)', 'opacity:.06', 'pointer-events:none', 'z-index:-1', 'background:var(--wm)'):
        assert want in r, f'the watermark lacks {want}'
    assert 'position:relative;isolation:isolate;' in RULES, 'z-index:-1 stays inside the card only in its own stacking context'


def test_the_nfl_card_carries_the_picked_sides_logo():
    js = ("const CARD_EVEN_BAND = 2;\nconst ESPN_CODE = {WAS: 'wsh'};\n" + function_source(APP, 'cardSide')
          + function_source(APP, 'teamLogo') + function_source(APP, 'watermark'))
    got = node(js + 'console.log(JSON.stringify([watermark({away: "WAS", home: "DAL", mktB_home: 30, fbA_home: 70}),'
                    ' watermark({away: "TB", home: "DAL", mktB_home: null, fbA_home: 72}),'
                    ' watermark({away: "TB", home: "DAL", mktB_home: 50.4, fbA_home: 72})]));')
    assert got == [" style=\"--wm:url('https://a.espncdn.com/i/teamlogos/nfl/500/wsh.png')\"",
                   " style=\"--wm:url('https://a.espncdn.com/i/teamlogos/nfl/500/dal.png')\"", ''], \
        "Model B's side; Model A's with no market; none on a toss-up"
    assert 'data-share="${shareAttr(g, awayC, homeC)}"${watermark(g)}>' in APP


@pytest.mark.parametrize('sport', ['nhl', 'nba'])
def test_a_day_boards_card_carries_the_picked_sides_logo(sport):
    src = SPORT_JS[sport]
    fn = function_source(src, 'watermark')
    got = node(fn + 'console.log(JSON.stringify([watermark("https://assets.nhle.com/logos/nhl/svg/NJD_dark.svg"),'
                    ' watermark(""), watermark("javascript:alert(1)")]));')
    assert got == [" style=\"--wm:url('https://assets.nhle.com/logos/nhl/svg/NJD_dark.svg')\"", '', '']
    assert '${watermark(logo(p.pick))}>' in function_source(src, 'pickedCard')


# ---------- V4 ----------

def test_compact_spacing_halves_the_larger_steps_and_shortens_rows():
    assert 'html[data-density="compact"]{--s5:10px;--s6:12px;--s7:16px;--s8:20px;}' in RULES
    for sel, rules in (('#game-grid.nfl-row', RULES), ('.nhl-row', SPORT_CSS['nhl']), ('.nba-row', SPORT_CSS['nba'])):
        rows = re.search(r'html\[data-density="compact"\]' + re.escape(sel) + r'\{min-height:(\d+)px;\}', rules)
        assert rows and int(rows.group(1)) == 40, f"{sel}: the audit's 40 px"
        assert int(rows.group(1)) >= 24, 'a row stays a 24 px target'


def test_spacing_is_chosen_in_the_settings_sheet_and_kept():
    assert "{key: 'site:density', label: 'Spacing', note: 'Compact fits more on a screen', reload: false,\n   options: [[null, 'Comfortable'], ['compact', 'Compact']]}," in SHEET
    assert "if(s.key === 'site:density'){\n      if(value) document.documentElement.setAttribute('data-density', value);" in SHEET
    for head in HEADS:
        assert "if(localStorage.getItem('site:density') === 'compact') document.documentElement.setAttribute('data-density','compact');" \
            in head.read_text(encoding='utf-8'), f'{head.parent.name}: the page would open comfortable and then jump'


# ---------- V5 ----------

@pytest.mark.parametrize('sport', ['nhl', 'nba'])
def test_a_printed_day_board_prints_its_cards_two_to_a_sheet(sport):
    css = SPORT_CSS[sport]
    block = css[css.index('@mediaprint{'):]
    assert f'.{sport}-row-detail{{display:block!important;}}' in block, 'the cards inside closed rows'
    assert f'.{sport}-row{{display:none!important;}}' in block
    p = print_block()
    assert '.game-card{min-height:118mm;margin-bottom:6mm;break-inside:avoid;}' in p
    assert '@page{margin:12mm;}' in RULES


def test_the_bars_print_in_two_greys_and_the_watermark_stays_off():
    p = print_block()
    assert '.tele-bar-seg:first-child{background:#3A3F47!important;}' in p
    assert '.tele-bar-seg:last-child{background:#B9BEC6!important;}' in p
    assert '.game-card::before{display:none!important;}' in p
    assert '#site-strip,.day-strip,.week-step-btn,.share-btn,.fav-star{display:none!important;}' in p


@pytest.mark.parametrize('sport,mark', [('nfl', 'favicon.svg'), ('nhl', 'favicon-nhl.svg'), ('nba', 'favicon-nba.svg')])
def test_each_sports_sheet_has_its_own_header(sport, mark):
    body = BODIES[sport].read_text(encoding='utf-8')
    head = re.search(r'<div class="print-head" aria-hidden="true">.*?</div>', body)
    assert head, f'{sport}: no print header'
    h = head.group(0)
    assert f'<img src="../assets/{mark}" alt="">' in h and f'<b>Sportalytics · {sport.upper()}</b>' in h
    assert '<span data-print-date></span>' in h and 'lock' in h
    assert body.index('<main id="main-content"') < body.index('class="print-head"')
    js = APP if sport == 'nfl' else SPORT_JS[sport]
    assert "window.addEventListener('beforeprint', () => {" in js and '`Printed ${at}.`' in js
    assert '.print-head{display:flex!important;}' in print_block()
    assert '.print-head{display:none;' in RULES, 'never on screen'
