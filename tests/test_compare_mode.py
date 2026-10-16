"""Compare mode: the NFL's week as one table (Stage 80 item 55, the 2026-10-13 UI/UX audit's F9).

Measured 2026-10-14 on the NFL page built from main, Week 5, at 1440 px:
the week could be read only as 15 cards, each model's chance on its own
card, so comparing Model A, Model B and the market across games meant
scrolling past every card. A "Cards | Table" switch beside the sort now
shows the week as one table, a game a row: kickoff, game, Model A, Model
B, the market (each a side and its chance, "even" inside the even band, as
the cards say it) and the result. It follows the board's filter and sort
until a column is chosen; then that column sorts it, strongest first, and
again turns it round. Mark chose the table at 641 px and wider only
(2026-10-14): a phone keeps its rows and is not shown the switch. The
choice is kept in this browser (nfl:boardView).

Run with: pytest tests/test_compare_mode.py -v
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
BODY = (ROOT / 'src' / 'dashboard' / 'body.html').read_text(encoding='utf-8')
NODE = shutil.which('node')


def fn(name):
    m = re.search(r'function %s\(.*?\n\}\n' % name, APP, re.S)
    assert m, f'{name} is not findable -- re-anchor this guard'
    return m.group(0)


def const(name):
    m = re.search(r'^const %s = .*?;\n' % name, APP, re.S | re.M)
    assert m, f'{name} is not findable -- re-anchor this guard'
    return m.group(0)


def run(expr):
    if not NODE:
        pytest.skip('node not available')
    js = (const('CARD_EVEN_BAND') + const('COMPARE_COLS') + const('COMPARE_PROB')
          + "function escapeHtml(s){ return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;'); }\n"
          + ''.join(fn(n) for n in ('cardSide', 'cardSideText', 'gradedTagHtml', 'compareKick', 'compareValue',
                                    'compareRows', 'compareSortState', 'compareTableHtml')))
    r = subprocess.run([NODE, '-e', js + f'\nprocess.stdout.write(JSON.stringify({expr}));'],
                       capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def game(away, home, a, b, mkt, day='2026-10-11', t='13:00', wd='Sunday', **kw):
    return {'away': away, 'home': home, 'fbA_home': a, 'mktB_home': b, 'mkt_home': mkt, 'gameday': day,
            'gametime_et': t, 'weekday': wd, 'graded': False, **kw}


WEEK = [game('TB', 'DAL', 72, 80, 85, '2026-10-08', '20:15', 'Thursday', graded=True, model_b_correct=0),
        game('PHI', 'JAX', 57, 74, 80, '2026-10-11', '09:30', graded=True, model_b_correct=1),
        game('SF', 'SEA', 51, 50.4, 63, graded=True, result='tie', model_b_correct=None),
        game('CHI', 'GB', 60, 43, None)]


def rows(html):
    return [re.findall(r'<td[^>]*>(.*?)</td>', r) for r in re.findall(r'<tr><td>.*?</tr>', html)]


def test_a_row_is_a_game_with_each_models_side_the_markets_and_the_result():
    html = run(f"compareTableHtml({json.dumps(WEEK)}, {{key: null, dir: -1}}, 'chronological', '2026 · Week 5')")
    got = rows(html)
    assert got[0] == ['Thu 8:15 PM', '<b>TB @ DAL</b>', 'DAL 72%', 'DAL 80%', 'DAL 85%', '<span class="graded-tag incorrect">Missed</span>']
    assert got[1][5] == '<span class="graded-tag correct">Correct</span>' and got[1][0] == 'Sun 9:30 AM'
    assert got[2][3] == 'even (50%)' and got[2][5] == '<span class="graded-tag tie">Tie</span>', 'the even band, as the cards'
    assert got[3][3] == 'CHI 57%' and got[3][4] == '—' and got[3][5] == '—', 'no price, no result yet'
    assert '<caption class="visually-hidden">2026 · Week 5: every game, ' in html
    assert len(re.findall(r'<td class="num">', html)) == 12, 'the three chances line up on the right'


def test_every_header_is_a_button_that_says_how_the_table_is_sorted():
    html = run(f"compareTableHtml({json.dumps(WEEK)}, {{key: null, dir: -1}}, 'chronological', 'W')")
    heads = re.findall(r'<th scope="col"(?: class="num")? aria-sort="(\w+)"><button type="button" class="cmp-sort" data-cmp="(\w+)">([^<]+)</button></th>', html)
    assert [h[1:] for h in heads] == [('kickoff', 'Kickoff'), ('game', 'Game'), ('a', 'Model A'), ('b', 'Model B'),
                                      ('market', 'Market'), ('result', 'Result')]
    assert [h[0] for h in heads] == ['ascending', 'none', 'none', 'none', 'none', 'none'], "the board's kickoff order"
    other = run(f"compareTableHtml({json.dumps(WEEK)}, {{key: null, dir: -1}}, 'confidence', 'W')")
    assert 'aria-sort="ascending"' not in other, "under another board sort no column claims the order"


def test_until_a_column_is_chosen_the_table_keeps_the_boards_order():
    order = run(f"compareRows({json.dumps(WEEK[::-1])}, {{key: null, dir: -1}}).map(g => g.home)")
    assert order == ['GB', 'SEA', 'JAX', 'DAL']


def test_a_column_sorts_strongest_first_and_again_turns_it_round():
    first = run(f"compareRows({json.dumps(WEEK)}, {{key: 'b', dir: -1}}).map(g => g.home)")
    assert first == ['DAL', 'JAX', 'GB', 'SEA'], "Model B's chance for its own side, strongest first"
    assert run(f"compareRows({json.dumps(WEEK)}, {{key: 'b', dir: 1}}).map(g => g.home)") == first[::-1]
    assert run(f"compareRows({json.dumps(WEEK)}, {{key: 'market', dir: -1}}).map(g => g.home)")[-1] == 'GB', 'no price sinks'
    assert run(f"compareRows({json.dumps(WEEK)}, {{key: 'kickoff', dir: -1}}).map(g => g.home)") == ['DAL', 'JAX', 'SEA', 'GB']
    assert run(f"compareRows({json.dumps(WEEK)}, {{key: 'result', dir: -1}}).map(g => g.home)") == ['JAX', 'DAL', 'SEA', 'GB']
    assert run("[compareSortState('b', {key: 'b', dir: -1}, 'x'), compareSortState('b', {key: 'b', dir: 1}, 'x'), "
               "compareSortState('game', {key: 'game', dir: -1}, 'x')]") == ['descending', 'ascending', 'ascending']


def test_the_switch_sits_beside_the_sort_and_only_where_the_table_fits():
    assert ('<div class="view-seg" id="view-seg" role="group" aria-label="Show the week as">\n'
            '        <button type="button" data-view="cards" aria-pressed="true">Cards</button>\n'
            '        <button type="button" data-view="table" aria-pressed="false">Table</button>') in BODY
    assert BODY.index('id="sort-select"') < BODY.index('id="view-seg"') < BODY.index('id="picks-pdf-link"')
    assert "const TABLE_MIN = '(min-width: 641px)';" in APP
    assert "function tableView(){ return boardView === 'table' && window.matchMedia(TABLE_MIN).matches; }" in APP
    assert '.view-seg{display:none; ' in CSS and '@media (min-width:641px){ .view-seg{display:inline-flex;} }' in CSS


def test_the_board_draws_the_table_from_its_filtered_sorted_games():
    body = fn('renderGames')
    at = body.index('if(tableView()){')
    assert body.index('const sorted = ') < at, 'the table follows the filter and the sort'
    assert "grid.innerHTML = compareTableHtml(sorted, compareSort, currentSort, weekLabel(currentBoardWeek));" in body[at:]
    assert "grid.classList.remove('is-table');" in body[:200]
    assert '#game-grid.is-table{display:block;}' in CSS


def test_the_choice_is_kept_and_a_header_keeps_the_focus():
    assert "const VIEW_KEY = 'nfl:boardView';" in APP
    assert "try{ if(localStorage.getItem(VIEW_KEY) === 'table') boardView = 'table'; }catch(e){}" in APP
    inst = fn('installCompare')
    assert 'try{ localStorage.setItem(VIEW_KEY, boardView); }catch(e2){}' in inst
    assert "compareSort = compareSort.key === key ? {key, dir: -compareSort.dir} : {key, dir: -1};" in inst
    assert 'if(again) again.focus();' in inst
    assert "mq.addEventListener('change'" in inst, 'across 641 px the board changes view'
    assert re.search(r'^installCompare\(\);$', APP, re.M)
