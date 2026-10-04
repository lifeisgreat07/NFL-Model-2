"""
Team Deep-Dive's offense and defense beside net (Stage 19, 2026-09-28).

The generator used to carry `{label, net}` only; both history files already
held offense and defense. Mark's calls: on a phone the pair takes a second
small line, and defense carries "lower is better", because it is expected
points allowed -- the one number on the page that runs backwards.

Held here: the data reaches the page from both files, net really is offense
minus defense (so the note is true), the pair is drawn through the rating
formatter or not at all, and the phone layout exists and is not beaten by an
earlier rule.

Run with: pytest tests/test_dive_off_def.py -v
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

from src.pipeline import generate_dashboard as gd
from src.pipeline.template_parts import JOINED_TEMPLATE

TEMPLATE = JOINED_TEMPLATE
NODE = shutil.which('node')


@pytest.fixture(scope='module')
def history():
    return gd.load_team_history()


def test_every_history_point_carries_offense_and_defense(history):
    points = [p for pts in history['timeline'].values() for p in pts]
    assert len(points) > 32, 'vacuity: the timeline is nearly empty'
    missing = [p['label'] for p in points if not isinstance(p.get('off'), (int, float))
               or not isinstance(p.get('def'), (int, float))]
    assert not missing, f'{len(missing)} points without offense/defense, e.g. {missing[:3]}'
    assert any('Wk' in p['label'] for p in points), (
        'no live week in the timeline -- the live file half was not checked')


def test_net_is_offense_minus_defense(history):
    """The page's note says so; this is what makes it true."""
    for team, pts in history['timeline'].items():
        for p in pts:
            assert abs(p['off'] - p['def'] - p['net']) <= 0.0002, (
                f"{team} {p['label']}: {p['off']} - {p['def']} != {p['net']}")


def function_source(src, name):
    m = re.search(r'function ' + name + r'\(.*?\n\}\n', src, re.S)
    assert m, f'{name} is not findable -- re-anchor this guard'
    return m.group(0)


CASES = {
    'both': {'net': 0.1491, 'off': 0.1538, 'def': 0.0048},
    'net_only': {'net': 0.1491},
    'def_missing': {'net': 0.1491, 'off': 0.1538, 'def': None},
}


@pytest.fixture(scope='module')
def split():
    if not NODE:
        pytest.skip('node not available')
    src = TEMPLATE.read_text(encoding='utf-8')
    # The formatter and the scale it reads, as tests/test_per_100_plays.py
    # extracts them.
    fmt = re.search(r'function ratingScale\(\).*?\nfunction fmtRatingScale\(.*?\n\}\n', src, re.S)
    assert fmt, 'the rating formatters are not findable -- re-anchor this guard'
    js = fmt.group(0) + function_source(src, 'diveSplitHtml') + \
        f'\nconst C={json.dumps(CASES)};const o={{}};' \
        'for(const k in C){try{o[k]=diveSplitHtml(C[k]);}catch(e){o[k]="THREW: "+e.message;}}' \
        'process.stdout.write(JSON.stringify(o));'
    r = subprocess.run([NODE, '-e', js], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_both_are_shown_in_the_rating_units(split):
    html = split['both']
    assert 'Offense +15.4' in html, html
    assert 'Defense +0.5' in html, html


def test_defense_says_lower_is_better(split):
    assert re.search(r'title="[^"]*lower is better"[^>]*>Defense', split['both']), split['both']
    note = function_source(TEMPLATE.read_text(encoding='utf-8'), 'renderTeamDive')
    assert 'for defense lower is better' in note


def test_a_point_without_both_draws_nothing(split):
    assert split['net_only'] == ''
    assert split['def_missing'] == '', 'half a split would read as defense being zero'


def test_every_row_draws_it():
    body = function_source(TEMPLATE.read_text(encoding='utf-8'), 'renderTeamDive')
    assert '<span class="dive-value">${fmtRating(p.net)}</span>\n      ${diveSplitHtml(p)}' in body


def test_on_a_phone_the_pair_takes_its_own_line():
    """Read with comments blanked (CLAUDE.md: an unclosed comment swallows
    what follows while a raw-text test still passes), and the phone rule must
    come after the base rule it overrides, or source order beats it."""
    css = re.sub(r'/\*.*?\*/', lambda m: ' ' * len(m.group(0)), TEMPLATE.read_text(encoding='utf-8'), flags=re.S)
    base = css.index('.dive-split{display:flex')
    phone = re.search(r'@media \(max-width:767px\)\{\s*\.dive-row\{flex-wrap:wrap;[^}]*\}\s*'
                      r'\.dive-row \.srs-bar-track\{flex:1 1 0;[^}]*\}\s*'
                      r'\.dive-split\{flex-basis:100%;', css)
    assert phone, ('no phone rule putting the offense/defense pair on its own line, with the '
                   'bar giving up width so the net value stays on the first (without it a row '
                   'wraps to three lines at 375px)')
    assert phone.start() > base, 'the phone rule comes before the base rule and loses to it'


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))
