"""The NBA page's Power Ratings and Teams (Stage 104 item 3).

The daily run writes results/nba/ratings_<season>.json (tests/test_daily_end_to_end.py
holds that); here the page data carries it, and the two pages draw it, run under
node with the page's own functions and only the DOM stubbed.

Run with: pytest tests/test_nba_ratings_page.py -v
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from src.sports.nba import site
from tests.optional import in_ci

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / 'src' / 'sports' / 'nba' / 'pages' / 'nba.js').read_text(encoding='utf-8').replace('\r\n', '\n')
NODE = shutil.which('node')


def fn(name):
    return re.search(rf'^function {name}\(.*?\n\}}\n', JS, re.S | re.M).group(0)


def test_the_page_data_carries_the_ratings_file(monkeypatch):
    real = site._maybe
    fake = {'as_of': '2026-11-11', 'teams': []}
    monkeypatch.setattr(site, '_maybe', lambda p: fake if p.name == 'ratings_2026.json' else real(p))
    assert site.board(2026)['ratings'] is fake


def run(call, bd):
    one_liners = ''.join(re.search(rf'^function {n}\(.*$', JS, re.M).group(0) + '\n' for n in ('signed', 'clubName'))
    src = ('const out = {}; const document = {getElementById: () => out, documentElement: {getAttribute: () => null}};'
           'function stateHtml(k, t, x){ return `STATE ${t}`; } function escapeHtml(s){ return String(s); }'
           f'const BD = {json.dumps(bd)};' + one_liners + fn('logo') + fn('ratingAxisHtml') + fn('ratingRowHtml')
           + fn('renderRatings') + call + 'process.stdout.write(out.innerHTML);')
    return subprocess.run([NODE, '-e', src], capture_output=True, text=True, encoding='utf-8', check=True).stdout


BD = {'teams': {'BOS': {'name': 'Boston', 'logo': 'b.svg'}, 'NY': {'name': 'New York', 'logo': 'n.svg'}},
      'ratings': {'as_of': '2026-11-11', 'teams': [{'team': 'BOS', 'point': 6.0, 'efficiency': 5.5},
                                                     {'team': 'NY', 'point': -3.0, 'efficiency': -2.4}]}}


@pytest.mark.skipif(NODE is None and not in_ci(), reason='node is not installed')
def test_power_ratings_rank_the_clubs_as_the_file_does_with_both_ratings():
    out = run('renderRatings();', BD)
    rows = re.findall(r'<td class="rank">(\d+)</td>.*?class="team-abbr">(\w+)<.*?class="net-value">([^<]+)<.*?<td class="num">([^<]+)</td></tr>', out)
    assert rows == [('1', 'BOS', '+6.0', '+5.5'), ('2', 'NY', '\u22123.0', '\u22122.4')], rows
    assert 'As of 2026-11-11' in out and 'width:50%' in out, 'the largest rating fills its half of the bar'


@pytest.mark.skipif(NODE is None and not in_ci(), reason='node is not installed')
def test_power_ratings_say_so_before_the_first_file():
    assert run('renderRatings();', {'teams': {}, 'ratings': None}).startswith('STATE No ratings yet')


def test_teams_counts_the_record_from_final_games_only():
    src = JS[JS.index('function teamRecord('):]
    assert "g.status === 'final' && g.hs !== null && g.hs !== undefined" in src[:400]
    init = JS[JS.index('installFavStars(renderBoard);'):]
    assert 'renderRatings();\nrenderTeams();\n' in init[:200], 'both pages are built at load'
