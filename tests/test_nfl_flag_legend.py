"""A flagged NFL row carries a flag, explained once (Stage 77 item 28, the 2026-10-13 UI/UX audit's N5).

On a phone, a flagged game's row ended in a blue "●" read as "flagged", with
no legend anywhere, and the same dot means "live" on the home page and the
season in the sidebar. The row now ends in a small flag ("flagged: a note
to read"), and a week with a flagged game says above its rows what the flag
means. The toast half of N5 is Stage 75 item 6 (#442).

Run with: pytest tests/test_nfl_flag_legend.py -v
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


def row(g):
    if not NODE:
        pytest.skip('node not available')
    consts = ''.join(re.search(r'^const %s = .*$' % n, APP, re.M).group(0) + '\n' for n in ('FLAG_ICON', 'FLAG_LEGEND'))
    fns = ''.join(re.search(r'function %s\(.*?\n\}\n' % n, APP, re.S).group(0) for n in ('cardSide', 'phoneRowHtml'))
    js = ("const CARD_EVEN_BAND = 2;\n"
          "function escapeHtml(s){ return String(s ?? ''); }\n" + consts + fns
          + 'console.log(JSON.stringify(phoneRowHtml(%s, "x")));' % json.dumps(g))
    r = subprocess.run([NODE, '-e', js], capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


GAME = {'away': 'SEA', 'home': 'DEN', 'mktB_home': 44, 'fbA_home': 66, 'mkt_home': 37,
        'gametime_et': '20:15', 'gameday': '2026-10-15'}


def test_a_flagged_row_ends_in_a_flag_not_a_dot():
    html = row(dict(GAME, flag='SEA: the pick uses Drew Lock.'))
    assert '<span class="nfl-row-flag" role="img" aria-label="flagged: a note to read"><svg' in html
    assert '&#9679;' not in html and '●' not in html
    assert 'nfl-row-flag' not in row(dict(GAME, flag=''))


def test_a_week_with_a_flag_says_what_it_means_once():
    assert "  if(sorted.some(g => g.flag)) grid.insertAdjacentHTML('afterbegin', FLAG_LEGEND);\n" in APP
    legend = re.search(r'^const FLAG_LEGEND = .*$', APP, re.M).group(0)
    assert '<span class="visually-hidden">A flag</span> marks a game with a note to read before you trust its pick.' in legend


def test_the_legend_shows_on_a_phone_only_like_the_rows():
    assert '.nfl-flag-legend{display:none;}\n.nfl-row, .nfl-phone-only{display:none;}' in CSS
    phone = CSS[CSS.index('@media (max-width:640px){\n  .nfl-phone-only'):]
    phone = phone[:phone.index('\n}\n')]
    assert '.nfl-flag-legend{display:block;' in phone
