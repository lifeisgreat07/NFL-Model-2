"""
Stage 10's table system (2026-09-23).

Every table sits in a `.table-wrap`. The wrapper scrolls sideways by default
and draws a soft edge on the side that has more columns; fitTables() marks it
`.fits` when the table is no wider than its box, and only then does the header
row stick to the top of the window. See the Tables block in the stylesheet for
why the two cannot both hold at once.

What this file holds is the set of premises the rendered behaviour rests on,
because no CI job here has a browser:

  * every table goes through the wrapper, and no wrapper overrides its
    overflow inline (an inline overflow beats `.fits` and kills the sticky
    header -- Model Lab's experiments table carried one);
  * `.fits` uses overflow:clip, the one value that rounds the corners
    WITHOUT making the wrapper a scroll container;
  * tables use border-collapse:separate, since a collapsed border stays
    behind when a sticky cell moves;
  * the stuck header sits above everything drawn inside a row;
  * a header looks and behaves like a control exactly when it sorts.

Run with: pytest tests/test_table_system.py -v
"""
import re
from pathlib import Path

import pytest

TEMPLATE = Path(__file__).parent.parent / 'src' / 'dashboard_template.html'


def strip_css_comments(src):
    return re.sub(r'/\*.*?\*/', '', src, flags=re.S)


def rule(css, selector):
    """The declarations of every rule whose selector list is exactly
    `selector`, media queries included, joined -- so a later override in a
    breakpoint counts against the rule as much as the base does."""
    hits = re.findall(r'(?:^|[}{\n])\s*' + re.escape(selector) + r'\s*\{([^}]*)\}', css)
    assert hits, f'{selector!r}: no rule found -- re-anchor this guard'
    return re.sub(r'\s+', '', ';'.join(hits))


def z_index(decls):
    m = re.search(r'z-index:(\d+)', decls)
    assert m, f'no z-index in {decls!r}'
    return int(m.group(1))


def unwrapped_tables(src):
    """Every <table> not opened directly inside a .table-wrap div."""
    out = []
    for m in re.finditer(r'<table\b', src):
        before = src[:m.start()].rstrip()
        if not re.search(r'<div class="table-wrap"[^>]*>$', before):
            out.append(src.count('\n', 0, m.start()) + 1)
    return out


def header_problems(src):
    """Sortable-looking and sortable-behaving headers must be the same set."""
    problems = []
    for th in re.findall(r'<th\b[^>]*>', src):
        key = re.search(r'data-key="([^"]+)"', th)
        sorts = key and key.group(1) != 'rank'   # the handler returns early on rank
        if sorts and 'aria-sort=' not in th:
            problems.append(f'sorts but has no aria-sort: {th}')
        if sorts and 'tabindex="0"' not in th:
            problems.append(f'sorts but a keyboard cannot reach it: {th}')
        if not sorts and ('aria-sort=' in th or 'tabindex=' in th):
            problems.append(f'announced as sortable but does not sort: {th}')
    return problems


@pytest.fixture(scope='module')
def src():
    return TEMPLATE.read_text(encoding='utf-8')


@pytest.fixture(scope='module')
def css(src):
    return strip_css_comments(src[:src.index('</style>')])


def test_every_table_sits_in_the_wrapper(src):
    assert not unwrapped_tables(src), f'tables outside a .table-wrap at lines {unwrapped_tables(src)}'


def test_the_scan_found_the_tables(src):
    """Vacuity guard for the rule above: the ratings table, Model Lab's
    experiments, and the metrics tables rendered in markup and by script."""
    assert len(re.findall(r'<table\b', src)) >= 12


def test_no_wrapper_overrides_its_overflow_inline(src):
    inline = re.findall(r'<div class="table-wrap"[^>]*style="[^"]*overflow[^"]*"', src)
    assert not inline, f'an inline overflow beats .fits and unsticks the header: {inline}'


def test_a_fitting_table_clips_rather_than_scrolls(css):
    """overflow:hidden or auto would make the wrapper a scroll container, and
    a sticky header then sticks to the wrapper, which never scrolls."""
    assert 'overflow:clip' in rule(css, '.table-wrap.fits')


def test_the_default_is_the_scrolling_one(css):
    """Before fitTables() runs, or without JavaScript, a wide table must
    scroll rather than lose columns."""
    decls = rule(css, '.table-wrap')
    assert 'overflow-x:auto' in decls
    assert 'local' in decls and 'scroll' in decls, 'the scroll-edge background is gone'


def test_the_header_sticks_only_where_the_table_fits(css):
    sticky = re.findall(r'([^{}]+)\{[^}]*position:\s*sticky[^}]*\}', css)
    th_sticky = [s.strip() for s in sticky if 'th' in s]
    assert th_sticky == ['.table-wrap.fits thead th'], th_sticky


def test_tables_do_not_collapse_borders(css):
    """Stated over the whole stylesheet, not the one `table` rule: the first
    draft checked only that rule, and .metrics-table -- eleven of the
    thirteen tables -- still said collapse."""
    assert 'border-collapse:separate' in rule(css, 'table')
    collapsing = re.findall(r'([^{}]+)\{[^}]*border-collapse:\s*collapse', css)
    assert not collapsing, f'these rules still collapse borders: {[c.strip() for c in collapsing]}'


def test_the_stuck_header_sits_above_the_net_rating_zero_line(css):
    header = z_index(rule(css, '.table-wrap.fits thead th'))
    zero = z_index(rule(css, '.srs-bar-track.diverging::before'))
    assert header > zero, (
        f'the stuck header (z-index {header}) is under the Net Rating zero line '
        f'(z-index {zero}), which pokes up through it as rows scroll past')


def test_only_sortable_headers_look_clickable(css):
    base = rule(css, 'thead th')
    assert 'cursor:pointer' not in base, 'every header on every table looks clickable again'
    assert 'cursor:pointer' in rule(css, 'thead th[aria-sort]')
    hover = re.findall(r'(thead th[^{]*):hover', css)
    assert hover and all('[aria-sort]' in h for h in hover), hover


def test_sortable_headers_are_announced_and_reachable(src):
    assert not header_problems(src), '\n'.join(header_problems(src))


def test_the_header_rule_over_synthetic_markup():
    assert header_problems('<th data-key="net" tabindex="0" aria-sort="none">') == []
    assert header_problems('<th data-key="rank">#</th>') == []
    assert header_problems('<th data-key="net">')            # neither
    assert header_problems('<th data-key="net" aria-sort="none">')   # no tabindex
    assert header_problems('<th tabindex="0" aria-sort="none">')     # does not sort


def test_the_sort_handler_takes_a_keyboard_and_reports_its_state(src):
    m = re.search(r"document\.querySelectorAll\('#ratings-table th\[data-key\]'\)\.forEach\(th=>\{.*?\n\}\);",
                  src, re.S)
    assert m, 'the ratings sort handler is not findable -- re-anchor this guard'
    block = m.group(0)
    assert "addEventListener('keydown'" in block and "'Enter'" in block and "' '" in block
    assert "setAttribute('aria-sort'" in block


def prose_in_figure_cells(src):
    """Static `td.num` cells holding a sentence rather than a figure.

    `td.num` right-aligns, which is right for a column of figures and wrong
    for prose: before Stage 10, 76 cells of it were set flush right -- the 46
    in Model Lab's result column, and 30 across Methodology's tables, the
    glossary's definitions among them.
    Four words is the line: every static figure cell left is one or two
    tokens ("-2.39pt", "[-5.15, +0.37]", "Rejected")."""
    out = []
    for m in re.finditer(r'<td class="num"[^>]*>(.*?)</td>', src, re.S):
        if '${' in m.group(1):
            continue            # filled by script with a computed figure
        words = re.sub(r'<[^>]+>', '', m.group(1)).split()
        if len(words) >= 4:
            out.append(' '.join(words)[:50])
    return out


def test_figure_cells_hold_figures(src):
    prose = prose_in_figure_cells(src)
    assert not prose, f'right-aligned prose in td.num: {prose}'


def test_the_figure_cell_rule_over_synthetic_markup():
    assert prose_in_figure_cells('<td class="num">+0.149</td>') == []
    assert prose_in_figure_cells('<td class="num">[-5.15, +0.37]</td>') == []
    assert prose_in_figure_cells('<td class="num">${fmt(x)} and some words here</td>') == []
    assert prose_in_figure_cells('<td class="num">Model A features plus the spread</td>')
