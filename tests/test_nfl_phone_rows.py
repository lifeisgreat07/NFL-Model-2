"""The NFL's Week Board on a phone: compact rows (Stage 68 item 36, option N2, Mark 2026-10-10).

Run with: pytest tests/test_nfl_phone_rows.py -v
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / 'src' / 'dashboard' / 'app.js').read_text(encoding='utf-8')
CSS = (ROOT / 'src' / 'dashboard' / 'styles.css').read_text(encoding='utf-8').replace('\r\n', '\n')
BODY = (ROOT / 'src' / 'dashboard' / 'body.html').read_text(encoding='utf-8')
NODE = shutil.which('node')


def fn(name):
    m = re.search(r'^function ' + name + r'\(.*?\n\}\n', APP, re.S | re.M)
    assert m, name
    return m.group(0)


def test_every_card_has_its_row_and_the_row_opens_it():
    assert 'slotHeadBefore(sorted, i) + phoneRowHtml(sorted[i], i) + card' in APP
    assert "card.id = `card-${i}`; card.classList.add('nfl-collapsible');" in APP
    assert "classList.toggle('is-open', open)" in APP


def test_rows_and_buttons_are_for_phones_only():
    assert '.nfl-row, .nfl-phone-only{display:none;}\n@media (max-width:640px){' in CSS
    phone = CSS[CSS.index('@media (max-width:640px){\n  .nfl-phone-only'):]
    assert '#game-grid .game-card.nfl-collapsible{display:none;' in phone
    assert '#game-grid .game-card.nfl-collapsible.is-open{display:block;}' in phone
    for btn in ('board-options-btn', 'board-prov-btn'):
        assert f'id="{btn}" aria-expanded="false"' in BODY


def row(g):
    if not NODE:
        pytest.skip('node not available')
    js = ("const CARD_EVEN_BAND = 2;\n"
          "function escapeHtml(s){ return String(s ?? '').replace(/[&<>\"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',\"'\":'&#39;'}[c])); }\n"
          + fn('cardSide') + fn('phoneRowHtml') + f'console.log(phoneRowHtml({json.dumps(g)}, "x"));')
    r = subprocess.run([NODE, '-e', js], capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return r.stdout


def test_a_row_says_the_time_the_game_the_pick_and_the_result():
    g = {'home': 'KC', 'away': 'BUF', 'gametime_et': '20:15', 'mktB_home': 61.2, 'fbA_home': 55, 'graded': True,
         'model_b_correct': False}
    out = row(g)
    assert '8:15 PM' in out and 'BUF @ KC' in out
    assert 'KC 61%' in out and 'incorrect">Wrong<' in out
    assert 'final">Final<' in row(dict(g, graded=False, status='final')), 'an ungraded final: Final, no verdict'
    assert 'Toss-up' in row(dict(g, mktB_home=50.5, graded=False)) and '">Wrong' not in row(dict(g, graded=False))
