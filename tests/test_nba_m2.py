"""Stage 84 item 4: Stage 61's M2 on the live season, the injury report
against who played.

experiments/nba/stage61/registry.json: "Over the forward test's graded games:
how far the availability read from the injury report was from the box
score's, and Model A's log loss with each", printed on the checking page once
100 games are graded. src/sports/nba/m2.py rebuilds each pick's injury-report
availability from the players it stored, takes the box score's from the
backtest's availability_table, and scores Model A, refitted as the pick
records, with each. Held here with the ratings and the model stubbed.

Run with: pytest tests/test_nba_m2.py -v
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.sports.nba import m2

ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which('node')
COLS = ['point_matchup', 'efficiency_matchup', 'availability_matchup']


class Rated:
    def matchup(self, home, away):
        return {'point_matchup': 0.0, 'efficiency_matchup': 0.0}


class Model:
    """P(home win) = sigmoid(availability_matchup * 4)."""
    def predict_proba(self, x):
        p = 1 / (1 + np.exp(-4 * x['availability_matchup'].to_numpy()))
        return np.column_stack([1 - p, p])


@pytest.fixture
def seen(monkeypatch):
    calls = {'fit': [], 'rate': [], 'report': []}
    monkeypatch.setattr(m2.ratings, 'day_ratings', lambda train, day, h, lam: calls['rate'].append((train, day)) or Rated())
    return calls


def fit(calls):
    def f(table):
        calls['fit'].append(table)
        return {'a': Model()}
    return f


def report_availability(calls):
    """Each side's availability: 1.0 less 0.25 per player listed out."""
    def f(minutes, day_of, team, day, h, out):
        calls['report'].append((team, set(out)))
        return 1.0 - 0.25 * len(out)
    return f


def player(pid, status):
    return {'athlete_id': pid, 'name': pid, 'status': status}


def pick(gid, slate, home_out=(), away_out=(), read=True, through='2026-10-30', model_a=None):
    return {'game_id': gid, 'slate': slate, 'home': 'ORL', 'away': 'ATL', 'training_through': through,
            'availability': {'read': True} if read else {'read': False, 'note': 'x'}, 'model_a': model_a,
            'injuries': {'home': [player(p, s) for p, s in home_out], 'away': [player(p, s) for p, s in away_out]}}


GAMES = pd.DataFrame({'game_id': ['1', '2', '3', '4'], 'day': pd.to_datetime(['2026-10-31'] * 2 + ['2026-11-01'] * 2),
                      'home_win': [1, 0, 1, 0]})
TABLE = pd.DataFrame({'day': ['2026-10-29', '2026-10-30', '2026-10-31'], 'home_prob': [0.5] * 3})
BOX = pd.Series({'1': 0.0, '2': -0.5, '3': 0.25, '4': 0.0})


def run(picks, calls):
    return m2.measure(picks, GAMES, None, TABLE, BOX, 120.0, 10.0, COLS, fit(calls), report_availability(calls))


def test_each_game_is_scored_with_the_reports_availability_and_the_box_scores(seen):
    out = run([pick('1', '2026-10-31', home_out=[('a', 'Out')]), pick('2', '2026-10-31')], seen)
    # Game 1: report 0.75 - 1.0 = -0.25, box 0.0. Game 2: report 0.0, box -0.5.
    sig = lambda z: 1 / (1 + np.exp(-4 * z))
    want_rep = np.mean([-np.log(sig(-0.25)), -np.log(1 - sig(0.0))])
    want_box = np.mean([-np.log(sig(0.0)), -np.log(1 - sig(-0.5))])
    assert out['model_a']['log_loss_report'] == pytest.approx(want_rep)
    assert out['model_a']['log_loss_box'] == pytest.approx(want_box)
    a = out['availability']
    assert a['mean_report_minus_box'] == pytest.approx(np.mean([-0.25, 0.5]))
    assert a['mean_absolute_gap'] == pytest.approx(np.mean([0.25, 0.5]))


def test_only_out_and_suspended_players_count_against_the_report(seen):
    run([pick('1', '2026-10-31', home_out=[('a', 'Out'), ('b', 'Day-To-Day'), ('c', 'Suspension')])], seen)
    assert seen['report'][0] == ('ORL', {'a', 'c'}) and seen['report'][1] == ('ATL', set())


def test_picks_made_without_availability_are_counted_and_left_out(seen):
    out = run([pick('1', '2026-10-31'), pick('2', '2026-10-31', read=False), pick('9', '2026-10-31')], seen)
    assert out['graded'] == 1 and out['graded_without_availability'] == 1, 'game 9 is not final: neither'


def test_the_refit_is_the_picks_own_cutoff_and_ratings_are_before_the_slate(seen):
    run([pick('3', '2026-11-01', through='2026-10-29')], seen)
    ((table,),) = [(t,) for t in seen['fit']]
    assert str(pd.to_datetime(table['day']).max().date()) == '2026-10-29'
    ((train, day),) = seen['rate']
    assert day == pd.Timestamp('2026-11-01') and train['day'].max() == pd.Timestamp('2026-10-31')


def test_the_refit_is_checked_against_the_saved_probability(seen):
    p_rep = round(float(1 / (1 + np.exp(1.0))), 4)   # report matchup -0.25
    out = run([pick('1', '2026-10-31', home_out=[('a', 'Out')], model_a=p_rep), pick('2', '2026-10-31', model_a=0.9)], seen)
    assert out['refit'] == {'reproduced_saved_model_a': 1, 'of': 2}


def test_the_difference_has_a_day_block_interval_and_no_verdict(seen):
    out = run([pick(str(i), d) for i, d in (('1', '2026-10-31'), ('2', '2026-10-31'), ('3', '2026-11-01'), ('4', '2026-11-01'))], seen)
    d = out['model_a']['box_minus_report']
    assert d['games'] == 4 and d['days'] == 2 and d['low'] <= d['diff'] <= d['high']
    assert out['judged'] is False and not re.search(r'ACCEPT|REJECT|INCONCLUSIVE', json.dumps(out))


# --- the registration, the run and the page ---------------------------------------------------

def test_it_measures_what_the_registration_names():
    reg = json.loads((ROOT / 'experiments' / 'nba' / 'stage61' / 'registry.json').read_text(encoding='utf-8'))
    found = []

    def walk(o):
        if isinstance(o, dict):
            if o.get('id') == 'M2':
                found.append(o)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(reg)
    (spec,) = found
    assert "how far the availability read from the injury report was from the box score's" in spec['question']
    assert "Model A's log loss with each" in spec['question'] and spec['spends_slot'] is False
    assert 'once 100 games are graded' in spec['consequence'] and m2.MIN_GAMES == 100


def test_the_daily_run_writes_it_every_run_from_the_backtests_table():
    src = (ROOT / 'src' / 'sports' / 'nba' / 'daily.py').read_text(encoding='utf-8')
    main = src[src.index('def main('):]
    assert main.index('avail_table = ratings.availability_table(games, minutes, h)') < main.index('if decision.lock:')
    assert "m2.write(PATHS.results / f'm2_{season}.json', picks=forward_test.read_picks(folder), games=games," in main
    assert 'box=avail_table' in main and 'report_availability=availability_for' in main
    wf = (ROOT / '.github' / 'workflows' / 'nba-daily.yml').read_text(encoding='utf-8')
    assert 'test -d results/nba && git add results/nba' in wf
    site = (ROOT / 'src' / 'sports' / 'nba' / 'site.py').read_text(encoding='utf-8')
    assert "'m2': _maybe(PATHS.results / f'm2_{season}.json')," in site


def page():
    js = (ROOT / 'src' / 'sports' / 'nba' / 'pages' / 'nba.js').read_text(encoding='utf-8').replace('\r\n', '\n')
    return re.search(r'function m2Html\(m\)\{.*?\n\}\n', js, re.S).group(0), js


def render(m):
    fn, _ = page()
    return subprocess.run([NODE, '-e', fn + f'process.stdout.write(m2Html({json.dumps(m)}));'],
                          capture_output=True, text=True, check=True, encoding='utf-8').stdout


A_FILE = {'measurement': 'M2', 'registered': 'experiments/nba/stage61/registry.json', 'graded': 120,
          'graded_without_availability': 15, 'printed_from': 100, 'judged': False,
          'availability': {'mean_report_minus_box': -0.0086, 'mean_absolute_gap': 0.1637, 'median_absolute_gap': 0.1529},
          'model_a': {'log_loss_report': 0.62668, 'log_loss_box': 0.646347,
                      'box_minus_report': {'games': 120, 'days': 16, 'diff': 0.0197, 'low': -0.0172, 'high': 0.0565,
                                           'level': 1 - 0.05 / 3}},
          'refit': {'reproduced_saved_model_a': 116, 'of': 120}}


@pytest.mark.skipif(NODE is None, reason='node not installed')
def test_the_page_prints_every_figure_once_100_games_are_graded():
    html = render(A_FILE)
    for want in ('Over 120 graded games', 'was 0.164 from the box score&#39;s on average', '&minus;0.0086 on the signed average',
                 '0.6267 with the injury report&#39;s', '0.6463 with the box score&#39;s',
                 '+0.0197 [&minus;0.0172, +0.0565] at 98.33%', '116 of 120 refitted', '15 graded picks were made without availability',
                 '<code>experiments/nba/stage61/registry.json</code>', 'reported, not judged'):
        assert want in html, want


@pytest.mark.skipif(NODE is None, reason='node not installed')
def test_the_page_waits_for_100_games():
    html = render({**A_FILE, 'graded': 92})
    assert '92 of the 100 graded games' in html and 'log loss' not in html
    assert 'nothing to measure' in render(None)


def test_the_checks_page_shows_it():
    _, js = page()
    body = js[js.index('function renderReliability(){'):]
    assert '<h2 class="section-title">The injury report against who played</h2>\n    ${m2Html(BD.m2)}' in body
