"""The desktop sidebar scrolls when it is taller than the window (audit 9, finding D1).

The rendered proof is `tests/browser/check_sidebar_reach.py`, which the Browser checks workflow runs on all three
sport pages. These hold the rules it rests on and the workflow steps that run it.

Run with: pytest tests/test_sidebar_scroll.py -v
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = (ROOT / 'src' / 'dashboard' / 'styles.css').read_text(encoding='utf-8')
WORKFLOW = (ROOT / '.github' / 'workflows' / 'browser-checks.yml').read_text(encoding='utf-8')


def rule(selector, having=''):
    """The declarations of the one rule whose selector is exactly `selector` (and that holds `having`)."""
    found = [r for r in re.findall(r'(?m)^\s*' + re.escape(selector) + r'\s*\{([^}]*)\}', CSS) if having in r]
    assert len(found) == 1, f'{len(found)} rules for {selector}'
    return re.sub(r'/\*.*?\*/', '', found[0], flags=re.S)


def test_the_tab_list_scrolls_and_its_items_keep_their_height():
    nav = rule('nav.side-nav')
    assert 'overflow-y:auto' in nav and 'flex:0 1 auto' in nav and re.search(r'min-height:\d+px', nav)
    assert 'flex-shrink:0' in rule('nav.side-nav > *'), 'or a short window squeezes the buttons instead of scrolling'


def test_the_whole_sidebar_scrolls_in_a_window_too_short_for_the_list_to_absorb():
    bar = rule('.sidebar', having='height:100vh')  # the phone's rule hides it and has no height
    assert 'position:sticky' in bar and 'overflow-y:auto' in bar


def test_the_more_mark_never_takes_a_click_and_adds_no_height():
    mark = rule('nav.side-nav::after')
    assert 'pointer-events:none' in mark and 'position:sticky' in mark and 'opacity:0' in mark
    height = re.search(r'flex:0 0 (var\(--s\d\))', mark).group(1)
    assert f'margin-top:calc(-1 * {height})' in mark
    assert 'animation-timeline:scroll()' in mark, 'shown only where the list really scrolls'


def test_the_browser_checks_run_the_reach_check_on_all_three_sport_pages_and_prove_it_can_fail():
    assert 'python tests/browser/check_sidebar_reach.py --self-test --tmp "$RUNNER_TEMP/reach"' in WORKFLOW
    assert ('python tests/browser/check_sidebar_reach.py index.html "$RUNNER_TEMP/states/nhl.html" '
            '"$RUNNER_TEMP/states/nba.html"') in WORKFLOW
