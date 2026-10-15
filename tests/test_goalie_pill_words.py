"""A goalie's name and status are two words to a screen reader (Stage 77 item 34, the 2026-10-13 UI/UX audit's L7).

The NHL card's goalie line read "NJD Jake AllenConfirmed" as text, so a
screen reader ran the name into the status pill (measured 2026-10-14). A
visually hidden ", " now sits between them; the pill's own margin is still
the gap on screen, so the card looks the same (before and after shots are
pixel-identical at 390 px).

Run with: pytest tests/test_goalie_pill_words.py -v
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


def text(gl):
    if not NODE:
        pytest.skip('node not available')
    fn = re.search(r'function goalieText\(team, gl\)\{.*?\n\}\n', JS, re.S)
    assert fn, 'goalieText is not findable -- re-anchor this guard'
    code = ("function escapeHtml(s){ return String(s); }\n" + fn.group(0)
            + 'const h = goalieText("NJD", %s); console.log(JSON.stringify([h, h.replace(/<[^>]+>/g, "")]));' % json.dumps(gl))
    r = subprocess.run([NODE, '-e', code], capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


@pytest.mark.parametrize('gl, spoken', [
    ({'name': 'Jake Allen', 'basis': 'projected', 'status': 'Confirmed'}, 'NJD Jake Allen, Confirmed'),
    ({'name': 'Jake Allen', 'basis': 'projected', 'status': 'Likely'}, 'NJD Jake Allen, Likely'),
    ({'name': 'Jake Allen', 'basis': 'projected', 'status': None}, 'NJD Jake Allen, No report yet'),
    ({'name': 'Jake Allen', 'basis': 'last_start'}, 'NJD Jake Allen, Last start'),
])
def test_the_name_and_the_status_are_separate_words(gl, spoken):
    html, said = text(gl)
    assert said == spoken
    assert '</b><span class="visually-hidden">, </span><span class="tag ' in html
