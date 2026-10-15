"""On a phone, an active filter says so above the rows (Stage 77 item 31, the 2026-10-13 UI/UX audit's N6).

At 390 px the Week Board's filter chips sit behind Options. With "Model
Disagreement" on and Options closed, 3 of week 6's 14 rows showed and
nothing on screen said a filter was on (measured 2026-10-14, both themes).
An active filter now prints "Filtered: Model Disagreement · clear" above the
rows wherever the chips are hidden, and "clear" puts every game back.

Run with: pytest tests/test_filtered_note.py -v
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / 'src' / 'dashboard' / 'app.js').read_text(encoding='utf-8')
CSS = (ROOT / 'src' / 'dashboard' / 'styles.css').read_text(encoding='utf-8')
NODE = shutil.which('node')


def note(label):
    if not NODE:
        pytest.skip('node not available')
    fn = re.search(r'function filteredNoteHtml\(label\)\{.*?\n\}\n', APP, re.S)
    assert fn, 'filteredNoteHtml is not findable -- re-anchor this guard'
    code = ("function escapeHtml(s){ return String(s).replace(/</g, '&lt;'); }\n" + fn.group(0)
            + 'console.log(JSON.stringify(filteredNoteHtml(%s)));' % json.dumps(label))
    r = subprocess.run([NODE, '-e', code], capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_the_note_names_the_filter_and_offers_to_clear_it():
    assert note('Model Disagreement') == ('<p class="nfl-filtered-note">Filtered: Model Disagreement &middot; '
                                          '<button type="button" class="btn btn-link" data-clear-filter>clear</button></p>')
    assert '&lt;b>' in note('<b>')


def test_it_is_drawn_with_the_rows_only_when_a_filter_is_on_and_clear_shows_all():
    fn = APP[APP.index('function showFilteredNote(grid){'):]
    fn = fn[:fn.index('\n}\n')]
    assert "  if(currentFilter === 'all') return;" in fn
    assert "grid.insertAdjacentHTML('afterbegin', filteredNoteHtml(chip.textContent.trim()));" in fn
    assert "document.querySelector('#filter-row .filter-btn[data-filter=all]');\n    if(all) all.click();" in fn
    assert "  showFilteredNote(grid);\n" in APP


def test_it_shows_only_where_the_chips_are_hidden():
    assert '.nfl-filtered-note{display:none;}\n' in CSS
    phone = CSS[CSS.index('@media (max-width:640px){\n  .nfl-phone-only'):]
    phone = phone[:phone.index('\n}\n')]
    assert '  #page-board:not(.nfl-options-open) .nfl-filtered-note{display:block;' in phone
