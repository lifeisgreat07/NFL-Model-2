"""The registered forward test is scored on the saved picks (Stage 84 item 1).

src/core/forward_test.py scores every saved pick whose game is final, the way
the NHL's and NBA's registrations say the live season is reported, and the
daily runs write it to results/<sport>/forward_<season>.json. Held here:

  * it scores what the registrations name, at the backtests' level, seeds and
    day blocks, and its interval is the backtests' interval on the same data;
  * each forecaster is scored on the picks it has a number for, and every
    comparison is paired on the games both scored;
  * the base rate reads only scored games before the pick's day;
  * nothing is judged: the file carries intervals, never a verdict;
  * both daily runs write the file.

Run with: pytest tests/test_forward_test.py -v
"""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.core import forward_test as ft

ROOT = Path(__file__).resolve().parents[1]
REGISTRIES = {'nhl': ROOT / 'experiments' / 'nhl' / 'stage58' / 'registry.json',
              'nba': ROOT / 'experiments' / 'nba' / 'stage65' / 'registry.json'}
BACKTESTS = {'nhl': ROOT / 'experiments' / 'nhl' / 'stage56' / 'registry.json',
             'nba': ROOT / 'experiments' / 'nba' / 'stage61' / 'registry.json'}


def registry(path):
    return json.loads(path.read_text(encoding='utf-8'))


# --- it reports what was registered ----------------------------------------------------------

@pytest.mark.parametrize('sport', ['nhl', 'nba'])
def test_the_registration_names_what_is_scored(sport):
    reported = registry(REGISTRIES[sport])['forward_test']['reported']
    for phrase in ('Model A, Model B, the market and the home-win base rate', 'log loss', 'Brier',
                   'accuracy is reported and never decides', '5,000 resamples'):
        assert phrase in reported, phrase
    assert set(ft.FORECASTERS) == {'model_a', 'model_b', 'market', 'base_rate'}
    assert ft.N_RESAMPLES == 5000


@pytest.mark.parametrize('sport', ['nhl', 'nba'])
def test_the_level_and_seed_are_the_backtests(sport):
    back = BACKTESTS[sport].read_text(encoding='utf-8')
    assert 'at level 1 - alpha/budget_m (98.33%)' in back and abs(ft.LEVEL - (1 - 0.05 / 3)) < 1e-12
    assert re.search(rf'resampling whole game days[^"]*5,000 resamples, seed {ft.SEEDS[sport]}\.', back)


def test_the_interval_is_the_backtests_on_the_same_games():
    """The same games, outcomes and two forecasters through the NBA backtest's
    day_block_interval and through this module give the same numbers."""
    from src.sports.nba import backtest
    rng = np.random.default_rng(7)
    n = 120
    table = pd.DataFrame({'game_id': [f'g{i}' for i in range(n)],
                          'day': np.repeat(pd.date_range('2026-10-20', periods=20), 6),
                          'home_win': rng.integers(0, 2, n)})
    a = pd.Series(rng.uniform(0.2, 0.8, n), index=table['game_id'])
    b = pd.Series(rng.uniform(0.2, 0.8, n), index=table['game_id'])
    want = backtest.day_block_interval(a, b, table, ft.LEVEL, seed=ft.SEEDS['nba'])
    y = table['home_win'].to_numpy(float)
    diff = ft.log_losses(a.to_numpy(float), y) - ft.log_losses(b.to_numpy(float), y)
    got = ft.interval(diff, table['day'].to_numpy(), ft.SEEDS['nba'])
    for key in ('games', 'days', 'diff', 'low', 'high', 'level'):
        assert got[key] == pytest.approx(want[key], abs=1e-12), key


# --- what is scored, and how ------------------------------------------------------------------

def finals(rows):
    return pd.DataFrame(rows, columns=['game_id', 'slate', 'home_win'])


def pick(gid, a, b=None, market=None, source=None):
    p = {'game_id': gid, 'model_a': a, 'model_b': b, 'market_source': source}
    if market is not None:
        p['market'] = {'home_prob': market, 'source': source}
    return p


def test_only_final_games_are_scored_and_each_forecaster_on_what_it_has():
    picks = [pick('1', 0.6, 0.62, 0.61, 'espn'), pick('2', 0.4), pick('3', 0.7, 0.7, 0.7, 'espn')]
    fin = finals([('1', '2026-10-20', 1.0), ('2', '2026-10-21', 0.0)])
    frame = ft.rows(picks, fin, {'2026-10-20': 0.55, '2026-10-21': 0.56})
    assert list(frame['game_id']) == ['1', '2'], 'game 3 is not final'
    s = ft.scores(frame)
    assert s['model_a']['games'] == 2 and s['base_rate']['games'] == 2
    assert s['model_b']['games'] == 1 and s['market']['games'] == 1, 'an unpriced pick scores only A and the base rate'


def test_a_score_is_log_loss_brier_and_accuracy():
    s = ft.score(np.array([0.8, 0.3]), np.array([1.0, 1.0]))
    assert s['log_loss'] == pytest.approx((-np.log(0.8) - np.log(0.3)) / 2)
    assert s['brier'] == pytest.approx((0.2 ** 2 + 0.7 ** 2) / 2)
    assert s['accuracy'] == 0.5 and s['games'] == 2


def test_a_comparison_is_paired_on_the_games_both_scored():
    picks = [pick(str(i), 0.6, 0.65 if i % 2 else None, 0.6 if i % 2 else None, 'espn') for i in range(12)]
    fin = finals([(str(i), f'2026-10-{20 + i // 3}', float(i % 3 == 0)) for i in range(12)])
    # No base rate on the first day (no earlier game): A against the base rate
    # pairs on the nine games that have both, though A has all twelve.
    frame = ft.rows(picks, fin, {f'2026-10-{20 + d}': 0.55 for d in range(1, 4)})
    out = ft.report(frame, 'nba', 2026, 'experiments/nba/stage65/registry.json')
    assert out['scores']['model_a']['games'] == 12 and out['scores']['base_rate']['games'] == 9
    assert out['comparisons']['model_a_minus_base_rate']['games'] == 9
    assert out['comparisons']['model_b_minus_model_a']['games'] == 6
    assert out['comparisons']['model_b_minus_market']['games'] == 6


def test_the_base_rate_reads_only_scored_games_before_the_day():
    played = pd.DataFrame({'day': ['2026-10-18', '2026-10-19', '2026-10-19', '2026-10-20', '2026-10-21'],
                           'home_score': [3, 1, None, 5, 9], 'away_score': [2, 4, None, 1, 0]})
    rates = ft.base_rates(['2026-10-20', '2026-10-21', '2026-10-18'], played)
    assert rates['2026-10-20'] == pytest.approx(0.5), 'the unplayed game is not an away win; the day itself is not read'
    assert rates['2026-10-21'] == pytest.approx(2 / 3)
    assert '2026-10-18' not in rates, 'no earlier game, no base rate'


def test_too_few_games_are_said_not_resampled():
    frame = ft.rows([pick('1', 0.6, 0.6, 0.6, 'espn')], finals([('1', '2026-10-20', 1.0)]), {'2026-10-20': 0.5})
    out = ft.report(frame, 'nhl', 2026, 'r')
    assert all(c.get('note') == 'too few games to resample' for c in out['comparisons'].values())


def test_nothing_is_judged():
    """The season-end decision rule is its own registered amendment (Stage 84
    item 3); this file reports intervals and carries no verdict."""
    picks = [pick(str(i), 0.6, 0.6, 0.55, 'espn') for i in range(30)]
    fin = finals([(str(i), f'2026-10-{10 + i // 3}', float(i % 2)) for i in range(30)])
    out = ft.report(ft.rows(picks, fin, {f'2026-10-{10 + d}': 0.5 for d in range(10)}), 'nba', 2026, 'r')
    text = json.dumps(out)
    assert not re.search(r'ACCEPT|REJECT|INCONCLUSIVE|verdict', text)
    assert out['interval_rule']['judged'] is False
    again = ft.report(ft.rows(picks, fin, {f'2026-10-{10 + d}': 0.5 for d in range(10)}), 'nba', 2026, 'r')
    assert again == out, 'the seed is fixed, so the same picks give the same file'


def test_the_fallback_source_is_reported_on_its_own():
    """The NBA's registration: picks priced by the fallback are reported on
    their own as well as in the total."""
    picks = [pick('1', 0.6, 0.6, 0.6, 'espn'), pick('2', 0.6, 0.6, 0.6, 'kalshi'), pick('3', 0.6)]
    fin = finals([('1', '2026-10-20', 1.0), ('2', '2026-10-20', 0.0), ('3', '2026-10-21', 1.0)])
    out = ft.report(ft.rows(picks, fin, {'2026-10-20': 0.5, '2026-10-21': 0.5}), 'nba', 2026, 'r')
    assert set(out['by_market_source']) == {'espn', 'kalshi'}
    assert out['by_market_source']['kalshi']['market']['games'] == 1
    assert out['scores']['market']['games'] == 2


def test_write_reads_the_folder_and_writes_the_file(tmp_path):
    folder = tmp_path / 'predictions'
    folder.mkdir()
    for i in range(6):
        (folder / f'{i}.json').write_text(json.dumps(pick(str(i), 0.6, 0.6, 0.6, 'espn')), encoding='utf-8')
    sched = pd.DataFrame({'game_id': [str(i) for i in range(7)], 'slate': [f'2026-10-{20 + i // 2}' for i in range(7)],
                          'status': ['final'] * 6 + ['scheduled'], 'home_win': [1, 0, 1, 1, 0, 1, None]})
    played = pd.DataFrame({'day': ['2026-10-19'] * 4, 'home_score': [1, 2, 3, 4], 'away_score': [2, 1, 0, 0]})
    out = ft.write(tmp_path / 'forward_2026.json', 'nhl', 2026, 'reg', folder, sched, played)
    assert json.loads((tmp_path / 'forward_2026.json').read_text(encoding='utf-8')) == out
    assert out['graded_picks'] == 6 and out['through'] == '2026-10-22'


# --- the daily runs write it ------------------------------------------------------------------

@pytest.mark.parametrize('sport', ['nhl', 'nba'])
def test_the_daily_run_writes_the_forward_test(sport):
    src = (ROOT / 'src' / 'sports' / sport / 'daily.py').read_text(encoding='utf-8')
    assert 'from src.core import forward_test' in src
    rel = REGISTRIES[sport].relative_to(ROOT).as_posix()
    assert f"forward_test.write(PATHS.results / f'forward_{{season}}.json', '{sport}', season,\n" in src
    assert f"'{rel}', folder, sched," in src
    wf = (ROOT / '.github' / 'workflows' / f'{sport}-daily.yml').read_text(encoding='utf-8')
    assert f'test -d results/{sport} && git add results/{sport}' in wf, 'the run commits results/<sport>/'
