"""The first-visit tour on the NFL's Week Board (Stage 80 item 58, the 2026-10-13 UI/UX audit's F12).

Measured 2026-10-14 on the NFL page built from main, a new browser, at 390
and 1440 px in both themes: a first visit met a 94 px banner of three
bullets (one line and "How to read a card" on a phone) and nothing that
pointed at the board itself. Mark chose the three-step spotlight as mocked
(2026-10-14), for new visitors only. Now a first visit is walked through
three steps, each a ring round one part of the board with a line beside it:
the week stepper, a game (a phone's row, a wide screen's card), and its
result. Skip, Esc or Done ends it, and it never runs again in that browser
(site:tour); a browser that has been here before, which has left one of the
site's keys, never sees it. The Settings sheet's "Show them again" asks for
it once more.

Run with: pytest tests/test_first_visit_tour.py -v
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / 'src' / 'dashboard' / 'app.js').read_text(encoding='utf-8')
CSS = (ROOT / 'src' / 'dashboard' / 'styles.css').read_text(encoding='utf-8')
SHEET = (ROOT / 'src' / 'core' / 'sheet.js').read_text(encoding='utf-8')
NODE = shutil.which('node')


def fn(name):
    m = re.search(r'function %s\(.*?\n\}\n' % name, APP, re.S)
    assert m, f'{name} is not findable -- re-anchor this guard'
    return m.group(0)


def node(code):
    if not NODE:
        pytest.skip('node not available')
    r = subprocess.run([NODE, '-e', code], capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def wanted(seed, throws=False):
    store = ("function store(seed){ const m = Object.assign({}, seed), ks = Object.keys(m); return {getItem: k => k in m ? m[k] : null,"
             " get length(){ return ks.length; }, key: i => ks[i]}; }\n")
    bad = "const s = {getItem(){ throw new Error('blocked'); }};\n" if throws else f"const s = store({json.dumps(seed)});\n"
    return node(store + "const TOUR_KEY = 'site:tour';\n" + fn('tourWanted') + bad + 'console.log(JSON.stringify(tourWanted(s)));')


def test_a_new_browser_gets_the_tour():
    assert wanted({}) is True
    assert wanted({'unrelated': '1'}) is True, "another site's key on the same host is not a visit here"


@pytest.mark.parametrize('key', ['site:theme', 'site:favs', 'nfl_pickem_my_picks', 'nfl_pickem_onboarding_dismissed', 'nhl:theme', 'site:lastVisit'])
def test_a_browser_that_has_been_here_does_not(key):
    assert wanted({key: '1'}) is False


def test_once_seen_never_again_unless_asked_and_a_blocked_store_never():
    assert wanted({'site:tour': 'done'}) is False
    assert wanted({'site:tour': 'show', 'site:theme': 'dark'}) is True, '"Show them again" asks for it once more'
    assert wanted({}, throws=True) is False
    assert "const SHEET_TOUR = 'site:tour';" in SHEET and "const TOUR_KEY = 'site:tour';" in APP


def test_three_steps_as_mocked():
    steps = node(re.search(r'^const TOUR_STEPS = \[.*?\n\];\n', APP, re.S | re.M).group(0) + 'console.log(JSON.stringify(TOUR_STEPS));')
    assert [s['title'] for s in steps] == ['Step through the weeks', 'Every game, both models', 'Graded after the game']
    assert steps[0]['target'] == ['#week-step']
    assert steps[1]['target'] == ['.game-row.nfl-row', '.game-card'], "a phone's row first, a wide screen's card"
    assert steps[2]['target'][0] == '.nfl-row-res.correct, .nfl-row-res.incorrect' and '.graded-tag' in steps[2]['target']
    assert 'The arrows, or [ and ], move a week at a time.' in steps[0]['text']


def test_a_step_points_at_what_is_drawn():
    body = fn('tourTarget')
    assert "x.getBoundingClientRect().width > 0 && !x.closest('[hidden]')" in body, "a closed row's card is not drawn"


def test_it_runs_on_the_week_board_once_the_page_has_settled():
    start = fn('startTour')
    assert "if(!page || !page.classList.contains('active') || !tourWanted(localStorage)) return;" in start
    assert "window.addEventListener('load', () => setTimeout(startTour, 300));" in APP
    assert "if(location.hash && !/^#board(\\/|$)/.test(location.hash)) return;" in start, 'an arrival at one game is not walked away from it'


def test_leaving_the_week_board_ends_it():
    start = fn('startTour')
    assert "const leave = new MutationObserver(() => { if(!page.classList.contains('active')) end(); });" in start
    assert "leave.observe(page, {attributes: true, attributeFilter: ['class']});" in start, \
        'the browser checks found its card over the Ratings and Model Lab pages'


def test_skip_esc_and_done_end_it_for_good_and_the_focus_is_kept():
    start = fn('startTour')
    assert "try{ localStorage.setItem(TOUR_KEY, 'done'); }catch(e){}" in start
    assert "if(e.key === 'Escape'){ e.preventDefault(); e.stopPropagation(); end(); }" in start
    assert "if(e.target.closest('[data-tour-skip]')) end();" in start
    assert "at === TOUR_STEPS.length - 1 ? end() : show(at + 1);" in start
    assert "pop.querySelector('[data-tour-next]').focus();" in start and "if(back && back.focus) back.focus();" in start
    assert "pop.setAttribute('role', 'dialog');" in start and "pop.setAttribute('aria-labelledby', 'tour-title');" in start


def test_the_ring_dims_the_rest_of_the_page():
    assert 'box-shadow:0 0 0 9999px color-mix(in srgb, var(--bg) 72%, transparent);' in CSS
    assert '.tour-ring{position:absolute; z-index:85;' in CSS and 'pointer-events:none;' in CSS
