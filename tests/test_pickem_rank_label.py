"""The Week Board card names a game's pick'em rank and points in words.

Stage 11 (CLAUDE.md, "Stage 11 - Integrity and access"). The card read
"Confidence #6 · 11 pts": "Confidence #6" reads as a confidence LEVEL, and
"pts" is an abbreviation this site also uses, as "pt", for percentage
points. It now reads "Pick'em rank 6 (11 points)".

The label is generated, so it is executed rather than read -- the singular
and the missing-field cases are where generated copy goes wrong.

Run with: pytest tests/test_pickem_rank_label.py -v
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

TEMPLATE = Path(__file__).resolve().parents[1] / 'src' / 'dashboard_template.html'
NODE = shutil.which('node')

CASES = {
    'both': {'confidence_rank': 6, 'confidence_points': 11},
    'top': {'confidence_rank': 1, 'confidence_points': 16},
    'onePoint': {'confidence_rank': 16, 'confidence_points': 1},
    'rankOnly': {'confidence_rank': 6},
    'pointsOnly': {'confidence_points': 5},
    'neither': {},
}


@pytest.fixture(scope='module')
def source():
    return TEMPLATE.read_text(encoding='utf-8')


@pytest.fixture(scope='module')
def labels(source):
    if not NODE:
        pytest.skip('node not available')
    m = re.search(r'function pickemRankLabel\(.*?\n\}\n', source, re.S)
    assert m, 'pickemRankLabel is not findable -- re-anchor this guard'
    js = m.group(0) + f'\nconst C={json.dumps(CASES)};const o={{}};' \
        'for(const k in C)o[k]=pickemRankLabel(C[k]);process.stdout.write(JSON.stringify(o));'
    r = subprocess.run([NODE, '-e', js], capture_output=True, text=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_the_rank_and_points_read_as_words(labels):
    assert labels['both'] == "Pick'em rank 6 (11 points)"
    assert labels['top'] == "Pick'em rank 1 (16 points)"


def test_one_point_is_singular(labels):
    assert labels['onePoint'] == "Pick'em rank 16 (1 point)"


def test_a_missing_field_is_left_out_not_invented(labels):
    assert labels['rankOnly'] == "Pick'em rank 6"
    assert labels['pointsOnly'] == "Worth 5 points in pick'em"
    assert labels['neither'] == ''


def test_the_card_uses_the_label_and_the_old_wording_is_gone(source):
    code = re.sub(r'/\*.*?\*/', '', source, flags=re.S)
    code = re.sub(r'(?m)^\s*//.*$', '', code)
    assert '<span class="game-confidence">${pickemRankLabel(g)}</span>' in code, (
        "the Week Board card no longer prints its rank through pickemRankLabel")
    assert 'Confidence #' not in code, 'the card still says "Confidence #n"'
    # A number or an interpolation followed by "pts" is the printed form;
    # `pts` on its own is also a variable name in the chart code.
    printed = re.findall(r'(?:\d|\})\s*pts\b', code)
    assert not printed, f'a printed "pts" is back in the page: {printed}'
