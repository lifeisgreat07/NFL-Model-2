"""
Stage 75 item 6 (the 2026-10-13 UI/UX audit): the "Pick saved / Undo" toast
is a status region, so a screen reader announces it.

Measured 2026-10-13 at 390 and 1440 px in both themes: no toast existed
before a pick, and the one made on the first pick had no role and no
aria-live. A live region added together with its text is not announced
reliably, so the page now carries the toast, empty, with role="status" from
the start; showUndoToast fills it, and its fallback (if the element is ever
missing) sets the same role.

Run with: pytest tests/test_toast_status.py -v
"""
import re
from pathlib import Path

from src.core.template_parts import read_template

REPO = Path(__file__).resolve().parents[1]
APP = (REPO / 'src' / 'dashboard' / 'app.js').read_text(encoding='utf-8')


def test_the_page_carries_the_toast_as_a_status_region_from_the_start():
    page = read_template()
    tags = re.findall(r'<div[^>]*\bid="undo-toast"[^>]*>', page)
    assert len(tags) == 1, tags
    assert 'role="status"' in tags[0] and 'class="undo-toast"' in tags[0]


def test_the_fallback_toast_is_a_status_region_too():
    made = APP[APP.index("toast = document.createElement('div');"):APP.index('document.body.appendChild(toast);')]
    assert "toast.setAttribute('role', 'status');" in made
