"""The home page's tiles in plain words (Stage 77 item 13, the 2026-10-13 UI/UX audit's copy fix 2).

"NFL, Model B 49–29 / NHL, picks 25–12 / Every pick saved before the start"
became "NFL picks 49–29 / NHL picks 25–12 / 3 sports · 115 picks graded".
The third tile adds up every built sport's record. Run under node.

Run with: pytest tests/test_home_tiles.py -v
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / 'src' / 'site' / 'home' / 'home.js').read_text(encoding='utf-8')
NODE = shutil.which('node')


def graded_tile(sports):
    if not NODE:
        pytest.skip('node not available')
    one = ''.join(re.search(rf'^function {n}\(.*$', JS, re.M).group(0) + '\n' for n in ('esc',))
    multi = ''.join(re.search(rf'^function {n}\(.*?\n\}}\n', JS, re.S | re.M).group(0) for n in ('tile', 'gradedTile'))
    code = one + multi + 'process.stdout.write(gradedTile(%s));' % json.dumps(sports)
    r = subprocess.run([NODE, '-e', code], capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return r.stdout


def test_the_third_tile_counts_every_graded_pick_across_the_built_sports():
    out = graded_tile([{'built': True, 'record': {'won': 49, 'lost': 29}}, {'built': True, 'record': {'won': 25, 'lost': 12}},
                       {'built': True, 'record': {'won': 0, 'lost': 0}}])
    assert '<span>3 sports</span><b>115</b><small>picks graded</small>' in out
    out = graded_tile([{'built': True, 'record': {'won': 1, 'lost': 0}}, {'built': False}, None])
    assert '<span>1 sport</span><b>1</b><small>pick graded</small>' in out


def test_the_tiles_say_picks():
    line = JS[JS.index("document.getElementById('home-score').innerHTML"):]
    line = line[:line.index(';\n')]
    assert "scoreTile(HOME.nfl, 'NFL picks')" in line and "scoreTile(HOME.nhl, 'NHL picks')" in line
    assert 'gradedTile([HOME.nfl, HOME.nhl, HOME.nba])' in line
    assert 'saved before the start' not in line and 'Model B' not in line
