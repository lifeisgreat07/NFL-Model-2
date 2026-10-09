"""A page change sets the title, marks the nav button and moves focus
(Stage 26 item 2, from the 2026-09-28 audit).

Before: the tab said "Command Board" on every page, the chosen nav button was
marked only by .active, and focus stayed on the button that was pressed, so
a screen reader heard nothing of the page that had just replaced the last.
setActivePage() now marks every nav button for the page aria-current="page"
(and clears the rest), titles the document from the page's heading, and,
when the change is one the reader asked for, moves focus to that heading.
A nav click and Back/Forward ask for it; the first paint does not, so a page
opened from a link starts where pages normally start.

The page was driven in a browser for the PR (process note there); these
tests hold the source, since the suite has no browser.
"""
import re

from src.core.template_parts import read_template

TEMPLATE = read_template()


def set_active_page():
    m = re.search(r'function setActivePage\(pageId, opts\)\{.*?\n\}', TEMPLATE, re.S)
    assert m, 'setActivePage is not findable -- re-anchor this test'
    return m.group(0)


def test_the_board_starts_marked_as_the_current_page():
    for cls in ('nav-btn', 'bnav-btn'):
        tag = re.search(rf'<button class="{cls} active" data-page="board"[^>]*>', TEMPLATE)
        assert tag and 'aria-current="page"' in tag.group(0), f'the {cls} for the board is not marked current'


def test_every_nav_button_is_marked_or_cleared_on_a_change():
    body = set_active_page()
    assert "if(on) b.setAttribute('aria-current', 'page'); else b.removeAttribute('aria-current');" in body


def test_the_title_names_the_page_by_its_heading():
    body = set_active_page()
    assert 'const BASE_TITLE = document.title;' in TEMPLATE
    assert re.search(r"document\.title = \(pageId === 'board' \|\| !heading\) \? BASE_TITLE\s*"
                     r":\s*`\$\{heading\.textContent\.trim\(\)\} — Sportalytics`;", body), (
        'the document title is no longer set from the page heading')


def test_focus_moves_only_when_asked():
    body = set_active_page()
    assert re.search(r"if\(opts && opts\.focus && heading\)\{\s*heading\.setAttribute\('tabindex', '-1'\);"
                     r"\s*heading\.focus\(\{preventScroll:true\}\);", body), 'focus is not moved to the heading'


def test_a_nav_click_and_back_ask_for_focus_and_the_first_paint_does_not():
    assert re.search(r'function goToPage\(page\)\{\s*setActivePage\(page, \{focus:true\}\);', TEMPLATE)
    assert ("window.addEventListener('popstate', ()=> applyRoute(parseRoute(location.hash, routeKnown), "
            "{focus:true}));") in TEMPLATE
    assert 'if(location.hash) applyRoute(parseRoute(location.hash, routeKnown));' in TEMPLATE
    assert 'setActivePage(r.page, opts);' in TEMPLATE


def test_every_page_has_a_heading_to_title_and_focus():
    pages = re.findall(r'<section class="page[^"]*" id="page-([a-z]+)">(.*?)</section>', TEMPLATE, re.S)
    assert len(pages) >= 9, f'only {len(pages)} pages found -- re-anchor this test'
    missing = [p for p, body in pages if not re.search(r'<h2[\s>]', body)]
    assert not missing, f'pages with no h2 to name them: {missing}'
