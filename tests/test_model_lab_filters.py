"""Model Lab can be filtered by decision, with counts (Stage 18).

wireLabFilters() reads the rendered experiment rows, and labChips() turns
them into one chip per decision the table holds -- All first, then the five
decisions in a fixed order, then the leakage flag -- each carrying its count.
The counting and the matching are executed here in node over synthetic rows;
the wiring around them is checked in the source.

Run with: pytest tests/test_model_lab_filters.py -v
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

TEMPLATE = Path(__file__).resolve().parents[1] / 'src' / 'pipeline' / 'dashboard_template.html'
NODE = shutil.which('node')


def src():
    return TEMPLATE.read_text(encoding='utf-8').replace('\r\n', '\n')


def run(expr):
    if not NODE:
        pytest.skip('node not available')
    s = src()
    code = re.search(r'const LAB_DECISIONS = .*?\nfunction labRowMatches\(.*?\n\}\n', s, re.S)
    assert code, 'the chip functions are not findable -- re-anchor this guard'
    r = subprocess.run([NODE, '-e', code.group(0) + f'\nprocess.stdout.write(JSON.stringify({expr}));'],
                       capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


ROWS = ([{'decision': 'REJECT', 'leakage': False}] * 3 + [{'decision': 'ACCEPT', 'leakage': False}]
        + [{'decision': 'DEFERRED', 'leakage': True}, {'decision': 'DEFERRED', 'leakage': False}])


def test_each_chip_carries_the_count_of_its_rows_in_a_fixed_order():
    chips = run(f'labChips({json.dumps(ROWS)})')
    assert [(c['key'], c['label'], c['n']) for c in chips] == [
        ('all', 'All', 6), ('ACCEPT', 'Accept', 1), ('REJECT', 'Reject', 3),
        ('DEFERRED', 'Deferred', 2), ('leakage', 'Leakage', 1)]


def test_a_decision_the_table_does_not_hold_gets_no_chip():
    chips = run(f'labChips({json.dumps(ROWS)})')
    assert not any(c['key'] in ('INCONCLUSIVE', 'CONFIRMED FINDING') for c in chips)
    assert [c['key'] for c in run('labChips([{"decision":"REJECT","leakage":false}])')] == ['all', 'REJECT']


def test_a_chip_shows_exactly_its_rows():
    got = run(f'["all","REJECT","DEFERRED","leakage","ACCEPT"].map(k => '
              f'{json.dumps(ROWS)}.filter(r => labRowMatches(r, k)).length)')
    assert got == [6, 3, 2, 1, 1]


def test_the_chips_are_counted_from_the_rendered_rows():
    body = re.search(r'\(function wireLabFilters\(\)\{.*?\n\}\)\(\);', src(), re.S)
    assert body, 'wireLabFilters is not findable -- re-anchor this guard'
    assert '.table-wrap[data-scroll-label="Experiment log"] tbody tr' in body.group(0)
    assert "td:last-child .conf-tag" in body.group(0)


def test_the_chip_row_is_hidden_until_the_script_can_make_it_work():
    assert re.search(r'<div class="filter-row" id="lab-filter-row"[^>]*\shidden>', src())
    assert 'bar.hidden = false;' in src()


def test_a_link_to_a_filtered_out_row_clears_the_filter():
    body = re.search(r'function applyRoute\(.*?\n\}\n', src(), re.S).group(0)
    assert 'if(row && row.hidden && labShowAll) labShowAll();' in body


def test_the_filter_says_how_many_rows_it_shows():
    assert '<p class="visually-hidden" id="lab-filter-status" aria-live="polite"></p>' in src()
    assert 'Showing ${shown} of ${rows.length} experiments.' in src()
