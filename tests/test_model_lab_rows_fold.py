"""Audit 9 D9 (M4, Mark's choice of 2026-11-16): each NFL Model Lab row with a
figure shows its glyph, then the figure and interval on one line, and folds
the sentence and its source under "Details". A deferred row keeps its reason
in view. The 65 rows had run to 16,809 px on a phone.

Run with: pytest tests/test_model_lab_rows_fold.py -v
"""
import re
from pathlib import Path

from src.sports.nfl import generate_dashboard as gd
from src.sports.nfl import model_lab as ml

ROOT = Path(__file__).resolve().parents[1]
ROW = re.compile(r'<tr><td>(.*?)</td><td>(.*?)</td><td>(.*?)</td></tr>', re.S)
FOLD = re.compile(r'^<span class="lab-lead">.*?</span><span class="lab-brief">(.*?)</span>'
                  r'<details class="disclosure lab-more"><summary>Details</summary>'
                  r'<div class="lab-more-body">(.*)</div></details>$', re.S)


def rows():
    entries = ml.entries()
    return list(zip(entries, ROW.findall(gd.render_model_lab_rows(entries))))


def test_a_row_with_a_figure_shows_it_and_folds_the_sentence():
    folded = 0
    for e, (_, result, _) in rows():
        h = e['headline'] if e['stage'] else None
        if not h:
            continue
        m = FOLD.match(result)
        assert m, e['id']
        brief, inside = m.groups()
        assert f"{gd._signed(h['diff'])} [{gd._signed(h['ci'][0])}, {gd._signed(h['ci'][1])}]" in brief, e['id']
        assert 'CI [' in inside and 'lab-src' in inside, (e['id'], 'the sentence and its source are under Details')
        assert 'lab-src' not in brief
        folded += 1
    assert folded >= 11


def test_the_fold_starts_closed():
    for e, (_, result, _) in rows():
        assert '<details class="disclosure lab-more" open' not in result, e['id']
        assert ' open>' not in result, e['id']


def test_a_deferred_row_keeps_its_reason_and_source_in_view():
    seen = 0
    for e, (_, result, _) in rows():
        if e['stage'] and e['headline'] is None:
            assert '<details' not in result, e['id']
            assert gd.html_escape(e['reason']) in result and 'lab-src' in result, e['id']
            seen += 1
    assert seen >= 1


def test_the_details_target_is_large_enough_to_tap():
    css = (ROOT / 'src' / 'dashboard' / 'styles.css').read_text(encoding='utf-8')
    rule = re.search(r'\.lab-more > summary\{([^}]*)\}', css)
    assert rule and 'min-height:44px' in rule.group(1)
