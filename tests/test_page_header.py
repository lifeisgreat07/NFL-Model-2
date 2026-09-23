"""
Stage 10's shared page header and the sidebar groups it names (2026-09-23).

THE DEFECT. The sidebar had two groups both headed "Model Output", so the
nav's own headings meant nothing, and the nine page headers were written
nine ways: two with no description, Methodology on one line, and the Week
Board's welcome box sitting ABOVE the page title. Model Lab's header also
typed the model version by hand and said 2.4 through the 2.5 release.

THE CONTRACT, now that it is one component in a static file: every page
opens with `.page-head`, which carries an eyebrow, an h2 and a `.desc`.
The eyebrow is the sidebar group the page's nav button sits in, and the h2
is that button's label. So the nav and the header cannot disagree about
what a page is called or where it lives -- on a phone, where the sidebar is
hidden, the eyebrow is the only place that still says so.

Run with: pytest tests/test_page_header.py -v
"""
import re
from pathlib import Path

import pytest

TEMPLATE = Path(__file__).parent.parent / 'src' / 'dashboard_template.html'


def strip_comments(src):
    return re.sub(r'<!--.*?-->', '', src, flags=re.S)


def text(html):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', html)).strip()


def sidebar_groups(src):
    """[(group label, [(data-page, button label), ...]), ...] in order."""
    nav = re.search(r'<nav class="side-nav"[^>]*>(.*?)</nav>', strip_comments(src), re.S)
    assert nav, 'the sidebar <nav class="side-nav"> is gone -- re-anchor this guard'
    groups = []
    for m in re.finditer(r'<div class="nav-group-label">(.*?)</div>|'
                         r'<button class="nav-btn[^"]*" data-page="([^"]+)">(.*?)</button>',
                         nav.group(1), re.S):
        if m.group(1) is not None:
            groups.append((text(m.group(1)), []))
        else:
            assert groups, 'a nav button sits above the first group label'
            groups[-1][1].append((m.group(2), text(m.group(3))))
    return groups


def page_heads(src):
    """{page id: (html between <section ...> and the first .page-head, head html)}."""
    out = {}
    for m in re.finditer(r'<section class="page[^"]*" id="page-([^"]+)">(.*?)</section>',
                         strip_comments(src), re.S):
        body = m.group(2)
        h = re.search(r'<div class="page-head">(.*?)\n    </div>\n', body, re.S)
        out[m.group(1)] = (body[:h.start()] if h else body, h.group(1) if h else None)
    return out


def header_problems(groups, heads):
    """Every way the headers and the sidebar disagree. Empty means they agree."""
    problems = []
    labels = [g for g, _ in groups]
    for dup in sorted({g for g in labels if labels.count(g) > 1}):
        problems.append(f'two sidebar groups are both called {dup!r}')
    where = {page: (g, label) for g, btns in groups for page, label in btns}
    for page, (before, head) in sorted(heads.items()):
        if head is None:
            problems.append(f'{page}: no .page-head')
            continue
        if text(before):
            problems.append(f'{page}: content before the page header: {text(before)[:60]!r}')
        eyebrow = re.search(r'<div class="page-eyebrow">(.*?)</div>', head, re.S)
        h2 = re.search(r'<h2>(.*?)</h2>', head, re.S)
        desc = re.search(r'<div class="desc">(.*?)</div>', head, re.S)
        if page not in where:
            problems.append(f'{page}: no sidebar button reaches this page')
            continue
        group, label = where[page]
        if not eyebrow or text(eyebrow.group(1)) != group:
            problems.append(f'{page}: eyebrow should read {group!r}, '
                            f'found {text(eyebrow.group(1)) if eyebrow else None!r}')
        if not h2 or text(h2.group(1)) != label:
            problems.append(f'{page}: title should match the nav label {label!r}, '
                            f'found {text(h2.group(1)) if h2 else None!r}')
        if not desc or not text(desc.group(1)):
            problems.append(f'{page}: no one-line .desc under the title')
        elif eyebrow and h2 and not (eyebrow.start() < h2.start() < desc.start()):
            problems.append(f'{page}: header parts out of order (eyebrow, title, desc)')
    return problems


@pytest.fixture(scope='module')
def src():
    return TEMPLATE.read_text(encoding='utf-8')


def test_every_page_header_agrees_with_the_sidebar(src):
    problems = header_problems(sidebar_groups(src), page_heads(src))
    assert not problems, 'page headers and the sidebar disagree:\n  ' + '\n  '.join(problems)


def test_the_scan_found_all_nine_pages_and_four_groups(src):
    """Vacuity guard: a regex that matched nothing would make the rule above
    pass over an empty page list."""
    assert len(page_heads(src)) == 9
    groups = sidebar_groups(src)
    assert [g for g, _ in groups] == ['This Week', 'Your Picks', 'Track Record', 'How It Was Built']
    assert sum(len(b) for _, b in groups) == 9


GOOD_NAV = ('<nav class="side-nav"><div class="nav-group-label">A</div>'
            '<button class="nav-btn" data-page="x">X</button></nav>')
GOOD_PAGE = ('<section class="page" id="page-x">\n    <div class="page-head">\n      <div>'
             '<div class="page-eyebrow">A</div><h2>X</h2><div class="desc">d</div></div>\n    </div>\n'
             '</section>')


@pytest.mark.parametrize('nav, page, expect', [
    (GOOD_NAV, GOOD_PAGE, None),
    (GOOD_NAV.replace('</nav>', '<div class="nav-group-label">A</div>'
                      '<button class="nav-btn" data-page="y">Y</button></nav>'), GOOD_PAGE, 'both called'),
    (GOOD_NAV, GOOD_PAGE.replace('>A<', '>B<'), 'eyebrow should read'),
    (GOOD_NAV, GOOD_PAGE.replace('<h2>X</h2>', '<h2>Z</h2>'), 'title should match'),
    (GOOD_NAV, GOOD_PAGE.replace('<div class="desc">d</div>', ''), 'no one-line .desc'),
    (GOOD_NAV, GOOD_PAGE.replace('<div class="page-head">', '<p>Welcome!</p><div class="page-head">'),
     'content before the page header'),
])
def test_the_header_rule_over_synthetic_markup(nav, page, expect):
    problems = header_problems(sidebar_groups(nav), page_heads(page))
    if expect is None:
        assert problems == []
    else:
        assert any(expect in p for p in problems), problems


def test_model_lab_does_not_type_the_model_version(src):
    """The header said 2.4 through the 2.5 release because the number was
    written into the markup. It is filled from modelVersion now."""
    head = page_heads(src)['modellab'][1]
    assert not re.search(r'\b\d+\.\d+\b', text(head)), (
        f'Model Lab header carries a literal version number: {text(head)!r}')
    assert 'id="modellab-version"' in head
    assert re.search(r"getElementById\('modellab-version'\)[\s\S]{0,300}modelVersion", src), (
        'nothing writes modelVersion into #modellab-version')
