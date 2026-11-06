"""Stage 84 item 5: the forward test reports the calibration intercept and
slope of Models A and B, with day-block intervals, and the checks pages show
them as the file has them.

The intercept is logit P(home win) = a + logit(p), the slope held at 1
(calibration in the large); the slope is logit P(home win) = a + b logit(p).
Perfect calibration is intercept 0 and slope 1. Reported, not judged.

Run with: pytest tests/test_forward_calibration.py -v
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.core import forward_test as ft
from tests.optional import in_ci
from tests.page_script import day_script

ROOT = Path(__file__).resolve().parents[1]
PAGES = {'nhl': ROOT / 'src' / 'sports' / 'nhl' / 'pages' / 'nhl.js',
         'nba': ROOT / 'src' / 'sports' / 'nba' / 'pages' / 'nba.js'}
NODE = shutil.which('node')


def synthetic(n=4000, a=0.3, b=0.7, seed=1):
    """Forecasts p, and outcomes drawn so the true intercept/slope are known."""
    rng = np.random.default_rng(seed)
    p = rng.uniform(0.15, 0.85, n)
    x = np.log(p / (1 - p))
    y = (rng.uniform(size=n) < 1 / (1 + np.exp(-(a + b * x)))).astype(float)
    return p, x, y


# --- the fit ----------------------------------------------------------------------------------

def test_the_slope_fit_recovers_a_known_intercept_and_slope():
    _, x, y = synthetic()
    a, b = ft.recalibrate(x, y, np.ones((1, len(x))), slope_free=True)
    assert a[0] == pytest.approx(0.3, abs=0.12) and b[0] == pytest.approx(0.7, abs=0.12)


def test_each_fit_solves_its_own_score_equations():
    """At the maximum, the weighted residuals sum to zero (and, for the slope,
    so do the residuals times the log-odds): the fit is the MLE, not near it."""
    _, x, y = synthetic(n=500)
    one = np.ones((1, len(x)))
    a, b = ft.recalibrate(x, y, one, slope_free=True)
    r = y - 1 / (1 + np.exp(-(a[0] + b[0] * x)))
    assert abs(r.sum()) < 1e-8 and abs((r * x).sum()) < 1e-8
    a, b = ft.recalibrate(x, y, one, slope_free=False)
    assert b[0] == 1.0, 'the intercept fit holds the slope at 1'
    assert abs((y - 1 / (1 + np.exp(-(a[0] + x)))).sum()) < 1e-8


def test_a_weighted_row_is_the_fit_on_those_games_repeated():
    """The bootstrap weights a game by how often its day was drawn; that must
    be the same fit as repeating the game that many times."""
    _, x, y = synthetic(n=60)
    w = np.random.default_rng(3).integers(0, 4, 60).astype(float)
    reps = w.astype(int)
    for free in (False, True):
        got = ft.recalibrate(x, y, w[None, :], free)
        want = ft.recalibrate(np.repeat(x, reps), np.repeat(y, reps), np.ones((1, reps.sum())), free)
        assert got[0][0] == pytest.approx(want[0][0], abs=1e-9) and got[1][0] == pytest.approx(want[1][0], abs=1e-9)


# --- the interval -----------------------------------------------------------------------------

def test_the_interval_resamples_days_at_the_backtests_level_and_contains_the_fit():
    p, _, y = synthetic(n=300)
    days = np.repeat(pd.date_range('2026-10-10', periods=30), 10)
    # 1,000 draws rather than the registered 5,000, to keep this test quick;
    # the daily run's file uses N_RESAMPLES (test_the_report_... below).
    out = ft.calibration(p, y, days, ft.SEEDS['nhl'], n=1000)
    assert out['games'] == 300 and out['days'] == 30 and out['level'] == ft.LEVEL
    for k in ('intercept', 'slope'):
        c = out[k]
        assert c['low'] <= c['value'] <= c['high'] and c['draws_unfit'] == 0, k
    assert out == ft.calibration(p, y, days, ft.SEEDS['nhl'], n=1000), 'the seed is fixed'
    assert ft.calibration.__defaults__ == (ft.LEVEL, ft.N_RESAMPLES), 'the report uses the registered level and count'


def test_forecasts_that_never_vary_have_an_intercept_and_no_slope():
    y = np.array([1, 0, 1, 1, 0, 1], float)
    out = ft.calibration(np.full(6, 0.6), y, np.repeat(['2026-10-10', '2026-10-11', '2026-10-12'], 2), 1)
    assert out['intercept']['value'] is not None
    assert out['slope'] == {'value': None, 'low': None, 'high': None, 'draws_unfit': out['slope']['draws_unfit'],
                            'note': 'no finite fit'}


def test_the_report_calibrates_a_and_b_on_the_games_each_has():
    rng = np.random.default_rng(5)
    picks, fin = [], []
    for i in range(60):
        priced = i % 3 != 0
        picks.append({'game_id': str(i), 'model_a': float(rng.uniform(0.3, 0.7)),
                      'model_b': float(rng.uniform(0.3, 0.7)) if priced else None})
        fin.append((str(i), f'2026-10-{10 + i // 4}', float(rng.uniform() < 0.55)))
    frame = ft.rows(picks, pd.DataFrame(fin, columns=['game_id', 'slate', 'home_win']), {})
    out = ft.report(frame, 'nba', 2026, 'r')
    assert set(out['calibration']) == set(ft.CALIBRATED) == {'model_a', 'model_b'}
    assert out['calibration']['model_a']['games'] == 60 and out['calibration']['model_b']['games'] == 40
    assert not re.search(r'ACCEPT|REJECT|INCONCLUSIVE|verdict', json.dumps(out['calibration']))


# --- the pages --------------------------------------------------------------------------------

def functions(sport):
    js = day_script(sport).replace('\r\n', '\n')
    out = []
    for name in ('forwardHtml', 'calibrationTable'):
        m = re.search(rf'function {name}\(f, sport(, level)?\)\{{.*?\n\}}\n', js, re.S)
        assert m, f'{name} is not findable in {sport}.js -- re-anchor this guard'
        out.append(m.group(0))
    return ''.join(out)


def render(sport, f):
    prog = functions(sport) + f'process.stdout.write(forwardHtml({json.dumps(f)}, {json.dumps(sport)}));'
    return subprocess.run([NODE, '-e', prog], capture_output=True, text=True, check=True, encoding='utf-8').stdout


def a_file():
    rng = np.random.default_rng(9)
    picks, fin = [], []
    for i in range(48):
        picks.append({'game_id': str(i), 'model_a': float(rng.uniform(0.3, 0.7)), 'model_b': float(rng.uniform(0.3, 0.7)),
                      'market': {'home_prob': float(rng.uniform(0.3, 0.7))}, 'market_source': 'espn'})
        fin.append((str(i), f'2026-10-{10 + i // 4}', float(rng.uniform() < 0.55)))
    frame = ft.rows(picks, pd.DataFrame(fin, columns=['game_id', 'slate', 'home_win']),
                    {f'2026-10-{10 + d}': 0.55 for d in range(12)})
    return json.loads(json.dumps(ft.report(frame, 'nba', 2026, 'experiments/nba/stage65/registry.json')))


def fx(x):
    return ('&minus;' if x < 0 else '') + f'{abs(x):.2f}'


def test_both_pages_carry_the_same_calibration_table():
    assert functions('nhl') == functions('nba')


@pytest.mark.skipif(NODE is None and not in_ci(), reason='node not installed')
@pytest.mark.parametrize('sport', ['nhl', 'nba'])
def test_every_calibration_figure_in_the_file_is_on_the_page(sport):
    f = a_file()
    html = render(sport, f)
    for name, label in (('model_a', 'Model A'), ('model_b', 'Model B')):
        c = f['calibration'][name]
        cells = (f'<tr><th scope="row">{label}</th><td class="num">{c["games"]}</td>'
                 + ''.join(f'<td class="num">{fx(c[k]["value"])}</td><td class="num">[{fx(c[k]["low"])}, {fx(c[k]["high"])}]</td>'
                           for k in ('intercept', 'slope')) + '</tr>')
        assert cells in html, f'{name}: {cells}'
    assert 'intercept of 0 and a slope of 1' in html and 'reported, not judged' in html


@pytest.mark.skipif(NODE is None and not in_ci(), reason='node not installed')
def test_a_file_without_calibration_shows_no_table_and_a_missing_fit_says_so():
    f = a_file()
    old = {k: v for k, v in f.items() if k != 'calibration'}
    assert 'Calibration' not in render('nba', old), 'a file written before Stage 84 item 5 has no calibration block'
    f['calibration']['model_b']['slope'] = {'value': None, 'low': None, 'high': None, 'draws_unfit': 5000,
                                            'note': 'no finite fit'}
    assert '<td colspan="2">no finite fit</td>' in render('nba', f)
