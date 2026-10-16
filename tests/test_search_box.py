"""The search box on every page (Stage 80 item 56, the 2026-10-13 UI/UX audit's F6).

Measured 2026-10-14 on the site built from main, at 390 and 1440 px in both
themes: no page could be searched (0 search fields or buttons; "/" and Ctrl
K did nothing), so finding the Seattle Kraken from the NFL's page meant the
sport switch, the Teams page and its select. Mark chose the box as mocked
(2026-10-14): "/" or Ctrl K, or a Search button (the sidebar's, the phone's
top bar's, the home's), opens one box that finds teams, the next games,
pages and the NFL's experiments across the three sports, each a link to
where it lives.

The build makes one index after all four pages are built
(src/site/search.py) and puts it, with src/core/palette.js, on every page
whose template has a Search button (src/site/build.py add_search); the
games are the Next games strip's slate.

Run with: pytest tests/test_search_box.py -v
"""
import json
import os
import re
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from src.site import build, search

ROOT = Path(__file__).resolve().parents[1]
PAL = (ROOT / 'src' / 'core' / 'palette.js').read_text(encoding='utf-8')
APP = (ROOT / 'src' / 'dashboard' / 'app.js').read_text(encoding='utf-8')
NODE = shutil.which('node')


def node(code):
    if not NODE:
        pytest.skip('node not available')
    # A game's time is printed on the viewer's own clock (as the Tonight strip's
    # is), so the labels below are pinned to one zone, as test_tonight_strip.py
    # pins its own: on a UTC runner 'Thu 7:00 PM' would read 'Thu 11:00 PM'.
    r = subprocess.run([NODE, '-e', code], capture_output=True, encoding='utf-8',
                       env={**os.environ, 'TZ': 'America/New_York'})
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def pure():
    """palette.js's two functions and their constants, without the part that needs a page."""
    return PAL[:PAL.index('(function(){')]


# ---------- the index ----------

NAV = ('<nav><button class="nav-btn active" data-page="board" aria-current="page"><svg><path d="M3 9"/></svg>Week Board</button>'
       '<button class="nav-btn" data-page="changelog"><svg></svg>What&#39;s Changed</button>'
       '<button class="bnav-btn" data-page="picks"><svg></svg><span class="bnav-label">Picks</span></button></nav>')


def test_a_sports_pages_are_read_from_its_sidebar():
    assert search.pages(NAV) == [['board', 'Week Board'], ['changelog', "What's Changed"]], \
        'the phone bar repeats them and is not read twice'


def test_an_experiments_address_is_the_one_its_row_gets_in_the_page():
    names = ["The market's curve: fitted against hand-picked", 'Early-season extra shrinkage',
             '  Market efficiency trend across seasons (2022–2025)  ', '--Leading punctuation & an ampersand--',
             'A name long enough that the forty-eight character cut lands right on a hyphen-',
             'Ünïcode and 4th-down & 2']
    js = re.search(r'function experimentSlug\(.*?\n\}\n', APP, re.S).group(0)
    want = node(js + f'console.log(JSON.stringify({json.dumps(names)}.map(experimentSlug)));')
    assert [search.experiment_slug(n) for n in names] == want


def test_the_experiments_are_the_model_labs_rows_each_slug_made_unique():
    page = ('<div class="table-wrap" data-scroll-label="Experiment log"><table><tbody>'
            '<tr><td>Drift on log loss</td><td>x</td></tr>'
            '<tr class="lab-row"><td>The market&#39;s <b>curve</b></td><td>y</td></tr>'
            '<tr><td>Drift on log-loss</td><td>z</td></tr></tbody></table></div><table><tr><td>Not a lab row</td></tr></table>')
    assert search.experiments(page) == [['drift-on-log-loss', 'Drift on log loss'],
                                        ['the-market-s-curve', "The market's curve"],
                                        ['drift-on-log-loss-2', 'Drift on log-loss']], 'as app.js routeKnown numbers them'
    assert search.experiments('<p>no lab here</p>') == []


def test_every_club_of_every_sport_is_named():
    names = search.team_names()
    assert (len(names['nfl']), len(names['nhl']), len(names['nba'])) == (32, 32, 30)
    assert names['nhl']['SEA'] == 'Seattle Kraken' and names['nfl']['SEA'] == 'Seattle Seahawks'


def test_the_index_holds_published_sports_only(tmp_path):
    (tmp_path / 'nfl').mkdir()
    (tmp_path / 'nfl' / 'index.html').write_text(NAV, encoding='utf-8')
    found = search.index(tmp_path, {'nfl'})
    assert {t[0] for t in found['teams']} == {'nfl'} and len(found['teams']) == 32
    assert found['pages'] == [['nfl', 'board', 'Week Board'], ['nfl', 'changelog', "What's Changed"]]
    assert found['experiments'] == []


# ---------- what the box finds ----------

INDEX = {'teams': [['nfl', 'SEA', 'Seattle Seahawks'], ['nhl', 'SEA', 'Seattle Kraken'], ['nba', 'BOS', 'Boston Celtics'],
                   ['nhl', 'OTC', 'Old Tampa Club'], ['nhl', 'TBL', 'Tampa Bay Lightning']],
         'pages': [['nfl', 'board', 'Week Board'], ['nfl', 'accuracy', 'Season Accuracy'], ['nfl', 'teamdive', 'Team Deep-Dive'],
                   ['nhl', 'teams', 'Teams'], ['nhl', 'accuracy', 'Season Accuracy'], ['nba', 'board', 'Day Board']],
         'experiments': [['nfl', 'early-season-extra-shrinkage', 'Early-season extra shrinkage']]}
GAMES = [{'s': 'nhl', 't': '2026-10-15T23:00:00Z', 'a': 'SEA', 'h': 'TBL', 'g': '2026020111', 'k': 'wait'},
         {'s': 'nfl', 't': '2026-10-16T00:15:00Z', 'a': 'SEA', 'h': 'DEN', 'g': '2026_week6-SEA-DEN', 'k': 'lean', 'p': 'SEA', 'c': 56},
         {'s': 'nhl', 't': '2026-10-13T23:00:00Z', 'a': 'SEA', 'h': 'OLD', 'g': '1', 'k': 'pick', 'p': 'SEA', 'c': 60}]
NOW = "Date.parse('2026-10-14T22:00:00Z')"


def find(q, base='../', here='NFL'):
    return node(pure() + f"const it = palItems({json.dumps(INDEX)}, {json.dumps(GAMES)}, '{base}', {NOW});\n"
                f"console.log(JSON.stringify(palSearch(it, {json.dumps(q)}, '{here}').map(i => [i.group, i.label, i.href, i.note])));")


def test_sea_finds_both_seattles_their_games_and_season_accuracy():
    got = find('sea')
    assert [g[:2] for g in got] == [['Teams', 'Seattle Seahawks'], ['Teams', 'Seattle Kraken'], ['Games', 'SEA @ TBL'],
                                    ['Games', 'SEA @ DEN'], ['Pages', 'Season Accuracy'], ['Pages', 'Season Accuracy'],
                                    ['Experiments', 'Early-season extra shrinkage']]
    assert 'SEA @ OLD' not in json.dumps(got), 'a game long over is not offered'


def test_each_thing_found_leads_where_it_lives_from_this_page():
    got = {(g[0], g[1], g[3]): g[2] for g in find('sea')}
    assert got[('Teams', 'Seattle Seahawks', 'NFL · Team Deep-Dive')] == '../nfl/#team/SEA'
    assert got[('Teams', 'Seattle Kraken', 'NHL · Teams')] == '../nhl/#team/SEA'
    assert got[('Games', 'SEA @ TBL', 'NHL · Thu 7:00 PM')] == '../nhl/#game/2026020111'
    assert got[('Games', 'SEA @ DEN', 'NFL · Thu 8:15 PM · Leans SEA 56%')] == '../nfl/#game/2026_week6-SEA-DEN'
    assert got[('Experiments', 'Early-season extra shrinkage', 'NFL · Model Lab')] == '../nfl/#modellab/early-season-extra-shrinkage'
    assert [g[2] for g in find('celtics')] == ['../nba/'], 'the NBA has no Teams page: its board'
    assert [g[2] for g in find('board', base='')] == ['nfl/', 'nba/'], 'from the home, no step up; a board is its bare address'


def test_every_word_typed_must_start_a_word_and_a_name_that_starts_with_it_leads():
    assert [g[1] for g in find('season acc')] == ['Season Accuracy', 'Season Accuracy']
    assert find('eason') == [], 'the middle of a word finds nothing'
    assert [g[1] for g in find('lightning')] == ['Tampa Bay Lightning']
    assert [g[1] for g in find('tampa')] == ['Tampa Bay Lightning', 'Old Tampa Club'], \
        'a name that starts with the query comes before one that only has the word'


def test_with_nothing_typed_it_offers_this_sports_pages():
    assert [g[1] for g in find('')] == ['Week Board', 'Season Accuracy', 'Team Deep-Dive']
    assert find('', base='', here='Home') == []
    assert 'Type a team, a game or a page.' in PAL


# ---------- the box ----------

def test_slash_and_ctrl_k_open_it_and_it_is_a_dialog_with_a_combobox():
    assert """if((e.key === 'k' || e.key === 'K') && (e.ctrlKey || e.metaKey) && !e.altKey){""" in PAL
    assert """} else if(e.key === '/' && !typing && !e.ctrlKey && !e.metaKey && !e.altKey && shell.hidden){""" in PAL
    assert '<div class="pal-dialog" role="dialog" aria-modal="true" aria-label="Search">' in PAL
    assert 'role="combobox" aria-expanded="true" aria-controls="pal-list" aria-autocomplete="list"' in PAL
    assert "input.setAttribute('aria-activedescendant', 'pal-opt-' + active);" in PAL
    assert "if(back && back.focus) back.focus();" in PAL, 'Esc gives the focus back'


def test_arrows_move_enter_follows_and_tab_stays():
    keys = PAL[PAL.index("input.addEventListener('keydown'"):]
    assert "active = (active + (e.key === 'ArrowDown' ? 1 : -1) + shown.length) % shown.length;" in keys
    assert "follow(shown[active]);" in keys and "e.key === 'Tab'" in keys


def test_the_search_buttons_wait_for_the_box():
    for rel in ('src/dashboard/body.html', 'src/sports/nhl/pages/body.html', 'src/sports/nba/pages/body.html'):
        page = (ROOT / rel).read_text(encoding='utf-8')
        assert page.count('class="side-search" data-palette-open aria-keyshortcuts="/ Control+K" hidden>') == 1, rel
        assert page.count('class="topbar-search" data-palette-open aria-label="Search" aria-keyshortcuts="/ Control+K" hidden>') == 1, rel
    home = (ROOT / 'src' / 'site' / 'home' / 'page.html').read_text(encoding='utf-8')
    assert 'class="home-theme home-search" data-palette-open aria-label="Search" aria-keyshortcuts="/ Control+K" hidden>' in home
    assert "openers.forEach(b => { b.hidden = false; b.addEventListener('click', open); });" in PAL
    css = (ROOT / 'src' / 'dashboard' / 'styles.css').read_text(encoding='utf-8')
    assert '.side-search[hidden], .topbar-search[hidden], .home-search[hidden]{display:none;}' in css


def test_its_names_cannot_meet_a_pages_own():
    top = set(re.findall(r'^(?:function|const|let) (\w+)', PAL, re.M))
    assert top == {'PAL_GROUPS', 'PAL_SPORT', 'palItems', 'palSearch'}
    for rel in ('src/dashboard/app.js', 'src/sports/nhl/pages/nhl.js', 'src/sports/nba/pages/nba.js', 'src/site/home/home.js'):
        text = (ROOT / rel).read_text(encoding='utf-8')
        assert not re.search(r'\b(?:function|const|let|var) (?:PAL_GROUPS|PAL_SPORT|palItems|palSearch)\b', text), rel


# ---------- the build puts it on every page ----------

def test_the_build_puts_the_index_and_the_box_on_a_page_once_after_the_slate(tmp_path):
    page = tmp_path / 'index.html'
    page.write_text('<body><button data-palette-open hidden></button><div id="site-strip"></div></body>', encoding='utf-8')
    build.inject_strip(page, build.strip_block([]))
    block = build.search_block({'teams': [['nfl', 'X', '</script>']], 'pages': [], 'experiments': []})
    assert build.inject_search(page, block) and build.inject_search(page, block)
    html = page.read_text(encoding='utf-8')
    assert html.count('id="site-search-data"') == 1 and html.count('<script data-site-search>') == 1
    assert html.index('id="site-strip-data"') < html.index('id="site-search-data"') < html.index('</body>')
    assert '</script>"' not in html and '/*' not in html.split('<script data-site-search>')[1]
    other = tmp_path / 'o.html'
    other.write_text('<body>no button</body>', encoding='utf-8')
    assert not build.inject_search(other, block)


def test_the_site_build_adds_it_and_survives_its_failure(tmp_path):
    (tmp_path / 'index.html').write_text('<body><button data-palette-open></button></body>', encoding='utf-8')
    seen = []

    def finder(out, published):
        seen.append(published)
        return {'teams': [], 'pages': [], 'experiments': []}
    results = [build.SportResult('nfl', built=True), build.SportResult('nhl'), build.SportResult('home', built=True)]
    assert build.add_search(tmp_path, results, finder) == ['index.html'] and seen == [{'nfl'}]

    def boom(out, published):
        raise ValueError('bad page')
    (tmp_path / 'index.html').write_text('<body><button data-palette-open></button></body>', encoding='utf-8')
    assert build.add_search(tmp_path, results, boom) == []
    src = Path(build.__file__).read_text(encoding='utf-8')
    assert '    add_strip(out, results)\n    add_search(out, results)\n' in src, 'after the strip, whose slate it reads'


def test_the_slates_games_carry_their_address():
    from src.site import home
    rows = home.slate(ROOT, datetime(2026, 10, 14, 22, 0, tzinfo=UTC))
    assert all(r.get('g') for r in rows)
