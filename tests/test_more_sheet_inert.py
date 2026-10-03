"""The closed More sheet takes no focus and is hidden from assistive technology.

Stage 11 (CLAUDE.md, "Stage 11 - Integrity and access"). The phone's More
sheet is always in the page; closed, it is only moved below the screen with a
transform. Its five buttons stayed in the Tab order, so on a 1440x900 desktop
-- where the sheet never opens at all -- the 19th Tab press focused "Team
Deep-Dive" at top 917, off the bottom of the screen
(docs/design/UX-REVIEW-2026-09-26.md). A keyboard user saw focus vanish for
five presses.

The fix is `inert` while closed. Two things have to hold for it to stay
fixed: the markup starts inert (so the first frame, and a page without
JavaScript, are right), and exactly one function opens and closes the sheet,
setting the class and the attribute together. The second is executed here
with a stub element rather than read, because "sets inert to the opposite
of open" is exactly the line a sign flip breaks.

Run with: pytest tests/test_more_sheet_inert.py -v
"""
import json
import re
import shutil
import subprocess

import pytest

from src.pipeline.template_parts import JOINED_TEMPLATE  # noqa: E402

TEMPLATE = JOINED_TEMPLATE
NODE = shutil.which('node')


@pytest.fixture(scope='module')
def source():
    return TEMPLATE.read_text(encoding='utf-8')


def _code(src):
    src = re.sub(r'/\*.*?\*/', '', src, flags=re.S)
    return re.sub(r'(?m)^\s*//.*$', '', src)


def test_the_sheet_starts_inert_in_the_markup(source):
    tags = re.findall(r'<div\b[^>]*\bid="bnav-more-sheet"[^>]*>', source)
    assert len(tags) == 1, f'expected one More sheet element, found {len(tags)}'
    assert re.search(r'\sinert(\s|>|=)', tags[0]), (
        f'the More sheet is not inert until opened: {tags[0]}')


def test_only_one_function_opens_or_closes_the_sheet(source):
    """Any other path that toggles `open` would leave `inert` behind."""
    code = _code(source)
    m = re.search(r'function setMoreSheetOpen\(open\)\{.*?\n\}', code, re.S)
    assert m, 'setMoreSheetOpen is gone -- re-anchor this guard'
    outside = code.replace(m.group(0), '')
    # Other components (the why-panel, the context note) have their own
    # 'open' class, so the match is on the sheet: by id, or through the
    # `sheet` name every sheet handler here binds it to.
    stray = re.findall(
        r"getElementById\(\s*'bnav-more-sheet'\s*\)\s*\.classList\.(?:toggle|add|remove)"
        r"|\bsheet\.classList\.(?:toggle|add|remove)\(", outside)
    assert not stray, (
        f"{len(stray)} place(s) outside setMoreSheetOpen open or close the More "
        f"sheet without updating inert: {stray}")
    # Vacuity: the guard must be looking at the handlers that DO exist.
    assert "getElementById('bnav-more-sheet')" in outside, (
        'no sheet handler found outside setMoreSheetOpen -- this guard is '
        'searching nothing')


@pytest.fixture(scope='module')
def executed(source):
    if not NODE:
        pytest.skip('node not available')
    m = re.search(r'function setMoreSheetOpen\(open\)\{.*?\n\}', source, re.S)
    assert m, 'setMoreSheetOpen is gone -- re-anchor this guard'
    js = """
const cls = new Set(); const sheet = {inert: true, classList: {
  toggle(c, on){ if(on) cls.add(c); else cls.delete(c); }, contains(c){ return cls.has(c); }}};
const document = {getElementById: id => id === 'bnav-more-sheet' ? sheet : null};
""" + m.group(0) + """
const out = {};
setMoreSheetOpen(true);  out.opened = {inert: sheet.inert, open: cls.has('open')};
setMoreSheetOpen(false); out.closed = {inert: sheet.inert, open: cls.has('open')};
process.stdout.write(JSON.stringify(out));
"""
    r = subprocess.run([NODE, '-e', js], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_opening_the_sheet_makes_it_reachable(executed):
    assert executed['opened'] == {'inert': False, 'open': True}


def test_closing_the_sheet_makes_it_inert_again(executed):
    assert executed['closed'] == {'inert': True, 'open': False}
