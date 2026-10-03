"""Team Deep-Dive says whose page it is, with the team's logo (2026-09-28).

Mark asked for the logo on the page because it re-establishes which team is
being viewed: the only other place the team is named is the picker button.
diveTeamHtml() is executed here rather than read, and renderTeamDive() is
checked to draw it above everything else.

Run with: pytest tests/test_team_dive_logo.py -v
"""
import json
import re
import shutil
import subprocess

import pytest

from src.pipeline.template_parts import JOINED_TEMPLATE  # noqa: E402

TEMPLATE = JOINED_TEMPLATE
NODE = shutil.which('node')


def src():
    return TEMPLATE.read_text(encoding='utf-8').replace('\r\n', '\n')


def run(expr):
    if not NODE:
        pytest.skip('node not available')
    s = src()
    js = re.search(r'const ESPN_CODE = \{.*?\n\};\n', s, re.S).group(0)
    for name in ('teamLogo', 'diveTeamHtml'):
        m = re.search(r'function ' + name + r'\(.*?\n\}\n', s, re.S)
        assert m, f'{name} is not findable -- re-anchor this guard'
        js += m.group(0)
    r = subprocess.run([NODE, '-e', js + f'\nprocess.stdout.write(JSON.stringify({expr}));'],
                       capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_the_page_names_its_team_with_logo_and_full_name():
    html = run('diveTeamHtml("KC", "Kansas City Chiefs")')
    assert html == ('<div class="dive-team"><img class="dive-logo" '
                    'src="https://a.espncdn.com/i/teamlogos/nfl/500/kc.png" alt="" loading="lazy" referrerpolicy="no-referrer" '
                    'onerror="this.style.display=\'none\'"><span class="dive-team-name">Kansas City Chiefs</span></div>')


def test_the_logo_is_decorative_and_a_missing_one_leaves_the_name():
    html = run('diveTeamHtml("KC", "Kansas City Chiefs")')
    img = re.search(r'<img [^>]*>', html).group(0)
    assert ' alt=""' in img and 'onerror="this.style.display=\'none\'"' in img


def test_a_team_with_no_name_on_file_shows_its_abbreviation():
    assert '<span class="dive-team-name">KC</span>' in run('diveTeamHtml("KC", undefined)')


def test_the_team_comes_first_on_the_page():
    body = re.search(r'function renderTeamDive\(.*?\n\}\n', src(), re.S).group(0)
    assert 'content.innerHTML = diveTeamHtml(team, teamHistory.names[team]) + renderTeamNews(team)' in body


def test_the_logo_is_large_enough_to_identify_the_page():
    m = re.search(r'\.dive-logo\{([^}]*)\}', src())
    assert m and 'width:48px' in m.group(1).replace(' ', '') and 'height:48px' in m.group(1).replace(' ', '')
