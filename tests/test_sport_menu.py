"""The sport menu's records and script (audit 9 D3; Mark's M1 B, 2026-11-16).

Every page's switcher is a menu (tests/test_sport_switch.py holds its markup). Open, each sport's row carries
the season's record, which the site build writes in as it puts the strip on (src/site/build.py add_menu):
each published sport's graded picks as its home card counts them (Model B's for the NFL), "won-lost", none
for a sport with nothing graded yet or no page in the build. A page kept from the live site has its old
records and script replaced. The build also adds src/core/sport_menu.js, which closes an open menu on Esc or a
click elsewhere; and the search box, which reads the current page's name from the menu, reads the name only.

Run with: pytest tests/test_sport_menu.py -v
"""
import inspect
import json
import re
import subprocess
from pathlib import Path

from src.site import build, home
from src.site.build import SportResult
from tests.optional import require_tool

ROOT = Path(__file__).resolve().parents[1]
MENU_JS = (ROOT / 'src' / 'core' / 'sport_menu.js').read_text(encoding='utf-8')
PALETTE_JS = (ROOT / 'src' / 'core' / 'palette.js').read_text(encoding='utf-8')
CSS = (ROOT / 'src' / 'dashboard' / 'styles.css').read_text(encoding='utf-8')
SLOTS = ''.join(f'<a href="../{s}/">{s.upper()}<span class="sm-rec" data-rec="{s}"></span></a>' for s in build.SPORTS)
PAGE = f'<html><body><nav class="sport-switch"><details class="sm">{SLOTS}</details></nav></body></html>'


def facts(won, lost, built=True):
    return lambda: {'built': built, 'record': {'label': 'x', 'won': won, 'lost': lost}}


READERS = {'nfl': facts(91, 44), 'nhl': facts(176, 102), 'nba': facts(0, 0)}


def site(tmp_path, page=PAGE):
    (tmp_path / 'index.html').write_text(page.replace('../', ''), encoding='utf-8')
    for s in build.SPORTS:
        (tmp_path / s).mkdir(exist_ok=True)
        (tmp_path / s / 'index.html').write_text(page, encoding='utf-8')
    return tmp_path


def records(html):
    return dict(re.findall(r'data-rec="([a-z]+)">([^<]*)<', html))


def test_the_build_writes_each_published_sports_record_on_every_page_and_adds_the_script(tmp_path):
    out = site(tmp_path)
    results = [SportResult('nfl', built=True), SportResult('nhl', kept_live=True), SportResult('nba', built=True)]
    assert build.add_menu(out, results, READERS) == ['index.html', 'nfl/index.html', 'nhl/index.html', 'nba/index.html']
    for page in ('index.html', 'nfl/index.html', 'nhl/index.html', 'nba/index.html'):
        html = (out / page).read_text(encoding='utf-8')
        assert records(html) == {'nfl': '91-44', 'nhl': '176-102', 'nba': ''}, f'{page}: nothing graded shows nothing'
        assert html.count('<script data-site-menu>') == 1 and html.index('<script data-site-menu>') < html.index('</body>')


def test_a_sport_with_no_page_in_the_build_has_no_record(tmp_path):
    results = [SportResult('nfl', built=True), SportResult('nhl', error='failed'), SportResult('nba', built=True)]
    assert build.menu_records(results, READERS) == {'nfl': '91-44'}
    unbuilt = dict(READERS, nfl=facts(3, 1, built=False))
    assert build.menu_records(results, unbuilt) == {}


def test_a_page_kept_from_the_live_site_has_its_records_and_script_replaced(tmp_path):
    out = site(tmp_path)
    results = [SportResult(s, built=True) for s in build.SPORTS]
    build.add_menu(out, results, READERS)
    build.add_menu(out, results, dict(READERS, nfl=facts(92, 44)))
    html = (out / 'nhl' / 'index.html').read_text(encoding='utf-8')
    assert records(html)['nfl'] == '92-44'
    assert html.count('<script data-site-menu>') == 1


def test_a_failure_reading_the_records_still_publishes_the_menus(tmp_path, capsys):
    def broken():
        raise OSError('no results folder')
    out = site(tmp_path)
    results = [SportResult(s, built=True) for s in build.SPORTS]
    assert len(build.add_menu(out, results, dict(READERS, nhl=broken))) == 4
    assert 'the sport menu records were left off: no results folder' in capsys.readouterr().out
    assert records((out / 'nfl' / 'index.html').read_text(encoding='utf-8')) == {'nfl': '', 'nhl': '', 'nba': ''}


def test_a_page_without_the_record_slots_is_left_alone(tmp_path):
    other = tmp_path / 'x.html'
    other.write_text('<html><body>x</body></html>', encoding='utf-8')
    assert not build.inject_menu(other, {'nfl': '1-0'}, build.menu_block())
    assert other.read_text(encoding='utf-8') == '<html><body>x</body></html>'


def test_the_records_are_the_home_cards_records(monkeypatch):
    for sport, (won, lost) in {'nfl': (5, 4), 'nhl': (7, 2), 'nba': (1, 1)}.items():
        monkeypatch.setattr(home, f'{sport}_facts', facts(won, lost))
    results = [SportResult(s, built=True) for s in build.SPORTS]
    assert build.menu_records(results) == {'nfl': '5-4', 'nhl': '7-2', 'nba': '1-1'}


def test_the_site_build_writes_the_records_after_the_strip_and_before_the_hashes():
    body = inspect.getsource(build.build_site)
    # After the search box's step too, which reads the strip's slate and is held to follow it straight away.
    assert '    add_strip(out, results)\n    add_search(out, results)\n    add_menu(out, results)\n' in body
    assert body.index('    add_menu(out, results)\n') < body.index('    add_csp(out)\n')


def run_close(menus, inside):
    node = require_tool('node')
    fn = re.search(r'function smClose\(menus, inside\)\{.*?\n\}', MENU_JS, re.S).group(0)
    src = fn + f"""
const menus = {json.dumps(menus)}.map((m, i) => ({{open: m.open, id: i, contains: t => t === i}}));
const n = smClose(menus, {json.dumps(inside)});
process.stdout.write(JSON.stringify({{n, open: menus.map(m => m.open)}}));"""
    out = subprocess.run([node, '-e', src], capture_output=True, text=True, encoding='utf-8', check=True).stdout
    return json.loads(out)


def test_a_click_outside_closes_an_open_menu_and_a_click_inside_does_not():
    assert run_close([{'open': True}, {'open': False}], 5) == {'n': 1, 'open': [False, False]}
    assert run_close([{'open': True}, {'open': True}], 1) == {'n': 1, 'open': [False, True]}, 'the clicked menu stays open'
    assert run_close([{'open': True}], None) == {'n': 1, 'open': [False]}, 'Esc closes it'


def test_the_script_closes_on_esc_and_on_a_click_and_hands_the_focus_back():
    assert "document.addEventListener('keydown', e => {\n    if(e.key !== 'Escape') return;" in MENU_JS
    assert "button.focus();" in MENU_JS
    assert "document.addEventListener('click', e => { smClose(menus(), e.target); });" in MENU_JS


def test_the_search_box_reads_the_current_pages_name_and_not_its_record():
    node = require_tool('node')
    line = re.search(r"  const here = cur \? .*?;\n", PALETTE_JS).group(0)
    src = ("const cur = {childNodes: [{nodeType: 1, textContent: ''}, {nodeType: 3, textContent: 'NHL'}, "
           "{nodeType: 1, textContent: '176-102'}]};\n" + line + 'process.stdout.write(here);')
    assert subprocess.run([node, '-e', src], capture_output=True, text=True, encoding='utf-8', check=True).stdout == 'NHL'
    assert "const cur = document.querySelector('.sport-switch [aria-current=\"page\"]');" in PALETTE_JS


def test_the_note_and_an_empty_record_hide_until_there_is_a_record():
    assert '  .sm-rec:empty{display:none;}\n' in CSS
    assert '  .sm-list:not(:has(.sm-rec:not(:empty))) .sm-note{display:none;}\n' in CSS
