"""One sport switcher on every page (Stage 68 item 35), a menu since audit 9 D3.

The audit (U11) found two designs: 28 px inverted pills on the sport pages and the home page's 40 px
segmented control. Mark chose the segmented control for every page on 2026-10-10 (option S1 of the rendered
"Stage 68 Design Options"), and on 2026-11-16 (audit 9, M1 B) a menu in its place: its button the page you
are on, its rows Home and every sport. What carries over from S1: a row is a full tap target, the current
page is raised with a hairline rather than inverted, and in the sidebar the control keeps inside the margins.

Run with: pytest tests/test_switch_s1.py -v
"""
import re
from pathlib import Path

CSS = (Path(__file__).resolve().parents[1] / 'src' / 'dashboard' / 'styles.css').read_text(encoding='utf-8')


def rule(selector):
    m = re.search(r'(?m)^\s*' + re.escape(selector) + r'\{([^}]*)\}', CSS)
    assert m, selector
    return m.group(1)


def test_the_rows_and_the_button_are_full_tap_targets():
    a = rule('.sport-switch a')
    assert 'min-height:44px' in a and 'background:transparent' in a and 'border:0' in a
    assert 'min-height:44px' in rule('.sm > summary')


def test_the_button_is_one_rounded_control_and_the_list_a_panel():
    box = rule('.sm > summary')
    assert 'background:var(--surface-2)' in box and 'border-radius:var(--r-full)' in box and 'list-style:none' in box
    assert 'display:none' in rule('.sm > summary::-webkit-details-marker'), 'the browser\'s own triangle shows too'
    panel = rule('.sm-list')
    assert 'flex-direction:column' in panel and 'background:var(--surface)' in panel


def test_the_current_page_is_raised_not_inverted():
    cur = rule('.sport-switch a[aria-current="page"]')
    assert 'background:var(--surface-2)' in cur and 'color:var(--text)' in cur
    assert 'inset 0 0 0 1px var(--border-strong)' in cur
    assert 'var(--text);' not in cur.split('color:var(--text)')[0], 'no inverted fill'


def test_in_the_sidebar_it_keeps_inside_the_margins():
    assert 'margin:var(--s3) var(--s4) 0' in rule('.sidebar .sport-switch')
    assert 'min-width:0' in rule('.sidebar .sm-list')
