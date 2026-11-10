"""Stage 84 item 4: Stage 56's M2 on the live season, the projected starter
against the actual one.

experiments/nhl/stage56/registry.json: "Over the forward test's graded games:
how often the projected starter started, and Model A's log loss with each",
printed on the checking page once 50 games are graded. src/sports/nhl/m2.py
refits Model A as each pick records, rates the clubs as of the day it was
saved, and scores each game with the goalies the pick used and with the two
who started. Held here with the ratings and the model stubbed, so each rule
is checked on its own.

Run with: pytest tests/test_nhl_m2.py -v
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.sports.nhl import backtest, m2
from tests.optional import in_ci

ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which('node')
K = 2000.0
GOALIE = backtest.goalie_column(K)


class Rated:
    """A day's ratings: the goalie column is the two goalie ids' difference / 1000."""
    def __init__(self, train):
        self.train = train

    def matchup(self, home, away, hg, ag, ks):
        return {'goal_matchup': 0.0, 'shot_matchup': 0.0, GOALIE: (float(hg) - float(ag)) / 1000}


class Model:
    def __init__(self, n):
        self.n = n

    def predict_proba(self, x):
        p = 1 / (1 + np.exp(-x[GOALIE].to_numpy()))
        return np.column_stack([1 - p, p])


@pytest.fixture
def seen(monkeypatch):
    calls = {'fit': [], 'rate': []}
    monkeypatch.setattr(m2.ratings, 'day_ratings', lambda train, day, h: calls['rate'].append((train, day)) or Rated(train))
    return calls


def fit(calls):
    def f(table, k):
        calls['fit'].append(table)
        return Model(len(table)), None
    return f


def pick(gid, slate, saved, hg, ag, through='2026-10-30', model_a=None):
    p = {'game_id': gid, 'slate': slate, 'saved_utc': saved, 'home': 'TOR', 'away': 'MTL',
         'goalies': {'home': {'player_id': hg}, 'away': {'player_id': ag}}, 'model_a': model_a}
    if through:
        p['training_through'] = through
    return p


def box(rows):
    return pd.DataFrame(rows, columns=['game_id', 'home_goalie_id', 'away_goalie_id', 'home_score', 'away_score'])


GAMES = pd.DataFrame({'day': pd.to_datetime(['2026-10-29', '2026-10-30', '2026-10-31', '2026-11-01'])})
TABLE = pd.DataFrame({'day': ['2026-10-29', '2026-10-30', '2026-10-31', '2026-11-01'], 'home_prob': [0.5] * 4})


def test_each_game_is_scored_with_the_goalies_used_and_the_two_who_started(seen):
    picks = [pick('1', '2026-10-31', '2026-10-31T21:00:00Z', 3000, 1000),
             pick('2', '2026-10-31', '2026-10-31T21:00:00Z', 3000, 1000)]
    b = box([('1', 3000, 1000, 3, 2), ('2', 1000, 1000, 1, 4)])
    out = m2.measure(picks, GAMES, TABLE, b, 120, K, fit(seen))
    s = out['starters']
    assert s == {'sides': 4, 'projected_started': 3, 'games_both_started': 1, 'games_a_starter_differed': 1}
    p_same, p_proj2, p_act2 = 1 / (1 + np.exp(-2.0)), 1 / (1 + np.exp(-2.0)), 0.5
    want_proj = np.mean([-np.log(p_same), -np.log(1 - p_proj2)])
    want_act = np.mean([-np.log(p_same), -np.log(1 - p_act2)])
    assert out['model_a']['log_loss_projected'] == pytest.approx(want_proj)
    assert out['model_a']['log_loss_actual'] == pytest.approx(want_act)


def test_the_refit_is_the_picks_own_cutoff_or_the_day_before_it_was_saved(seen):
    # Pick 1 was saved on 10-31 but records a fit through 10-29 (not the day
    # before it was saved), so the two rules give different cutoffs.
    picks = [pick('1', '2026-10-31', '2026-10-31T21:00:00Z', 1, 1, through='2026-10-29'),
             pick('2', '2026-11-01', '2026-11-01T14:00:00Z', 1, 1, through=None)]
    m2.measure(picks, GAMES, TABLE, box([('1', 1, 1, 1, 0), ('2', 1, 1, 1, 0)]), 120, K, fit(seen))
    cutoffs = [str(pd.to_datetime(t['day']).max().date()) for t in seen['fit']]
    assert cutoffs == ['2026-10-29', '2026-10-31'], 'its training_through; else every game before the day it was saved'


def test_ratings_are_as_of_the_eastern_day_the_pick_was_saved(seen):
    # 01:00 UTC on 11-01 is 9 PM on 10-31 in New York.
    m2.measure([pick('1', '2026-11-01', '2026-11-01T01:00:00Z', 1, 1)], GAMES, TABLE,
               box([('1', 1, 1, 1, 0)]), 120, K, fit(seen))
    ((train, day),) = seen['rate']
    assert day == pd.Timestamp('2026-10-31')
    assert train['day'].max() == pd.Timestamp('2026-10-30'), 'games before that day only'


def test_games_without_a_final_box_score_are_left_out(seen):
    picks = [pick('1', '2026-10-31', '2026-10-31T21:00:00Z', 1, 1), pick('2', '2026-10-31', '2026-10-31T21:00:00Z', 1, 1),
             pick('3', '2026-10-31', '2026-10-31T21:00:00Z', 1, 1)]
    out = m2.measure(picks, GAMES, TABLE, box([('1', 1, 1, 2, 1), ('2', 1, 1, None, None)]), 120, K, fit(seen))
    assert out['graded'] == 1


def test_the_refit_is_checked_against_the_saved_probability(seen):
    p_same = round(1 / (1 + np.exp(-2.0)), 4)
    picks = [pick('1', '2026-10-31', '2026-10-31T21:00:00Z', 3000, 1000, model_a=p_same),
             pick('2', '2026-10-31', '2026-10-31T21:00:00Z', 3000, 1000, model_a=0.5)]
    out = m2.measure(picks, GAMES, TABLE, box([('1', 3000, 1000, 1, 0), ('2', 3000, 1000, 1, 0)]), 120, K, fit(seen))
    assert out['refit'] == {'reproduced_saved_model_a': 1, 'of': 2, 'provenance_recorded': 2}


def test_the_difference_has_a_day_block_interval_and_no_verdict(seen):
    picks = [pick(str(i), f'2026-10-{20 + i // 3}', f'2026-10-{20 + i // 3}T21:00:00Z', 2000 + i, 1000)
             for i in range(12)]
    b = box([(str(i), 2000 + i if i % 4 else 1000, 1000, i % 2, 1 - i % 2) for i in range(12)])
    out = m2.measure(picks, GAMES, TABLE, b, 120, K, fit(seen))
    d = out['model_a']['actual_minus_projected']
    assert d['days'] == 4 and d['games'] == 12 and d['low'] <= d['diff'] <= d['high']
    assert out['judged'] is False and not re.search(r'ACCEPT|REJECT|INCONCLUSIVE', json.dumps(out))


# --- the registration, the run and the page ---------------------------------------------------

def test_it_measures_what_the_registration_names():
    reg = json.loads((ROOT / 'experiments' / 'nhl' / 'stage56' / 'registry.json').read_text(encoding='utf-8'))
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
    assert 'how often the projected starter started' in spec['question'] and "Model A's log loss with each" in spec['question']
    assert 'once 50 games are graded' in spec['consequence'] and m2.MIN_GAMES == 50
    assert spec['spends_slot'] is False


def test_the_daily_run_writes_it_every_run_and_commits_it():
    src = (ROOT / 'src' / 'sports' / 'nhl' / 'daily.py').read_text(encoding='utf-8')
    main = src[src.index('def main('):]
    assert main.index("table = ratings.features(games, h, [k])") < main.index('if decision.lock:'), \
        'the table is built on every run, not only a locking one'
    assert "m2.write(PATHS.results / f'm2_{season}.json', forward_test.read_picks(folder), games, table," in main
    wf = (ROOT / '.github' / 'workflows' / 'nhl-daily.yml').read_text(encoding='utf-8')
    assert 'test -d results/nhl && git add results/nhl' in wf
    site = (ROOT / 'src' / 'sports' / 'nhl' / 'site.py').read_text(encoding='utf-8')
    assert "'m2': _read(PATHS.results / f'm2_{season}.json')," in site


def page_function():
    js = (ROOT / 'src' / 'sports' / 'nhl' / 'pages' / 'nhl.js').read_text(encoding='utf-8').replace('\r\n', '\n')
    return re.search(r'function m2Html\(m\)\{.*?\n\}\n', js, re.S).group(0), js


def render(m):
    fn, _ = page_function()
    return subprocess.run([NODE, '-e', fn + f'process.stdout.write(m2Html({json.dumps(m)}));'],
                          capture_output=True, text=True, check=True, encoding='utf-8').stdout


A_FILE = {'measurement': 'M2', 'registered': 'experiments/nhl/stage56/registry.json', 'graded': 157,
          'printed_from': 50, 'judged': False,
          'starters': {'sides': 314, 'projected_started': 299, 'games_both_started': 143, 'games_a_starter_differed': 14},
          'model_a': {'log_loss_projected': 0.65091, 'log_loss_actual': 0.65112,
                      'actual_minus_projected': {'games': 157, 'days': 28, 'diff': 0.00021, 'low': -0.0011,
                                                 'high': 0.0016, 'level': 1 - 0.05 / 3}},
          'refit': {'reproduced_saved_model_a': 130, 'of': 157, 'provenance_recorded': 131}}


@pytest.mark.skipif(NODE is None and not in_ci(), reason='node not installed')
def test_the_page_prints_every_figure_once_50_games_are_graded():
    html = render(A_FILE)
    for want in ('Over 157 graded games', 'on 299 of 314 sides (95.2%)', 'both started in 143',
                 '0.6509 with the goalies the picks used', '0.6511 with the two who started',
                 '+0.0002 [&minus;0.0011, +0.0016] at 98.33%', '130 of 157 refitted probabilities',
                 '<code>experiments/nhl/stage56/registry.json</code>', 'reported, not judged'):
        assert want in html, want


@pytest.mark.skipif(NODE is None and not in_ci(), reason='node not installed')
def test_the_page_waits_for_50_games():
    html = render({**A_FILE, 'graded': 49})
    assert '49 of the 50 graded games' in html and 'log loss' not in html
    assert 'nothing to measure' in render(None)


def test_the_checks_page_shows_it():
    _, js = page_function()
    body = js[js.index('function renderReliability(){'):]
    assert '<h2 class="section-title">The projected starter against the actual one</h2>\n    ${m2Html(DATA.m2)}' in body
