"""The home page says when it was made, and how much of a locked NFL week is left (Stage 77 item 30, the 2026-10-13 UI/UX audit's H2).

The home printed no "Updated" line anywhere, though each sport's page does,
and its NFL card showed a locked week as "Week 6 locked" all the way through
it (measured 2026-10-14 at 390 and 1440 px, both themes). The build now
records when the page was made, the page prints "Updated <date, time> ET"
under the cards, and once a locked week has begun the NFL card says how many
games have kicked off and how many are to play. The NHL's and NBA's cards
gained their "N final, M to play" in Stage 77 item 12.

Run with: pytest tests/test_home_updated.py -v
"""
import json
import os
import re
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from src.site import home

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / 'src' / 'site' / 'home' / 'home.js').read_text(encoding='utf-8')
PAGE = (ROOT / 'src' / 'site' / 'home' / 'page.html').read_text(encoding='utf-8')
NODE = shutil.which('node')


def node(code, tz=None):
    if not NODE:
        pytest.skip('node not available')
    env = {**os.environ, 'TZ': tz} if tz else None
    r = subprocess.run([NODE, '-e', code], capture_output=True, encoding='utf-8', env=env)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def nfl_status(now, kickoffs):
    keep = ''.join(re.search(r'^function %s\(.*$' % n, JS, re.M).group(0) + '\n' for n in ('esc', 'clock', 'weekday', 'when', 'record'))
    fns = ''.join(re.search(r'function %s\(.*?\n\}\n' % n, JS, re.S).group(0) for n in ('nflCard',))
    code = (f'const NOW = Date.parse({json.dumps(now)});\n' + keep
            + 'function notBuilt(){ return null; }\n'
            + 'function card(sport, name, href, status){ return status.text; }\n' + fns
            + 'console.log(JSON.stringify(nflCard(%s)));' % json.dumps(
                {'built': True, 'week': 6, 'kickoffs': kickoffs, 'record': {'label': 'Model B', 'won': 1, 'lost': 0}}))
    return node(code)


KICKS = ['2026-10-16T00:15:00Z', '2026-10-18T13:30:00Z', '2026-10-18T17:00:00Z', '2026-10-18T17:00:00Z']


def test_a_locked_week_says_how_much_is_left_once_it_has_begun():
    assert nfl_status('2026-10-15T20:00:00Z', KICKS) == 'Week 6 locked'
    assert nfl_status('2026-10-17T12:00:00Z', KICKS) == 'Week 6 locked · 1 kicked off, 3 to play'
    assert nfl_status('2026-10-18T16:00:00Z', KICKS) == 'Week 6 locked · 2 kicked off, 2 to play'


def test_the_page_says_when_it_was_made_in_eastern_time():
    fn = re.search(r'function updatedText\(iso\)\{.*?\n\}\n', JS, re.S)
    assert fn, 'updatedText is not findable -- re-anchor this guard'
    got = node(fn.group(0) + 'console.log(JSON.stringify([updatedText("2026-10-14T18:39:00Z"), updatedText(null)]));',
               tz='Pacific/Auckland')  # far from ET, so a page that drops timeZone shows 7:39 AM
    assert got == ['Updated Oct 14, 2:39 PM ET', '']
    assert "document.getElementById('home-updated').textContent = updatedText(HOME.built_utc);" in JS
    assert '<p class="home-updated" id="home-updated"></p>' in PAGE


def test_the_build_records_when_it_ran():
    now = datetime(2026, 10, 14, 18, 39, tzinfo=UTC)
    assert home.facts(now=now)['built_utc'] == '2026-10-14T18:39:00Z'
