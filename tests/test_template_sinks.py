"""Text reaching innerHTML goes through escapeHtml() (Stage 23 item 4).

The 2026-09-28 audit found two places the template put a string into
innerHTML as written: the Power Ratings "No teams match" row, which echoes
whatever the reader typed into the search, and the card's context notes,
which come from sourced web reports saved with a pick. Neither note text
nor search text is markup, so both are escaped, and each is a small
function run here in node rather than read.

The source check below guards the call sites: a render that goes back to
building either string inline would bypass the helper and still pass the
node tests.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from src.pipeline.template_parts import JOINED_TEMPLATE

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = JOINED_TEMPLATE
NODE = shutil.which('node')
PAYLOAD = '<img src=x onerror=alert(1)>"&'


def src():
    return TEMPLATE.read_text(encoding='utf-8').replace('\r\n', '\n')


def fn(s, name):
    m = re.search(r'function ' + name + r'\(.*?\n\}\n', s, re.S)
    assert m, f'{name} is not findable -- re-anchor this guard'
    return m.group(0)


def run(expr):
    if not NODE:
        pytest.skip('node not available')
    s = src()
    js = ''.join(fn(s, f) for f in ('escapeHtml', 'ratingsNoMatchRow', 'contextNotesHtml'))
    r = subprocess.run([NODE, '-e', js + f'\nprocess.stdout.write(JSON.stringify({expr}));'],
                       capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_the_search_text_is_escaped_in_the_no_match_row():
    html = run(f'ratingsNoMatchRow({json.dumps(PAYLOAD)})')
    assert '<img' not in html, f'the typed text became markup: {html}'
    assert 'No teams match "&lt;img src=x onerror=alert(1)&gt;&quot;&amp;"' in html


def test_context_notes_are_escaped_one_item_each():
    html = run(f'contextNotesHtml({json.dumps([PAYLOAD, "Rush starts"])})')
    assert '<img' not in html, f'a note became markup: {html}'
    assert html.count('<li ') == 2, 'one list item per note'
    assert '&lt;img src=x onerror=alert(1)&gt;&quot;&amp;</li>' in html
    assert '>Rush starts</li>' in html, 'plain text reads the same after escaping'


def test_the_render_sites_use_the_helpers():
    s = src()
    assert 'body.innerHTML = ratingsNoMatchRow(q);' in s, (
        'Power Ratings builds its no-match row inline again')
    assert '${contextNotesHtml(g.notes)}' in s, (
        'the card builds its context notes inline again')
    assert 'No teams match "${q}"' not in s and '${n}</li>' not in s, (
        'an unescaped copy of either string is back in the template')
