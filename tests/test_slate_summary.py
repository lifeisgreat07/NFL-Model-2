"""A graded slate says how each forecast did (Stage 80 item 59, the 2026-10-13 UI/UX audit's F16).

Before, a graded NFL week or NHL day showed its cards and nothing that
summed them up; the totals were only on Season Accuracy. Its top now reads
"Model B 10–4 · Model A 12–2 · Market 9–5 · 1 tie" (the NFL's Week 5, which
matched the Season Accuracy table week by week when measured on 2026-10-14),
and while the slate is being played, how many of its games are in. A tie
counts for no one and is named; a cancelled game is not waited for. The NHL
and NBA draw theirs from src/core/accuracy.js, as their accuracy pages do.

Run with: pytest tests/test_slate_summary.py -v
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / 'src' / 'dashboard' / 'app.js').read_text(encoding='utf-8')
ACC = (ROOT / 'src' / 'core' / 'accuracy.js').read_text(encoding='utf-8')
GEN = (ROOT / 'src' / 'sports' / 'nfl' / 'generate_dashboard.py').read_text(encoding='utf-8')
NODE = shutil.which('node')


def fn(src, name):
    m = re.search(r'function %s\(.*?\n\}\n' % name, src, re.S)
    assert m, f'{name} is not findable -- re-anchor this guard'
    return m.group(0)


def node(code):
    if not NODE:
        pytest.skip('node not available')
    r = subprocess.run([NODE, '-e', code], capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def g(b, a, m, graded=True, result=None, status='final'):
    return {'graded': graded, 'result': result, 'status': status,
            'model_b_correct': b, 'model_a_correct': a, 'market_correct': m}


def nfl(games):
    return node(fn(APP, 'slateSummaryHtml') + f'console.log(JSON.stringify({json.dumps(games)}.map(slateSummaryHtml)));')


def text(html):
    return re.sub(r'<[^>]+>', '', html)


def test_a_graded_week_reads_each_forecasts_record_and_names_a_tie():
    week = [g(1, 1, 1), g(1, 0, 0), g(0, 1, 1), g(None, None, None, result='tie')]
    assert text(nfl([week])[0]) == 'Model B 2–1 · Model A 2–1 · Market 2–1 · 1 tie'


def test_a_week_in_play_says_how_much_is_in_and_a_cancelled_game_is_not_waited_for():
    part = [g(1, 1, 0), g(None, None, None, graded=False, status='scheduled'), g(None, None, None, graded=False, status='cancelled')]
    none = [g(None, None, None, graded=False, status='scheduled')]
    a, b = nfl([part, none])
    assert text(a) == 'Model B 1–0 · Model A 1–0 · Market 0–1 1 of 2 graded'
    assert b == '', 'nothing graded, no strip'


def test_the_week_board_draws_it_with_the_markets_grade_as_grading_wrote_it():
    assert "if(el) el.innerHTML = slateSummaryHtml(gamesList);" in fn(APP, 'renderWeekGlance')
    assert "'market_correct': graded.get('market_correct') if graded else None," in GEN


def test_a_graded_day_on_the_nhl_and_nba_reads_the_same():
    games = json.dumps([{'a': 0.6, 'b': 0.55, 'm': 0.52, 'home': True}, {'a': 0.4, 'b': 0.6, 'm': 0.45, 'home': False},
                        {'a': 0.7, 'b': 0.45, 'm': 0.5, 'home': False}])
    code = ACC[ACC.index('const ACC_SERIES'):ACC.index('/* The NFL scoreboard')] + fn(ACC, 'accSummaryHtml')
    got = node(code + f'console.log(JSON.stringify([accSummaryHtml({games}, 3), accSummaryHtml({games}, 5), accSummaryHtml([], 4)]));')
    assert text(got[0]) == 'Model B 2–1 · Model A 2–1 · Market 2–0', 'a pick of exactly 50% picks no side'
    assert text(got[1]).endswith(' 3 of 5 graded') and got[2] == ''
    for sport, picks in (('nhl', 'DATA.picks'), ('nba', 'BD.picks')):
        js = (ROOT / 'src' / 'sports' / sport / 'pages' / f'{sport}.js').read_text(encoding='utf-8')
        assert f"const gradedToday = dayGames.map(g => ({{p: {picks}[g.id], g}})).filter(x => x.p && (x.p.result === 'correct' || x.p.result === 'wrong'));" in js
        assert 'accSummaryHtml(accGames(gradedToday), dayGames.length)' in js
