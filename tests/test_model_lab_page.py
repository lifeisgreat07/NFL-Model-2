"""Model Lab's table is built from the experiment records (Stage 18).

generate_dashboard.render_model_lab_rows() writes one row per entry that
src/pipeline/model_lab.py builds, into the template's placeholder, at build time -- so
the table is there without JavaScript and every #modellab/<slug> link still
finds its row. These tests check nothing is typed into the template any
more, that a moved row reaches the page unchanged, that each row shows its
decision and, when it differs, the label it was first given, and that every
figure a registered row prints is the one in its file.

Run with: pytest tests/test_model_lab_page.py -v
"""
import html
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

from src.pipeline import generate_dashboard as gd
from src.pipeline import model_lab as ml
from src.pipeline.template_parts import JOINED_TEMPLATE, read_template

TEMPLATE = JOINED_TEMPLATE
ROW = re.compile(r'<tr><td>(.*?)</td><td>(.*?)</td><td>(.*?)</td></tr>', re.S)


@pytest.fixture(scope='module')
def entries():
    return ml.entries()


@pytest.fixture(scope='module')
def rows(entries):
    out = ROW.findall(gd.render_model_lab_rows(entries))
    assert len(out) == len(entries), 'a row the pattern cannot read -- re-anchor this guard'
    return out


def test_no_experiment_row_is_typed_into_the_template():
    t = TEMPLATE.read_text(encoding='utf-8')
    start = t.index('<section class="page" id="page-modellab">')
    body = t[t.index('<tbody>', start) + 7:t.index('</tbody>', start)]
    assert '<tr' not in body, 'a hand-written row is back in the Model Lab table'
    assert body.count('__MODEL_LAB_ROWS__') == 1


def test_the_build_fills_the_placeholder():
    src = (ROOT / 'src' / 'pipeline' / 'generate_dashboard.py').read_text(encoding='utf-8')
    assert "html.replace('__MODEL_LAB_ROWS__', render_model_lab_rows(model_lab_entries()))" in src


def test_every_entry_is_a_row_in_order(entries, rows):
    for e, (name, _, _) in zip(entries, rows):
        expected = e['experiment'] if e['stage'] is None else gd.html_escape(e['title'])
        assert name == expected


def test_a_moved_row_reaches_the_page_unchanged(entries, rows):
    for e, (name, result, _) in zip(entries, rows):
        if e['stage'] is None:
            assert (name, result) == (e['experiment'], e['result'])


def test_each_row_shows_its_decision_and_any_first_label(entries, rows):
    for e, (_, _, cell) in zip(entries, rows):
        assert cell.startswith(f'<span class="lab-tags"><span class="conf-tag tag-neutral">{e["decision"]}</span>')
        first = f'<span class="lab-first">First labelled {e["label"]}</span>'
        if e['label'] != e['decision']:
            assert first in cell, (e['id'], 'a mapped label must stay visible beside its decision')
        else:
            assert 'lab-first' not in cell


def test_a_rows_pills_share_one_row_and_never_break_inside(entries, rows):
    """"CONFIRMED FINDING" broke across two lines of one pill, and DEFERRED
    sat on LEAKAGE with nothing between them (Mark, 2026-09-28)."""
    src = read_template()
    tags = re.search(r'\.lab-tags\{([^}]*)\}', src)
    assert tags and 'display:flex' in tags.group(1).replace(' ', '') and 'gap:' in tags.group(1)
    pill = re.search(r'\.lab-tags \.conf-tag\{([^}]*)\}', src)
    assert pill and 'white-space:nowrap' in pill.group(1).replace(' ', '')
    for e, (_, _, cell) in zip(entries, rows):
        pills = re.fullmatch(r'<span class="lab-tags">((?:<span class="conf-tag tag-neutral">[A-Z ]+</span>)+)</span>'
                             r'(?:<span class="lab-first">[^<]*</span>)?', cell)
        assert pills, (e['id'], 'every pill must sit inside the one pill row', cell)
        assert pills.group(1).count('conf-tag') == (2 if e['leakage'] else 1), e['id']


def test_only_the_leakage_row_carries_the_flag(entries, rows):
    flagged = [e['id'] for e, (_, _, cell) in zip(entries, rows) if '>LEAKAGE</span>' in cell]
    assert flagged == [e['id'] for e in entries if e['leakage']] and len(flagged) == 1


def _number(text):
    return float(html.unescape(text).replace('−', '-'))


def test_every_figure_a_registered_row_prints_is_its_files(entries, rows):
    checked = 0
    for e, (_, result, _) in zip(entries, rows):
        h = e['headline']
        if not h:
            continue
        m = re.search(r' ((?:&minus;|\+)[\d.]+) CI \[((?:&minus;|\+)[\d.]+), ((?:&minus;|\+)[\d.]+)\] '
                      r'at ([\d.]+)%, .*?, ([\d,]+) ', result)
        assert m, (e['id'], result)
        diff, lo, hi, level, n = m.groups()
        assert abs(_number(diff) - h['diff']) <= 5e-5
        assert abs(_number(lo) - h['ci'][0]) <= 5e-5 and abs(_number(hi) - h['ci'][1]) <= 5e-5
        # At most two decimals: Stage 33's 1 - 0.05/3 printed as "98.3333%"
        # under a bare :g until 2026-10-02.
        assert float(level) == pytest.approx(h['ci_level'] * 100, abs=0.005)
        assert len(level.partition('.')[2]) <= 2, (e['id'], level)
        assert int(n.replace(',', '')) == h['n']
        assert f"<code>{e['source']}</code>" in result
        checked += 1
    assert checked >= 11


def test_a_row_says_which_step_its_figure_is_from(entries, rows):
    by_id = {e['id']: r for e, r in zip(entries, rows)}
    assert 'confirmation seasons 2024&ndash;2025' in by_id['H1'][1]
    assert 'validation screen 2022&ndash;2023; it did not go on to confirmation' in by_id['H2'][1]


def test_a_deferred_question_shows_its_reason(entries, rows):
    for e, (_, result, _) in zip(entries, rows):
        if e['stage'] and e['decision'] == 'DEFERRED':
            assert gd.html_escape(e['reason']) in result


def test_a_negative_difference_is_written_with_a_minus_sign():
    assert gd._signed(-0.0109) == '&minus;0.0109'
    assert gd._signed(0.0021) == '+0.0021'
