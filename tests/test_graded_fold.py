"""Season Accuracy's graded picks on the NHL and NBA: the last seven game days shown, the rest folded, every pick as
CSV (audit 9, finding D8).

`gradedListHtml` in src/core/day_board.js is run under node on a made-up season, so what the page draws and what
the CSV holds are checked as data, not as source text.

Run with: pytest tests/test_graded_fold.py -v
"""
import json
import re
import shutil
import subprocess
import urllib.parse
from pathlib import Path

import pytest

from tests.optional import require_tool

ROOT = Path(__file__).resolve().parents[1]
CORE = (ROOT / 'src' / 'core' / 'day_board.js').read_text(encoding='utf-8')
ESCAPE = (ROOT / 'src' / 'core' / 'escape.js').read_text(encoding='utf-8')
BOARDS = {s: (ROOT / 'src' / 'sports' / s / 'pages' / f'{s}.js').read_text(encoding='utf-8') for s in ('nhl', 'nba')}
CSS = (ROOT / 'src' / 'dashboard' / 'styles.css').read_text(encoding='utf-8')
STUBS = ("const FMT_MONTHDAY = {format: d => d.toISOString().slice(5, 10)};\n"
         "function dayDate(day){ return new Date(day + 'T12:00:00Z'); }\n")


def shared():
    start = CORE.index('const GRADED_RECENT_DAYS')
    return CORE[start:CORE.index('\n}\n', CORE.index('function gradedListHtml(')) + 3]


def season(days, per_day=2):
    """Newest first, as the pages sort it."""
    out = []
    for d in range(days, 0, -1):
        for i in range(per_day):
            out.append({'g': {'day': f'2026-11-{d:02d}', 'away': f'A{d}', 'home': f'H{i}'},
                        'p': {'pick': f'A{d}', 'by': 'model_b' if i else 'model_a',
                              'result': 'correct' if (d + i) % 2 else 'wrong'}})
    return out


def draw(picks, sport='nhl'):
    node = require_tool('node')
    code = ESCAPE + STUBS + shared() + f'console.log(gradedListHtml({json.dumps(picks)}, {json.dumps(sport)}));'
    r = subprocess.run([shutil.which('node') or node, '-e', code], capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return r.stdout


def parts(html):
    folded = html.split('<details', 1)
    csv = urllib.parse.unquote(re.search(r'href="data:text/csv;charset=utf-8,([^"]*)"', html).group(1))
    return rows(folded[0]), rows(folded[1]) if len(folded) > 1 else 0, csv


def rows(html):
    return len(re.findall(r'<tr><td>', html))


def test_the_last_seven_game_days_show_and_every_other_pick_is_one_tap_below():
    html = draw(season(10))
    shown, folded, _ = parts(html)
    assert (shown, folded) == (14, 6)
    assert '<summary>Show the other 6 graded picks</summary>' in html
    assert 'The last 7 game days below, 14 of the 20 graded picks; the other 6 are one tap further down.' in html
    assert 'class="disclosure graded-more"' in html


def test_the_csv_holds_every_graded_pick_newest_first():
    _, _, csv = parts(draw(season(10)))
    lines = csv.strip('\n').split('\n')
    assert lines[0] == 'date,away,home,pick,model,result' and len(lines) == 21
    assert lines[1] == '2026-11-10,A10,H0,A10,Model A,Missed' and lines[-1] == '2026-11-01,A1,H1,A1,Model B,Missed'


def test_a_season_of_seven_days_or_fewer_folds_nothing():
    html = draw(season(5))
    assert parts(html)[:2] == (10, 0) and '<details' not in html and 'All 10 graded picks.' in html


def test_a_comma_or_quote_in_a_field_is_quoted_in_the_csv_and_escaped_on_the_page():
    picks = season(1, 1)
    picks[0]['g']['away'] = 'A"B,C'
    html = draw(picks, 'nba')
    assert '"A""B,C"' in parts(html)[2]
    assert 'A&quot;B,C at' in html and 'download="nba-graded-picks.csv"' in html


@pytest.mark.parametrize('sport', ['nhl', 'nba'])
def test_each_season_accuracy_page_draws_its_graded_picks_with_the_shared_function(sport):
    assert f"${{gradedListHtml(list, '{sport}')}}" in BOARDS[sport]
    assert 'function gradedListHtml(' not in BOARDS[sport]


def test_the_fold_is_a_thumb_sized_target():
    assert '.graded-more > summary{display:inline-flex; align-items:center; min-height:44px;' in CSS
