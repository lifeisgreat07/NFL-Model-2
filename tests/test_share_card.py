"""A game card as an image to share (Stage 80 item 63, the 2026-10-13 UI/UX audit's F13).

Measured 2026-10-15 on the site built from main, at 390 and 1440 px in both
themes: a card could be shared only as a link (the NFL's #game/ address)
or a screenshot; no card on any sport's page offered an image of itself.

Now every card with a saved pick has "Share image": src/core/share_card.js
draws the card's teams, the pick, the split bar, each forecast and, once
graded, how it went, on a 1200 by 630 canvas, and gives the PNG to the
phone's share sheet or, where there is none, downloads it. It draws from
the card's numbers (data-share), never the page: a logo from ESPN or the
NHL would taint the canvas and the image could not be read back.

Run with: pytest tests/test_share_card.py -v
"""
import inspect
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from src.site import build

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / 'src' / 'core' / 'share_card.js').read_text(encoding='utf-8')
APP = (ROOT / 'src' / 'dashboard' / 'app.js').read_text(encoding='utf-8')
NHL = (ROOT / 'src' / 'sports' / 'nhl' / 'pages' / 'nhl.js').read_text(encoding='utf-8')
NBA = (ROOT / 'src' / 'sports' / 'nba' / 'pages' / 'nba.js').read_text(encoding='utf-8')
NODE = shutil.which('node')

CARD = {'sport': 'NFL', 'away': 'SEA', 'home': 'DEN', 'colours': ['#69BE28', '#FB4F14'], 'lead': 'Model B', 'team': 'SEA',
        'pct': 56.2, 'homePct': 43.8, 'when': 'Thursday, Oct 15 · 8:15 PM ET',
        'forecasts': [{'label': 'Model B', 'text': 'SEA 56%'}, {'label': 'Market', 'text': 'SEA 63%'},
                      {'label': 'Model A', 'text': 'DEN 66%'}],
        'result': None, 'score': None}


def node(code):
    if not NODE:
        pytest.skip('node not available')
    r = subprocess.run([NODE, '-e', code], capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def pure():
    return JS[:JS.index('(function(){')]


def function_source(src, name):
    m = re.search(r'function ' + name + r'\(.*?\n\}\n', src, re.S)
    assert m, f'{name} is not findable -- re-anchor this guard'
    return m.group(0)


RECORDER = r"""
function recorder(){
  const calls = [];
  return new Proxy({calls}, {
    get(t, k){ return k in t ? t[k] : (...a) => calls.push([k, ...a]); },
    set(t, k, v){ calls.push(['set ' + k, v]); return true; },
  });
}
"""


def drawn(d, site='example.io/site'):
    return node(pure() + RECORDER + f'const c = recorder(); shareDraw(c, {json.dumps(d)}, {json.dumps(site)});'
                'console.log(JSON.stringify(c.calls));')


# ---------- what the image says ----------

def test_the_image_says_the_game_the_pick_and_every_forecast():
    texts = [c[1] for c in drawn(CARD) if c[0] == 'fillText']
    for want in ('SPORTALYTICS · NFL', 'Thursday, Oct 15 · 8:15 PM ET', 'SEA at DEN', 'Model B: SEA 56% to win',
                 'Model B SEA 56%', 'Market SEA 63%', 'Model A DEN 66%', 'SEA', 'DEN', '50%',
                 'Picked before the game, graded after it.', 'example.io/site'):
        assert want in texts, f'the image does not say {want!r}'


def test_a_graded_card_says_how_it_went_in_its_colour():
    calls = drawn(dict(CARD, result='Missed', score='Final: SEA 20, DEN 23'))
    texts = [c[1] for c in calls if c[0] == 'fillText']
    assert 'Missed' in texts and 'Final: SEA 20, DEN 23' in texts
    at = next(i for i, c in enumerate(calls) if c[:2] == ['fillText', 'Missed'])
    colour = [c[1] for c in calls[:at] if c[0] == 'set fillStyle'][-1]
    assert colour == '#E5636B'
    assert 'Correct' not in [c[1] for c in drawn(CARD) if c[0] == 'fillText'], 'an ungraded card says nothing of a result'


def test_the_bar_draws_the_away_team_first_split_where_the_card_splits():
    calls = drawn(CARD)
    rects = [c for c in calls if c[0] == 'fillRect']
    w = 1200 - 176
    away = next(r for r in rects if r[1] == 88 and r[2] == 300)
    assert away[3] == pytest.approx(w * (100 - 43.8) / 100)
    fills = [c[1] for c in calls if c[0] == 'set fillStyle']
    assert '#69BE28' in fills and '#FB4F14' in fills
    assert fills.index('#69BE28') < fills.index('#FB4F14')


def test_the_pick_line_reads_as_its_card_does():
    line = lambda **k: [c[1] for c in drawn(dict(CARD, **k)) if c[0] == 'fillText'][3]
    assert line() == 'Model B: SEA 56% to win'
    assert line(result='Correct') == 'Model B picked SEA 56%', 'past tense once graded'
    assert line(team='NJD', pct=50.6, even=True) == 'Model B picked NJD 51% · even', 'a saved pick inside the band'
    assert line(team=None, pct=50.6) == 'Model B: too close to call', "the NFL's card, with no side"


def test_nothing_from_another_host_is_drawn():
    assert 'drawImage' not in JS, 'a logo from ESPN or the NHL would taint the canvas: toBlob would fail'


def test_the_file_is_named_for_the_game():
    assert node(pure() + f'console.log(JSON.stringify(shareFileName({json.dumps(CARD)})));') == 'sportalytics-nfl-SEA-at-DEN.png'
    assert node(pure() + 'console.log(JSON.stringify(shareFileName({sport: "NHL", away: "T/BL", home: "<x>"})));') \
        == 'sportalytics-nhl-TBL-at-x.png'


def test_the_footer_names_the_site_not_the_page():
    got = node(pure() + 'console.log(JSON.stringify(["https://a.github.io/NFL-Model-2/nfl/#board/2026_week6",'
                        ' "https://a.github.io/NFL-Model-2/nhl/index.html", "https://a.github.io/NFL-Model-2/"].map(shareSite)));')
    assert got == ['a.github.io/NFL-Model-2'] * 3


# ---------- sharing it ----------

def test_a_phone_gets_its_share_sheet_and_anything_else_a_download():
    run = JS[JS.index('(function(){'):]
    assert "if(navigator.canShare && navigator.canShare({files: [file]})){" in run
    assert "if(e && e.name === 'AbortError') return;" in run, 'closing the share sheet is not a reason to download'
    assert run.index('navigator.share(') < run.index('a.download = name;')
    assert 'URL.revokeObjectURL(url)' in run
    assert 'await document.fonts.ready' in run, "the image is drawn in the site's face, once it has loaded"


# ---------- the cards ----------

@pytest.mark.parametrize('name,src', [('NHL', NHL), ('NBA', NBA)], ids=['nhl', 'nba'])
def test_a_day_boards_card_carries_its_image(name, src):
    helpers = (function_source(src, 'side') + function_source(src, 'sideText')
               + "const EVEN_BAND = 2;\nfunction startLabel(){ return 'Thu, Oct 15 · 7:00 PM ET'; }\n"
               "function escapeHtml(s){ return String(s).replace(/&/g,'&amp;').replace(/\"/g,'&quot;').replace(/</g,'&lt;'); }\n"
               + function_source(src, 'shareAttr'))
    g = {'away': 'BUF', 'home': 'TOR', 'status': 'final', 'hs': 2, 'as': 3, 'lp': 'OT'}
    p = {'a': 0.55, 'b': 0.42, 'market': {'prob': 0.45}, 'colours': ['#003087', '#00205B'], 'result': 'correct'}
    attr = node(helpers + f'console.log(JSON.stringify(shareAttr({json.dumps(g)}, {json.dumps(p)})));')
    assert '"' not in attr, 'the attribute is escaped'
    d = json.loads(attr.replace('&quot;', '"').replace('&lt;', '<').replace('&amp;', '&'))
    assert d == {'sport': name, 'away': 'BUF', 'home': 'TOR', 'colours': ['#003087', '#00205B'], 'lead': 'Model B', 'team': 'BUF', 'even': False,
                 'pct': pytest.approx(58), 'homePct': pytest.approx(42),
                 'forecasts': [{'label': 'Model B', 'text': 'BUF 58%'}, {'label': 'Market', 'text': 'BUF 55%'},
                               {'label': 'Model A', 'text': 'TOR 55%'}],
                 'when': 'Thu, Oct 15 · 7:00 PM ET', 'result': 'Correct', 'score': 'Final: BUF 3, TOR 2 (OT)'}
    even = node(helpers + 'console.log(JSON.stringify(shareAttr({away: "NJD", home: "DET", status: "final", hs: 4, as: 5},'
                          ' {a: 0.53, b: 0.494, market: null, colours: ["#c00", "#f00"], pick: "NJD", result: "correct"})));')
    e = json.loads(even.replace('&quot;', '"').replace('&lt;', '<').replace('&amp;', '&'))
    assert (e['team'], e['even'], round(e['pct'], 1)) == ('NJD', True, 50.6), 'inside the band, the saved pick'
    card = function_source(src, 'pickedCard')
    assert 'data-share="${shareAttr(g, p)}"' in card and '${SHARE_BUTTON}' in card
    assert "const SHARE_BUTTON = '<button type=\"button\" class=\"btn btn-link share-btn\" data-share-card>Share image</button>';" in src
    assert 'data-share' not in function_source(src, 'waitingCard'), 'a game with no saved pick has nothing to share'


def test_the_nfl_card_carries_its_image():
    helpers = ("const CARD_EVEN_BAND = 2;\nfunction kickoffLabel(){ return 'Thursday, Oct 15 · 8:15 PM ET'; }\n"
               "function gameHasScore(g){ return g.home_score !== null && g.home_score !== undefined; }\n"
               "function escapeHtml(s){ return String(s).replace(/&/g,'&amp;').replace(/\"/g,'&quot;').replace(/</g,'&lt;'); }\n"
               + function_source(APP, 'cardSide') + function_source(APP, 'cardSideText') + function_source(APP, 'shareAttr'))
    g = {'away': 'SEA', 'home': 'DEN', 'mktB_home': 43.8, 'mkt_home': 37, 'fbA_home': 66, 'graded': True,
         'model_b_correct': False, 'status': 'final', 'away_score': 20, 'home_score': 23}
    attr = node(helpers + f'console.log(JSON.stringify(shareAttr({json.dumps(g)}, "#69BE28", "#FB4F14")));')
    assert '"' not in attr, 'the attribute is escaped'
    d = json.loads(attr.replace('&quot;', '"').replace('&lt;', '<').replace('&amp;', '&'))
    assert d['lead'] == 'Model B' and d['team'] == 'SEA' and d['homePct'] == 43.8
    assert [f['text'] for f in d['forecasts']] == ['SEA 56%', 'SEA 63%', 'DEN 66%']
    assert d['result'] == 'Missed' and d['score'] == 'Final: SEA 20, DEN 23'
    assert d['colours'] == ['#69BE28', '#FB4F14']
    assert "data-share=\"${shareAttr(g, awayC, homeC)}\">" in APP
    assert '<button type="button" class="btn btn-link share-btn" data-share-card>Share image</button>' in APP


# ---------- the build ----------

PAGE = '<html><body><script>const b = `<button data-share-card>`;</script></body></html>'


def test_the_build_puts_the_script_on_a_page_whose_cards_offer_it(tmp_path):
    page = tmp_path / 'p.html'
    page.write_text(PAGE, encoding='utf-8')
    block = build.share_block()
    assert build.inject_share(page, block) and build.inject_share(page, block)
    html = page.read_text(encoding='utf-8')
    assert html.count('<script data-site-share>') == 1 and 'function shareDraw' in html
    other = tmp_path / 'home.html'
    other.write_text('<html><body>home</body></html>', encoding='utf-8')
    assert not build.inject_share(other, block)


def test_the_build_tries_the_sport_pages_only(tmp_path):
    for s in ('nfl', 'nhl', 'nba'):
        (tmp_path / s).mkdir()
        (tmp_path / s / 'index.html').write_text(PAGE, encoding='utf-8')
    (tmp_path / 'index.html').write_text(PAGE, encoding='utf-8')
    assert build.add_share(tmp_path) == ['nfl/index.html', 'nhl/index.html', 'nba/index.html']
    assert 'data-site-share' not in (tmp_path / 'index.html').read_text(encoding='utf-8')
    assert 'add_share(out)' in inspect.getsource(build.build_site)
