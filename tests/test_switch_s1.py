"""One sport switcher on every page: the segmented control (Stage 68 item 35).

The audit (U11) found two designs: 28 px inverted pills on the sport pages
and the home page's 40 px segmented control. Mark chose the segmented
control for every page on 2026-10-10 (option S1 of the rendered "Stage 68
Design Options").

Run with: pytest tests/test_switch_s1.py -v
"""
import re
from pathlib import Path

CSS = (Path(__file__).resolve().parents[1] / 'src' / 'dashboard' / 'styles.css').read_text(encoding='utf-8')


def rule(selector):
    m = re.search(r'(?m)^\s*' + re.escape(selector) + r'\{([^}]*)\}', CSS)
    assert m, selector
    return m.group(1)


def test_the_links_are_forty_pixel_segments():
    a = rule('.sport-switch a')
    assert 'min-height:40px' in a and 'background:transparent' in a and 'border:0' in a


def test_the_control_is_one_track():
    box = rule('.sport-switch')
    assert 'background:var(--surface-2)' in box and 'border-radius:var(--r-full)' in box and 'flex-wrap:nowrap' in box


def test_the_current_sport_is_raised_not_inverted():
    cur = rule('.sport-switch a[aria-current="page"]')
    assert 'background:var(--surface)' in cur and 'color:var(--text)' in cur
    assert 'var(--text);' not in cur.split('color:var(--text)')[0], 'no inverted fill'


def test_in_the_sidebar_it_keeps_inside_the_margins():
    assert 'margin:var(--s3) var(--s4) 0' in rule('.sidebar .sport-switch')
    assert 'flex:1' in rule('.sidebar .sport-switch a')
