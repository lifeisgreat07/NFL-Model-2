"""Options shows when it is open, and a week without a PDF says so (Stage 77 item 27, the 2026-10-13 UI/UX audit's N2).

On a phone, the Week Board's Options button looked the same open and closed
(border and text colour unchanged after a tap, measured with no hover or
focus), and on a week with no printable PDF the Print / PDF link was simply
hidden, at every width. Options now takes the accent colour and turns its
chevron when open, as the listbox buttons do; a week without a PDF says why
where the link would be. The first part of N2, the provenance link on a
preview week, is Stage 77 item 16 (tests/test_preview_provenance.py).

Run with: pytest tests/test_nfl_options_pdf.py -v
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / 'src' / 'dashboard' / 'app.js').read_text(encoding='utf-8')
BODY = (ROOT / 'src' / 'dashboard' / 'body.html').read_text(encoding='utf-8')
CSS = (ROOT / 'src' / 'dashboard' / 'styles.css').read_text(encoding='utf-8')
NODE = shutil.which('node')


def pdf_none(weeks):
    if not NODE:
        pytest.skip('node not available')
    fn = re.search(r'function pdfNoneText\(weekData\)\{.*?\n\}\n', APP, re.S)
    assert fn, 'pdfNoneText is not findable -- re-anchor this guard'
    r = subprocess.run([NODE, '-e', fn.group(0) + 'console.log(JSON.stringify(%s.map(pdfNoneText)));' % json.dumps(weeks)],
                       capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_a_week_without_a_pdf_says_why():
    assert pdf_none([{'preview': True}, {'preview': False}, None]) == [
        'The printable PDF comes when these picks lock.',
        'No printable PDF for this week.', 'No printable PDF for this week.']


def test_the_sentence_sits_where_the_link_would_and_shows_only_without_it():
    link = BODY.index('id="picks-pdf-link"')
    assert BODY.index('<span id="picks-pdf-none" class="pdf-none" hidden></span>') > link
    board = APP[APP.index("const pdfLink = document.getElementById('picks-pdf-link');"):]
    assert "      pdfNone.hidden = hasPdf;\n      pdfNone.textContent = hasPdf ? '' : pdfNoneText(weekData);" in board[:500]


def test_on_a_phone_the_sentence_sits_behind_options_and_never_prints():
    assert '  #page-board:not(.nfl-options-open) #picks-pdf-none,\n' in CSS
    assert '.pdf-link, .pdf-none, .onboarding-banner' in CSS


def test_options_shows_when_it_is_open():
    assert 'id="board-options-btn" aria-expanded="false">Options<svg class="nfl-options-chev"' in BODY
    assert '#board-options-btn[aria-expanded="true"]{border-color:var(--accent); color:var(--accent);}' in CSS
    assert '#board-options-btn[aria-expanded="true"] .nfl-options-chev{transform:rotate(180deg);' in CSS
    phone = CSS[CSS.index('@media (max-width:640px){\n  .nfl-phone-only'):]
    phone = phone[:phone.index('\n}\n')]
    assert '#board-options-btn{display:inline-flex;' in phone, 'the button shows on a phone only'
