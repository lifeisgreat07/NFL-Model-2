"""The Settings sheet and the keyboard shortcuts (Stage 80 item 57, the 2026-10-13 UI/UX audit's F10 and F11).

Measured 2026-10-14 on the site built from main, at 390 and 1440 px in both
themes: no page had settings (the theme button was the one choice, and it
could not go back to the device's), every start was printed in Eastern time
whatever the visitor's zone, "?" did nothing, and on the NHL's and NBA's day
boards [ and ] stepped whole weeks, so there was no key for a day. Mark
chose the sheet and the panel as mocked (2026-10-14).

Now a Settings button (the sidebar's, the phone's More sheet's, the home's
footer) opens a sheet: the theme (light, dark or the device's), times in
Eastern or the visitor's own zone, full or compact cards, the page the site
opens on, and the dismissed tips shown again, each kept in this browser
under a site: key. "?" shows the shortcuts. On a day board [ and ] step a
day, and Shift with them a week. src/core/prefs.js is the time setting every
sport's page reads (the NFL's app.js carries the same text); src/core/sheet.js
is the sheet, put on each page by the site build.

Run with: pytest tests/test_settings_sheet.py -v
"""
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from src.site import build

ROOT = Path(__file__).resolve().parents[1]
PREFS = (ROOT / 'src' / 'core' / 'prefs.js').read_text(encoding='utf-8')
SHEET = (ROOT / 'src' / 'core' / 'sheet.js').read_text(encoding='utf-8')
APP = (ROOT / 'src' / 'dashboard' / 'app.js').read_text(encoding='utf-8')
NHL = (ROOT / 'src' / 'sports' / 'nhl' / 'pages' / 'nhl.js').read_text(encoding='utf-8')
NBA = (ROOT / 'src' / 'sports' / 'nba' / 'pages' / 'nba.js').read_text(encoding='utf-8')
CSS = (ROOT / 'src' / 'dashboard' / 'styles.css').read_text(encoding='utf-8')
NODE = shutil.which('node')
STORE = ("function store(seed){ const m = Object.assign({}, seed); return {getItem: k => k in m ? m[k] : null,"
         " setItem: (k, v) => { m[k] = String(v); }}; }\n")


def fn(src, name):
    m = re.search(r'function %s\(.*?\n\}\n' % name, src, re.S)
    assert m, f'{name} is not findable -- re-anchor this guard'
    return m.group(0)


def node(code, tz='America/New_York'):
    if not NODE:
        pytest.skip('node not available')
    r = subprocess.run([NODE, '-e', code], capture_output=True, encoding='utf-8', env={**os.environ, 'TZ': tz})
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def prefs_body():
    return PREFS[PREFS.index('const TZ_KEY'):]


# ---------- times ----------

def test_a_start_is_eastern_unless_the_visitor_chose_their_own():
    got = node(STORE + "let localStorage = store({});\n" + prefs_body()
               + "const a = [startZone(), startMark()];\n"
               + "localStorage = store({'site:tz': 'local'});\nconst b = [startZone() === undefined, startMark()];\n"
               + "localStorage = {getItem(){ throw new Error('blocked'); }};\nconst c = [startZone(), startMark()];\n"
               + "console.log(JSON.stringify([a, b, c]));")
    assert got == [['America/New_York', ' ET'], [True, ''], ['America/New_York', ' ET']], 'storage that throws keeps Eastern'


def test_the_nfl_carries_the_same_functions():
    assert prefs_body() in APP, 'app.js and src/core/prefs.js have drifted apart'


def eastern(day, clock):
    head = re.search(r'^const ET_PARTS = .*?;\n', APP, re.S | re.M).group(0)
    return node(head + fn(APP, 'etInstant') + f"console.log(JSON.stringify(new Date(etInstant('{day}', '{clock}')).toISOString()));")


def test_an_eastern_date_and_clock_is_the_right_instant_either_side_of_daylight_saving():
    assert eastern('2026-10-15', '20:15') == '2026-10-16T00:15:00.000Z'
    assert eastern('2026-12-03', '20:15') == '2026-12-04T01:15:00.000Z'
    assert eastern('2026-11-01', '13:00') == '2026-11-01T18:00:00.000Z', 'the day Eastern falls back'
    assert eastern('2027-03-14', '13:00') == '2027-03-14T17:00:00.000Z', 'the day it springs forward'


def kickoff(g, tz, setting):
    head = (STORE + f"const localStorage = store({json.dumps(setting)});\n" + prefs_body()
            + "const KICKOFF_MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];\n"
            + re.search(r'^const ET_PARTS = .*?;\n', APP, re.S | re.M).group(0))
    return node(head + fn(APP, 'etInstant') + fn(APP, 'kickoffClock') + fn(APP, 'kickoffLocalLabel') + fn(APP, 'kickoffLabel')
                + f"const g = {json.dumps(g)};\nconsole.log(JSON.stringify([kickoffLabel(g), kickoffClock(g)]));", tz)


GAME = {'gameday': '2026-10-08', 'gametime_et': '20:15', 'weekday': 'Thursday'}


def test_an_nfl_start_is_printed_where_the_visitor_asked():
    assert kickoff(GAME, 'America/Los_Angeles', {}) == ['Thursday, Oct 8 · 8:15 PM ET', '8:15 PM'], 'Eastern, as before'
    assert kickoff(GAME, 'America/Los_Angeles', {'site:tz': 'local'}) == ['Thursday, Oct 8 · 5:15 PM', '5:15 PM']
    assert kickoff(GAME, 'Asia/Tokyo', {'site:tz': 'local'}) == ['Friday, Oct 9 · 9:15 AM', '9:15 AM'], 'the day moves with it'


def test_every_nfl_start_goes_through_the_setting():
    assert 'if(!startZone()) return kickoffLocalLabel(g);' in fn(APP, 'kickoffLabel')
    assert "const time = g.gametime_et ? kickoffClock(g) : '';" in fn(APP, 'phoneRowHtml')
    assert '${kickoffClock(g)}' in fn(APP, 'compareKick')
    assert fn(APP, 'slotHeadBefore').count('kickoffLabel(') == 1


@pytest.mark.parametrize('src,name', [(NHL, 'nhl'), (NBA, 'nba')], ids=['nhl', 'nba'])
def test_the_day_sports_print_a_start_in_the_chosen_zone(src, name):
    for fmt in ('FMT_TIME', 'FMT_HOUR'):
        assert f"const {fmt} = new Intl.DateTimeFormat('en-US', {{hour: 'numeric', minute: '2-digit', timeZone: startZone()}});" in src, (name, fmt)
    assert "${startMark()}" in fn(src, 'startLabel') and ' ET`' not in fn(src, 'startLabel')
    assert "const FMT_ET_DATE = new Intl.DateTimeFormat('en-CA', {year: 'numeric', month: '2-digit', day: '2-digit', timeZone: ET});" in src, \
        "a game's day is still the league's"
    page = (ROOT / 'src' / 'sports' / name / 'pages' / 'page.html').read_text(encoding='utf-8')
    assert '{% include "favs.js" %}\n{% include "prefs.js" %}\n' in page
    site = (ROOT / 'src' / 'sports' / name / 'site.py').read_text(encoding='utf-8')
    assert """.replace('{% include "prefs.js" %}', PREFS_JS.read_text(encoding='utf-8'))""" in site


# ---------- the keys ----------

@pytest.mark.parametrize('src', [NHL, NBA], ids=['nhl', 'nba'])
def test_on_a_day_board_brackets_step_a_day_and_shift_a_week(src):
    keys = node(fn(src, 'dayKeyStep') + "const k = (key, shiftKey = false, ctrlKey = false) => dayKeyStep({key, shiftKey, ctrlKey, metaKey: false, altKey: false});\n"
                "console.log(JSON.stringify([k('['), k(']'), k('{', true), k('}', true), k(']', true), k('[', false, true), k('a')]));")
    assert keys == [{'by': -1, 'week': False}, {'by': 1, 'week': False}, {'by': -1, 'week': True}, {'by': 1, 'week': True},
                    {'by': 1, 'week': True}, None, None]
    assert 'if(step.week) stepWeek(step.by); else stepDay(step.by);' in src


@pytest.mark.parametrize('src', [NHL, NBA], ids=['nhl', 'nba'])
def test_a_day_past_the_weeks_edge_opens_the_next_week(src):
    harness = ("let WEEK_KEYS = ['2026-10-05', '2026-10-12'], currentWeek = '2026-10-05', currentDay = '2026-10-11', drawn = [];\n"
               "function weekDays(w){ const d = new Date(w + 'T00:00:00Z'); return [...Array(7)].map((_, i) => new Date(d.getTime() + i * 864e5).toISOString().slice(0, 10)); }\n"
               "function renderBoard(){ drawn.push(currentDay); }\nfunction replaceRoute(){}\n")
    got = node(harness + fn(src, 'stepDay') + "stepDay(1); stepDay(-1); stepDay(-1); currentWeek = '2026-10-12'; currentDay = '2026-10-18'; stepDay(1);\n"
               "console.log(JSON.stringify(drawn));")
    assert got == ['2026-10-12', '2026-10-11', '2026-10-10'], 'Sunday to the next Monday and back; the last week goes no further'


def test_the_buttons_name_their_keys():
    for sport in ('nhl', 'nba'):
        body = (ROOT / 'src' / 'sports' / sport / 'pages' / 'body.html').read_text(encoding='utf-8')
        assert 'id="week-prev" aria-label="Previous week" aria-keyshortcuts="Shift+["' in body
        assert 'id="week-next" aria-label="Next week" aria-keyshortcuts="Shift+]"' in body
        assert f'id="{sport}-day-strip" aria-label="Days of this week" aria-keyshortcuts="[ ]"' in body


# ---------- the sheet ----------

def test_the_sheet_offers_the_mocked_settings_under_site_keys():
    got = node(SHEET[:SHEET.index('(function(){')] + 'console.log(JSON.stringify([SHEET_SETTINGS, SHEET_TIPS, SHEET_TOUR]));')
    settings, tips, tour = got
    assert [(s['key'], [o[1] for o in s['options']]) for s in settings] == [
        ('site:theme', ['Light', 'Dark', 'Device']), ('site:tz', ['Your time', 'Eastern']),
        ('site:cards', ['Full', 'Compact']), ('site:density', ['Comfortable', 'Compact']),  # Stage 80 item 64 (V4)
        ('site:start', ['Home', 'NFL', 'NHL', 'NBA'])]
    assert [o[0] for o in settings[0]['options']] == ['light', 'dark', None], "the device's theme is no saved choice"
    assert tips == ['nfl_pickem_onboarding_dismissed'] and tour == 'site:tour'
    assert "      put(SHEET_TOUR, 'show');\n" in SHEET, '"Show them again" asks for the tour once more'


def test_the_sheet_is_a_dialog_that_keeps_the_focus_and_question_mark_opens_the_keys():
    assert '<div class="sheet-dialog" role="dialog" aria-modal="true" aria-labelledby="sheet-title">' in SHEET
    assert "if(e.key === 'Escape'){ e.preventDefault(); close(); return; }" in SHEET
    assert "else if(!e.shiftKey && i === stops.length - 1){ e.preventDefault(); stops[0].focus(); }" in SHEET
    assert "if(e.key === '?' && !typing && !e.ctrlKey && !e.metaKey && !e.altKey && shell.hidden){" in SHEET
    assert "if(back && back.focus) back.focus();" in SHEET
    assert "if(s.key === 'site:theme') SHEET_OLD_THEMES.forEach(k => put(k, null));" in SHEET
    assert 'aria-pressed="${v === on}"' in SHEET


def test_compact_cards_and_the_opening_sport_are_read_before_the_page_draws():
    for rel in ('src/dashboard/page.html', 'src/sports/nhl/pages/page.html', 'src/sports/nba/pages/page.html'):
        page = (ROOT / rel).read_text(encoding='utf-8')
        assert "if(localStorage.getItem('site:cards') === 'compact') document.documentElement.setAttribute('data-cards','compact');" in page, rel
    assert 'html[data-cards="compact"] .game-card > :is(.card-keys, .market-ref, .card-qbs, .why-by,' in CSS
    home = (ROOT / 'src' / 'site' / 'home' / 'page.html').read_text(encoding='utf-8')
    assert "if(/^(nfl|nhl|nba)$/.test(start || '') && !fromSite && !location.hash) location.replace(start + '/');" in home


def test_the_settings_buttons_wait_for_the_sheet():
    for rel in ('src/dashboard/body.html', 'src/sports/nhl/pages/body.html', 'src/sports/nba/pages/body.html'):
        page = (ROOT / rel).read_text(encoding='utf-8')
        assert page.count('<button type="button" class="btn btn-block side-settings" data-settings-open hidden>') == 1, rel
        assert page.count('<button type="button" class="bnav-more-item" data-settings-open hidden>') == 1, rel
    home = (ROOT / 'src' / 'site' / 'home' / 'page.html').read_text(encoding='utf-8')
    assert '<button type="button" class="home-settings" data-settings-open hidden>Settings</button>' in home
    assert "openers.forEach(b => { b.hidden = false; b.addEventListener('click', () => open('settings')); });" in SHEET
    assert '.side-settings[hidden], .bnav-more-item[hidden], .home-settings[hidden]{display:none;}' in CSS


def test_the_build_puts_the_sheet_on_a_page_once(tmp_path):
    page = tmp_path / 'index.html'
    page.write_text('<body><button data-settings-open hidden></button></body>', encoding='utf-8')
    block = build.sheet_block()
    assert build.inject_sheet(page, block) and build.inject_sheet(page, block)
    html = page.read_text(encoding='utf-8')
    assert html.count('<script data-site-sheet>') == 1 and '/*' not in html
    other = tmp_path / 'o.html'
    other.write_text('<body>none</body>', encoding='utf-8')
    assert not build.inject_sheet(other, block)
    assert '    add_sheet(out)\n    add_scores(out)\n    add_share(out)\n    add_offline(out)\n    return results' in Path(build.__file__).read_text(encoding='utf-8')
