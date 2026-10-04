"""The Week Board's kickoff slots and regional TV pills (Stage 37 item 2).

Mark's observation in the 2026-10-04 audit: on a Sunday the board repeats
"CBS" and "FOX" on every afternoon card, though which of those games a
viewer gets depends on where they live. The pill now says "regional", and
under the chronological sort the cards sit under one header per kickoff
slot. Under any other sort there are no slot headers: they would contradict
the order the cards are in.

The functions run in node, taken from the shipped template.

Run with: pytest tests/test_board_slots.py -v
"""
import json
import re
import shutil
import subprocess

import pytest

from src.pipeline.template_parts import JOINED_TEMPLATE

NODE = shutil.which('node')


def template():
    return JOINED_TEMPLATE.read_text(encoding='utf-8')


def function_source(src, name):
    m = re.search(r'function ' + name + r'\(.*?\n\}\n', src, re.S)
    assert m, f'{name} is not findable -- re-anchor this guard'
    return m.group(0)


def const_line(src, name):
    m = re.search(r'^const ' + name + r' = .*?;\n', src, re.M | re.S)
    assert m, f'{name} is not findable -- re-anchor this guard'
    return m.group(0)


def game(day, time, tv=None, regional=False, home='H', away='A', weekday='Sunday'):
    return {'gameday': day, 'gametime_et': time, 'weekday': weekday, 'tv': tv,
            'tv_regional': regional, 'home': home, 'away': away, 'graded': False, 'status': 'upcoming'}


SLATE = [game('2026-10-04', '13:00', 'CBS', True, 'H1', 'A1'),
         game('2026-10-04', '13:00', 'FOX', True, 'H2', 'A2'),
         game('2026-10-04', '16:25', 'CBS', True, 'H3', 'A3'),
         game('2026-10-04', '20:20', 'NBC', False, 'H4', 'A4')]


@pytest.fixture(scope='module')
def out():
    if not NODE:
        pytest.skip('node not available')
    src = template()
    js = (const_line(src, 'KICKOFF_MONTHS') + function_source(src, 'escapeHtml') +
          function_source(src, 'kickoffLabel') + function_source(src, 'cardTvPill') +
          function_source(src, 'slotKey') + function_source(src, 'slotHeadBefore') +
          f'let currentSort = "chronological"; const S = {json.dumps(SLATE)};'
          'const heads = S.map((g, i) => slotHeadBefore(S, i));'
          'currentSort = "confidence"; const other = S.map((g, i) => slotHeadBefore(S, i));'
          'const pills = S.map(cardTvPill);'
          'process.stdout.write(JSON.stringify({heads, other, pills}));')
    r = subprocess.run([NODE, '-e', js], capture_output=True, text=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr[-800:]
    return json.loads(r.stdout)


def test_one_header_per_slot_and_only_where_the_slot_starts(out):
    h = out['heads']
    assert [bool(x) for x in h] == [True, False, True, True], h
    assert 'Sunday, Oct 4 · 1:00 PM ET' in h[0] and '2 games' in h[0]
    assert 'Sunday, Oct 4 · 4:25 PM ET' in h[2] and '1 game<' in h[2]


def test_no_slot_headers_under_another_sort(out):
    assert out['other'] == ['', '', '', '']


def test_a_regional_channel_says_so_on_its_pill(out):
    p = out['pills']
    assert 'CBS' in p[0] and 'regional' in p[0]
    assert 'NBC' in p[3] and 'regional' not in p[3]
