"""The NHL's Ratings rows are the NFL's Power Ratings row (Stage 79 item 47, the 2026-10-13 UI/UX audit's V8).

Measured 2026-10-14 on the NHL's sample page at 390 and 1440 px, both
themes: Ratings was a plain table of numbers, with no bar, no printed scale
and no logo (0 .srs-bar-track, no .net-axis). Each club's row is now the
NFL's: rank, logo, code and name (the name hidden on a phone, as the NFL
hides it), and its goal rating as a bar about a zero line against the
league's largest, whose ends the column's header prints. Its sparkline and
rank move are not drawn: they need a rating's history, which the NHL's daily
run does not keep. The NBA has no Ratings page yet (after this audit: Mark, 2026-10-14).

Run with: pytest tests/test_nhl_ratings_row.py -v
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / 'src' / 'sports' / 'nhl' / 'pages' / 'nhl.js').read_text(encoding='utf-8')
NODE = shutil.which('node')


def fn(name):
    m = re.search(r'function %s\(.*?\n\}\n' % name, JS, re.S)
    assert m, f'{name} is not findable -- re-anchor this guard'
    return m.group(0)


def run(expr):
    if not NODE:
        pytest.skip('node not available')
    signed = re.search(r'^function signed\(.*$', JS, re.M).group(0)
    code = ("const DATA = {teams: {COL: {name: 'Colorado Avalanche'}}};\n"
            "function escapeHtml(s){ return String(s); }\n"
            "function logo(a){ return a === 'COL' ? 'col.svg' : ''; }\n"
            "function teamName(a){ return (DATA.teams[a] || {}).name || a; }\n"
            + signed + '\n' + fn('ratingAxisHtml') + fn('ratingRowHtml')
            + f'console.log(JSON.stringify({expr}));')
    r = subprocess.run([NODE, '-e', code], capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_a_row_is_the_power_ratings_row():
    row = run("ratingRowHtml({team: 'COL', goal: 0.5, shot: 2}, 0, 1)")
    assert row.startswith('<tr><td class="rank">1</td><td><div class="team-cell"><img class="team-logo" src="col.svg" ')
    assert '<span class="team-abbr">COL</span><span class="team-full">Colorado Avalanche</span></div></td>' in row
    assert '<div class="srs-bar-track diverging" ' in row and '<span class="net-value">+0.50</span>' in row
    assert row.endswith('<td class="num">+2.0</td></tr>')


def test_the_bar_grows_from_the_zero_line_against_the_leagues_largest():
    up, down = run("[ratingRowHtml({team: 'COL', goal: 0.5, shot: 2}, 0, 1), ratingRowHtml({team: 'XYZ', goal: -0.5, shot: 0}, 1, 1)]")
    assert 'style="left:50%; width:25%;"' in up
    assert 'style="left:25%; width:25%;"' in down
    assert '<span class="team-full">XYZ</span>' in down and '<img' not in down, 'no logo, no broken image'


def test_the_header_prints_the_scale():
    axis = run("ratingAxisHtml(0.97, 'Goals a game')")
    assert '<div class="net-axis" aria-hidden="true"><span class="ax-min">−0.97</span><span class="ax-zero">0</span><span class="ax-max">+0.97</span></div>' in axis


def test_the_page_draws_its_clubs_with_them():
    body = fn('renderRatings')
    assert 'const scale = Math.max(...r.teams.map(t => Math.abs(t.goal)), 0.01);' in body
    assert "${ratingAxisHtml(scale, 'Goals a game')}" in body
    assert '${r.teams.map((t, i) => ratingRowHtml(t, i, scale)).join(\'\')}' in body
