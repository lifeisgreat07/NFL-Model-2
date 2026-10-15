"""The numbers behind an NFL pick are points of win chance, not raw model terms (Stage 77 item 23, the 2026-10-13 UI/UX audit's copy row 12).

The card's "+ the numbers behind this" panel printed "Offense edge +0.055".
That number is the part's push on Model A's log-odds toward the home team,
so the audit's suggested "+5.5 points per 100 plays" would have named the
wrong unit (Mark chose this reading on 2026-10-14). Each row now reads the
team the part helped and the points of win chance it gave them: Model A's
chance with the part, less the chance with it taken back out. whyChance runs
here under node.

Run with: pytest tests/test_why_chance.py -v
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / 'src' / 'dashboard' / 'app.js'
NODE = shutil.which('node')


def why_chance(cases):
    if not NODE:
        pytest.skip('node not available')
    js = JS.read_text(encoding='utf-8')
    fn = re.search(r'function whyChance\(val, homePct, home, away\)\{.*?\n\}\n', js, re.S)
    assert fn, 'whyChance is not findable -- re-anchor this guard'
    code = fn.group(0) + 'console.log(JSON.stringify(%s.map(c => whyChance(...c))));' % json.dumps(cases)
    r = subprocess.run([NODE, '-e', code], capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_a_push_reads_as_points_of_win_chance_for_the_team_it_helped():
    # SEA at DEN, week 6: Model A gave DEN 66%. The offense term +0.055
    # pushes toward DEN, the defense term -0.041 toward SEA.
    assert why_chance([[0.055, 66, 'DEN', 'SEA'], [-0.041, 66, 'DEN', 'SEA'],
                       [0.036, 66, 'DEN', 'SEA']]) == ['DEN +1.2', 'SEA +0.9', 'DEN +0.8']


def test_the_size_follows_how_sure_the_model_is():
    # The same push moves a coin flip further than a near-certain pick.
    assert why_chance([[0.2, 50, 'H', 'A'], [0.2, 90, 'H', 'A']]) == ['H +5.0', 'H +1.9']


def test_no_push_and_no_chance_are_said_plainly():
    assert why_chance([[0.0, 60, 'H', 'A'], [0.0004, 60, 'H', 'A'],
                       [0.1, None, 'H', 'A'], [0.1, 100, 'H', 'A']]) == ['even', 'even', '—', '—']


def test_the_board_panel_prints_every_row_this_way_under_a_caption():
    js = JS.read_text(encoding='utf-8')
    panel = js[js.index('<div class="why-panel" id="why-${idSafe}">'):]
    panel = panel[:panel.index('trackRecordHtml(')]
    assert "<p class=\"why-unit\">Points of win chance each part gave a team in Model A's pick.</p>" in panel
    rows = re.findall(r"whyRow\('([^']+)', g\.why\.(\w+)(.*?)\)(?:\}| :)", panel)
    assert [r[0] for r in rows] == ['Offense edge', 'Defense edge', 'QB edge', 'O-line continuity']
    for label, key, rest in rows:
        assert rest.startswith(', whyChance(g.why.%s, g.fbA_home, g.home, g.away)' % key), label
    assert 'per 100 plays' not in panel


def test_the_value_cell_keeps_to_one_line():
    css = (ROOT / 'src' / 'dashboard' / 'styles.css').read_text(encoding='utf-8')
    rule = re.search(r'\.why-val\{[^}]*\}', css).group(0)
    assert 'white-space:nowrap' in rule and 'min-width:52px' in rule
