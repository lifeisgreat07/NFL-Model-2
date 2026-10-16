"""One accuracy component for the NHL and the NBA (Stage 79 item 46, the 2026-10-13 UI/UX audit's L5 and B4).

The NHL's Accuracy was a calibration table and the NBA's Checking the AI's
work prose only, where the NFL draws a race, a trend and a calibration
diagram. src/core/accuracy.js draws all three for both, and with nothing
graded each chart says so inside its frame. Its arithmetic runs here under
node; tests/browser/check_accuracy.py draws both pages.

Run with: pytest tests/test_accuracy_component.py -v
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / 'src' / 'core' / 'accuracy.js').read_text(encoding='utf-8')
NODE = shutil.which('node')
GAMES = [  # home won the first two; the market had no price on the third
    {'day': '2026-10-05', 'a': 0.60, 'b': 0.62, 'm': 0.58, 'home': True, 'c': 0.62, 'right': True},
    {'day': '2026-10-05', 'a': 0.45, 'b': 0.55, 'm': 0.52, 'home': True, 'c': 0.55, 'right': True},
    {'day': '2026-10-06', 'a': 0.70, 'b': None, 'm': None, 'home': False, 'c': 0.70, 'right': False},
    {'day': '2026-10-06', 'a': 0.50, 'b': 0.40, 'm': 0.45, 'home': False, 'c': 0.60, 'right': True},
]


def run(expr, games=GAMES):
    if not NODE:
        pytest.skip('node not available')
    code = ('global.window = {matchMedia: () => ({matches: false})};\n' + JS
            + f'\nconst games = {json.dumps(games)};\nconsole.log(JSON.stringify({expr}));')
    r = subprocess.run([NODE, '-e', code], capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_each_forecast_is_scored_on_the_games_it_picked_a_side_in():
    rec = run("['a', 'b', 'm'].map(k => accRecord(games, k))")
    assert rec[0] == {'correct': 1, 'n': 3, 'pct': pytest.approx(100 / 3)}, 'a 50% call picks no side'
    assert rec[1] == {'correct': 3, 'n': 3, 'pct': 100}, 'a forecast with no number is left out, not counted wrong'
    assert rec[2] == {'correct': 3, 'n': 3, 'pct': 100}


def test_the_race_says_who_leads_as_the_nfl_scoreboard_does():
    assert run("accVerdict([{subject: 'Model B', correct: 3, n: 3}, {subject: 'The betting market', correct: 3, n: 3}, {subject: 'Model A', correct: 1, n: 3}])") == \
        'Model B and the betting market are level at the top.'
    assert run("accVerdict([{subject: 'Model B', correct: 0, n: 0}, {subject: 'Model A', correct: 0, n: 0}])") == 'Nothing is graded yet.'
    html = run('accRaceHtml(games)')
    assert html.count('class="score-row"') == 3 and 'Picked the winner &middot; 4 games graded' in html


def test_the_interval_is_wilsons_at_95_percent():
    lo, hi = run('accWilson(7, 10)')
    assert lo == pytest.approx(0.3968, abs=1e-4) and hi == pytest.approx(0.8922, abs=1e-4)
    assert run('accWilson(0, 0)') == [0, 1]


def test_with_nothing_graded_each_chart_says_so_inside_its_frame():
    html = run('accuracyHtml([])', games=[])
    assert html.count('<svg') == 2 and html.count('class="acc-empty chart-title"') == 2
    assert 'Nothing is graded yet.' in html


def test_one_graded_day_is_not_drawn_as_a_trend():
    html = run("accTrendHtml(games.filter(g => g.day === '2026-10-05'))")
    assert 'The trend starts once two days are graded.' in html and '<path d="M' not in html


def test_no_chart_text_is_under_11px():
    # Since Stage 79 item 45 both charts take the one chart style
    # (styles.css, tests/test_chart_style.py), which sets their text at 11
    # and up; neither sets a size of its own.
    html = run('accuracyHtml(games)')
    assert html.count('<svg class="chart" ') == 2 and 'font-size=' not in html


@pytest.mark.parametrize('sport, where', [('nhl', 'function renderAccuracy(){'), ('nba', 'function renderReliability(){')])
def test_each_sport_draws_it_from_its_own_graded_picks(sport, where):
    js = (ROOT / 'src' / 'sports' / sport / 'pages' / f'{sport}.js').read_text(encoding='utf-8')
    assert 'function accGames(graded){' in js and 'function accuracyHtml' not in js, 'the component is shared, not copied'
    body = js[js.index(where):]
    assert 'accuracyHtml(accGames(' in body[:2500]
    page = (ROOT / 'src' / 'sports' / sport / 'pages' / 'page.html').read_text(encoding='utf-8')
    assert '{% include "routes.js" %}\n{% include "accuracy.js" %}\n' in page
    site = (ROOT / 'src' / 'sports' / sport / 'site.py').read_text(encoding='utf-8')
    assert """.replace('{% include "accuracy.js" %}', ACCURACY_JS.read_text(encoding='utf-8'))""" in site


def test_the_browser_check_runs():
    wf = (ROOT / '.github' / 'workflows' / 'browser-checks.yml').read_text(encoding='utf-8')
    assert 'run: python tests/browser/check_accuracy.py --self-test --tmp "$RUNNER_TEMP/accuracy"\n' in wf
    assert 'run: python tests/browser/check_accuracy.py "$RUNNER_TEMP/states/nhl.html" "$RUNNER_TEMP/states/nba.html"\n' in wf
