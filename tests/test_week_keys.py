"""[ and ] step weeks on the Week Board and My Picks (Stage 17).

CLAUDE.md's Stage 17 plan: "`[` and `]` step weeks on desktop." The key
presses the page's own stepper button, so it takes the click's path and stops
at either end where that button is disabled. weekKeyTarget() is run in node
with plain event objects; the wiring is read from the template.

Run with: pytest tests/test_week_keys.py -v
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from src.pipeline.template_parts import JOINED_TEMPLATE  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = JOINED_TEMPLATE
NODE = shutil.which('node')


def src():
    return TEMPLATE.read_text(encoding='utf-8').replace('\r\n', '\n')


def target(key, page='board', inside=None, **mods):
    """weekKeyTarget() for one key press. `inside` is the selector the
    focused element sits in, or None for the page body."""
    if not NODE:
        pytest.skip('node not available')
    fn = re.search(r'function weekKeyTarget\(.*?\n\}\n', src(), re.S)
    assert fn, 'weekKeyTarget is not findable -- re-anchor this guard'
    ev = dict({'key': key, 'ctrlKey': False, 'metaKey': False, 'altKey': False,
               'defaultPrevented': False}, **mods)
    js = fn.group(0) + f"""
const inside = {json.dumps(inside)};
const e = Object.assign({json.dumps(ev)}, {{target: {{closest: sel =>
  inside && sel.split(',').map(s => s.trim()).includes(inside) ? {{}} : null}}}});
process.stdout.write(JSON.stringify(weekKeyTarget(e, {json.dumps(page)})));"""
    r = subprocess.run([NODE, '-e', js], capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_open_bracket_goes_back_and_close_bracket_goes_on():
    assert target('[') == 'week-prev'
    assert target(']') == 'week-next'
    assert target('a') is None and target('ArrowLeft') is None


def test_both_steppers_answer_and_no_other_page_does():
    assert target('[', 'picks') == 'picks-week-prev'
    assert target(']', 'picks') == 'picks-week-next'
    assert target('[', 'ratings') is None and target(']', None) is None


def test_modified_keys_are_left_to_the_browser():
    for mod in ('ctrlKey', 'metaKey', 'altKey'):
        assert target('[', **{mod: True}) is None, mod
    assert target(']', defaultPrevented=True) is None


def test_keys_typed_into_a_control_do_nothing():
    """The sort list's type-ahead reads every character, and a field is a
    field: neither may lose a keystroke to the week."""
    for where in ('input', 'textarea', 'select', '[role="listbox"]', '[contenteditable="true"]'):
        assert target('[', inside=where) is None, where


def test_the_key_presses_the_steppers_own_button():
    body = re.search(r"document\.addEventListener\('keydown', e => \{.*?\n\}\);", src(), re.S)
    assert body, 'the key listener is not findable -- re-anchor this guard'
    assert 'weekKeyTarget(e,' in body.group(0) and 'btn.click();' in body.group(0)


def test_the_buttons_announce_their_keys():
    s = src()
    for prefix in ('week', 'picks-week'):
        assert f'id="{prefix}-prev" aria-label="Previous week" aria-keyshortcuts="["' in s, prefix
        assert f'id="{prefix}-next" aria-label="Next week" aria-keyshortcuts="]"' in s, prefix
