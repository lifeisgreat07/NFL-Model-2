"""Team Deep-Dive's games list has column headings (Stage 19).

The list is a column of buttons -- each opens that game's breakdown -- drawn
on a five-column grid: week, opponent, line, Model B's win probability for
the selected team, result. Nothing said which number was which. A heading row
now sits on the same grid, and on a phone it follows the rows' own layout:
the week on its own line and the line column hidden.

The heading row is aria-hidden, because it is not a real table header and a
screen reader could not tie it to the buttons. Each button says the same
words itself instead, through .visually-hidden labels.

On a phone the rows also changed: they were a two-column grid, which put the
result on a third line under the opponent. They are now opponent, Model B and
result on one row, on the same columns as the heading.

Run with: pytest tests/test_team_dive_games_head.py -v
"""
import re

from src.pipeline.template_parts import JOINED_TEMPLATE

TEMPLATE = JOINED_TEMPLATE
LABELS = ['Week', 'Opponent', 'Line', 'Model B', 'Result']


def source():
    return TEMPLATE.read_text(encoding='utf-8').replace('\r\n', '\n')


def render_games():
    src = source()
    start = src.index('function renderTeamGames(')
    return src[start:src.index('\n}\n', start)]


def css():
    style = re.search(r'<style>(.*?)</style>', source(), re.S).group(1)
    return re.sub(r'/\*.*?\*/', '', style, flags=re.S)


def phone_block():
    m = re.search(r'@media \(max-width:640px\)\{((?:(?!\n  \}).)*?\.dive-game-head.*?)\n  \}', css(), re.S)
    assert m, "the phone block for the games list is gone -- re-anchor this guard"
    return m.group(1)


def columns(text, selector):
    m = re.search(re.escape(selector) + r'\{[^}]*grid-template-columns:([^;]+);', text)
    return m.group(1).strip() if m else None


def test_the_heading_row_names_the_five_columns_in_order():
    js = render_games()
    m = re.search(r'<div class="dive-games-head" aria-hidden="true">(.*?)</div>', js, re.S)
    assert m, 'the games list has no heading row, or it is exposed to assistive technology'
    names = [re.sub(r'<[^>]+>', '', s).strip() for s in re.findall(r'<span class="dgh-\w+"[^>]*>(.*?)</span>', m.group(1))]
    assert names == LABELS


def test_the_heading_row_comes_before_the_rows_inside_the_list():
    js = render_games()
    wrap = js[js.index('<div class="table-wrap">'):]
    assert wrap.index('dive-games-head') < wrap.index('${rows}')


def test_heading_and_rows_share_their_columns_on_a_wide_screen():
    sheet = css()
    wide = sheet[:sheet.index(phone_block())]
    assert columns(wide, '.dive-games-head') == columns(wide, '.dive-game-head') is not None


def test_heading_and_rows_share_their_columns_on_a_phone():
    block = phone_block()
    rows = columns(block, '.dive-game-head')
    assert rows and rows == columns(block, '.dive-games-head')
    assert len(rows.split()) == 3, f'the phone rows are {rows!r}; the result goes back to its own line'
    assert re.search(r'\.dive-games-head \.dgh-week, \.dive-games-head \.dgh-line\{display:none;\}', block), (
        "the phone heading still names the week and line columns the rows no longer show")


def test_each_row_names_its_numbers_to_a_screen_reader():
    js = render_games()
    for cell, label in (('dive-game-line', 'Line '), ('dive-game-prob', 'Model B '), ('dive-game-res', 'Result ')):
        assert re.search(r'<span class="%s"[^>]*><span class="visually-hidden">%s</span>' % (cell, label), js), (
            f'{cell} says its number with no name for it')
