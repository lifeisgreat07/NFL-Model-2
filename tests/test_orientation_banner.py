"""The orientation banner is three lines, and on a phone it sits after the first games.

Stage 13 (CLAUDE.md). The first-visit banner on the Week Board was six
bullets. At 390x844 it was 610px tall and the first game card started at
914px, below the fold, so a phone opened on instructions. It now shows three
lines, keeps the rest behind a native "How to read this" disclosure, and on a
phone is moved in among the cards after the first two. "Got it" still hides
it on this device for good.

orientationSlot() is executed under node; the wiring (re-placed on every
rewrite of the grid and on crossing the phone breakpoint) is held by source
guards, because it needs a browser.

Run with: pytest tests/test_orientation_banner.py -v
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

TEMPLATE = Path(__file__).resolve().parents[1] / 'src' / 'pipeline' / 'dashboard_template.html'
NODE = shutil.which('node')


@pytest.fixture(scope='module')
def src():
    return TEMPLATE.read_text(encoding='utf-8')


@pytest.fixture(scope='module')
def banner(src):
    m = re.search(r'<div id="onboarding-banner".*?\n    </div>\n', src.replace('\r\n', '\n'), re.S)
    assert m, 'the orientation banner is no longer findable -- re-anchor this guard'
    return m.group(0)


@pytest.fixture(scope='module')
def slots(src):
    if not NODE:
        pytest.skip('node not available')
    consts = re.search(r'const ORIENTATION_AFTER = [^;]+;', src)
    fn = re.search(r'function orientationSlot\(.*?\n\}\n', src.replace('\r\n', '\n'), re.S)
    assert consts and fn, 'orientationSlot is not findable -- re-anchor this guard'
    cases = [[16, True], [2, True], [1, True], [0, True], [16, False], [1, False]]
    js = (consts.group(0) + '\n' + fn.group(0) +
          f'\nprocess.stdout.write(JSON.stringify({json.dumps(cases)}.map(([n, p]) => orientationSlot(n, p))));')
    r = subprocess.run([NODE, '-e', js], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return dict(zip(['phone16', 'phone2', 'phone1', 'phone0', 'wide16', 'wide1'], json.loads(r.stdout)))


def test_three_lines_show_and_the_rest_waits_behind_how_to_read_this(banner):
    shown, _, rest = banner.partition('<details')
    assert rest, 'there is no "How to read this" disclosure'
    assert len(re.findall(r'<li>', shown)) == 3, 'the banner no longer shows exactly three lines'
    assert re.search(r'<summary>How to read this</summary>', rest)
    assert len(re.findall(r'<li>', rest)) >= 3, 'the disclosure lost the explanations it holds'
    assert 'onclick="dismissOnboarding()">Got it</button>' in banner, '"Got it" is gone'


def test_the_disclosure_is_a_24px_control_that_shows_its_state(src):
    css = re.sub(r'/\*.*?\*/', '', src.split('</style>')[0], flags=re.S)
    rule = re.search(r'\.onboarding-more summary\{([^}]*)\}', css)
    assert rule and 'min-height:24px' in rule.group(1), 'the "How to read this" toggle is under 24px tall'
    assert re.search(r'\.onboarding-more\[open\] summary::before\{content:', css), (
        'nothing says whether "How to read this" is open')


def test_on_a_phone_the_banner_goes_after_the_first_two_cards(slots):
    assert slots['phone16'] == 2 and slots['phone2'] == 2


def test_with_too_few_cards_or_a_wider_screen_it_stays_home(slots):
    assert slots['phone1'] is None and slots['phone0'] is None, (
        'with fewer than two cards there is nothing to put first; the banner stays in its markup home')
    assert slots['wide16'] is None and slots['wide1'] is None


def test_every_rewrite_of_the_grid_and_every_breakpoint_crossing_re_places_it(src):
    body = re.search(r'\(function placeOrientationWiring\(\)\{.*?\n\}\)\(\);', src.replace('\r\n', '\n'), re.S)
    assert body, 'placeOrientationWiring is gone -- re-anchor this guard'
    code = body.group(0)
    assert "new MutationObserver(placeOrientation).observe(grid, {childList:true})" in code, (
        'renderGames() rewrites the grid with innerHTML; without the observer the banner '
        'is dropped the first time the week, sort or filter changes on a phone')
    assert "phone.addEventListener('change', placeOrientation)" in code, (
        'turning a phone to landscape or resizing past 640px leaves the banner where it was')
    assert re.search(r"const ORIENTATION_PHONE = '\(max-width:640px\)';", src)
    assert re.search(r'\.game-grid > \.onboarding-banner\{grid-column:1 / -1;', src), (
        'inside the grid the banner must span every column')
