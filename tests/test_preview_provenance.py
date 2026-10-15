"""A preview week has nothing saved to point at (Stage 77 item 16, the 2026-10-13 UI/UX audit's copy fix 5).

On a phone the Week Board offers "When these picks were saved, and where to
check", which opens the lock note. A preview week has no lock note, so the
button opened nothing; the preview note above it already says the picks
lock before the week's first kickoff. On a preview week the button is now
hidden. renderLockProof runs here under node with stand-in elements.

Run with: pytest tests/test_preview_provenance.py -v
"""
import json
import re
import shutil
import subprocess

import pytest

from src.core.template_parts import JOINED_TEMPLATE

NODE = shutil.which('node')


def shown(week):
    if not NODE:
        pytest.skip('node not available')
    js = JOINED_TEMPLATE.read_text(encoding='utf-8')
    fn = re.search(r'^function renderLockProof\(weekKey, weekData\)\{.*?\n\}\n', js, re.S | re.M)
    assert fn, 'renderLockProof is not findable -- re-anchor this guard'
    code = ("const els = {'board-lock-note': {hidden: true, innerHTML: ''}, 'board-prov-btn': {hidden: false}};\n"
            "global.document = {getElementById: id => els[id]};\n"
            "const lockProof = {weeks: {}}; function lockProofHtml(){ return '<span>Locked Thu 7:00 PM ET</span>'; }\n"
            + fn.group(0) + f'renderLockProof("2026_week6", {json.dumps(week)});\n'
            "console.log(JSON.stringify({button: !els['board-prov-btn'].hidden, note: !els['board-lock-note'].hidden}));")
    r = subprocess.run([NODE, '-e', code], capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_a_preview_week_hides_the_button_with_nothing_behind_it():
    assert shown({'preview': True, 'games': []}) == {'button': False, 'note': False}


def test_a_locked_week_keeps_it():
    assert shown({'games': []}) == {'button': True, 'note': True}
