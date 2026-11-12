"""
Stage 85 item 1 (the 2026-11-02 review): the NHL's and NBA's drift checks
look at registered checkpoints, with the one-sided 95% shared among the
looks, instead of testing at every daily run.

Run with: pytest tests/test_drift_looks.py -v
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.sports.nba import daily as nba_daily
from src.sports.nba import drift as nba_drift
from src.sports.nhl import daily as nhl_daily
from src.sports.nhl import drift as nhl_drift
from tests.optional import in_ci
from tests.page_script import day_script

ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which('node')
SPORTS = {'nhl': (nhl_drift, nhl_daily, 'experiments/nhl/stage58/registry.json'),
          'nba': (nba_drift, nba_daily, 'experiments/nba/stage65/registry.json')}
CHECKPOINTS = [100, 200, 400, 800, 1200]


@pytest.mark.parametrize('sport', SPORTS)
def test_the_looks_and_their_level_are_the_registered_ones(sport):
    drift, _, registry = SPORTS[sport]
    rule = drift.baseline()['rule']
    assert rule['checkpoints'] == CHECKPOINTS and rule['min_games'] == CHECKPOINTS[0]
    # The family's one-sided 95%, shared equally among the looks (Bonferroni).
    assert rule['one_sided_level'] == 0.95
    assert rule['per_look_level'] == pytest.approx(1 - (1 - rule['one_sided_level']) / len(rule['checkpoints']))
    reg = json.loads((ROOT / registry).read_text(encoding='utf-8'))
    text = reg['drift']['amended_2026_11_04']
    assert '100, 200, 400, 800 and 1,200 graded picks' in text and 'one-sided 99%' in text
    (entry,) = [a for a in reg['amendments'] if a['entry'] == 'drift' and a['date'] == '2026-11-04']
    assert entry['before_any_result'] is False


@pytest.mark.parametrize('sport', SPORTS)
def test_each_look_is_on_its_first_n_picks_at_the_per_look_level(sport):
    drift = SPORTS[sport][0]
    spec = drift.baseline()
    rule = spec['rule']
    losses = [0.55, 0.7, 0.62, 0.81, 0.6] * 50  # 250 graded
    looks = drift.looks(losses, spec)
    assert [look['games'] for look in looks] == [100, 200]
    for look in looks:
        n = look['games']
        assert look['lower_bound'] == drift.lower_bound(losses[:n], rule, rule['per_look_level'])
    assert looks[0]['lower_bound'] < drift.lower_bound(losses[:100], rule, rule['one_sided_level'])


@pytest.mark.parametrize('sport', SPORTS)
def test_a_look_is_one_sided_losses_between_the_bounds_flag(sport):
    """Stage 95 item 34 (T2): the level's sidedness, not only its value. Losses are
    placed so the baseline sits between the look's one-sided lower bound and the
    two-sided bound at the same level: one-sided, the look flags; two-sided, it
    would not. The bounds are worked out here from the rule's seeded bootstrap,
    not by calling lower_bound, so a changed lower_bound cannot move the target."""
    drift = SPORTS[sport][0]
    spec = drift.baseline()
    rule, base = spec['rule'], spec['baseline']['value']
    n, level = rule['checkpoints'][0], rule['per_look_level']
    raw = 0.65 + 0.25 * np.sin(np.arange(n) * 1.7)  # spread like real log losses, fixed
    idx = np.random.default_rng(rule['seed']).integers(0, n, size=(rule['n_resamples'], n))
    means = raw[idx].mean(axis=1)
    one = float(np.percentile(means, (1 - level) * 100))
    two = float(np.percentile(means, (1 - level) / 2 * 100))
    assert one - two > 0.001, 'the two bounds must be far enough apart to fall between'
    losses = list(raw + (base - (one + two) / 2))
    (look,) = drift.looks(losses, spec)
    assert look['lower_bound'] > base, 'one-sided, the bound clears the baseline'
    assert look['lower_bound'] - base == pytest.approx((one - two) / 2, abs=1e-9)
    assert look['flagged'] is True and drift.flags(losses, spec) is True


@pytest.mark.parametrize('sport', SPORTS)
def test_no_look_before_the_first_checkpoint(sport):
    drift = SPORTS[sport][0]
    spec = drift.baseline()
    assert drift.looks([5.0] * 99, spec) == [] and drift.flags([5.0] * 99, spec) is False


@pytest.mark.parametrize('sport', SPORTS)
def test_a_flag_at_an_early_look_stands_for_the_season(sport):
    drift = SPORTS[sport][0]
    spec = drift.baseline()
    base = spec['baseline']['value']
    losses = [base + 0.3] * 100 + [base - 0.3] * 300
    looks = drift.looks(losses, spec)
    assert [look['flagged'] for look in looks] == [True, False, False]
    assert drift.flags(losses, spec) is True


@pytest.mark.parametrize('sport', SPORTS)
def test_the_next_look(sport):
    drift = SPORTS[sport][0]
    spec = drift.baseline()
    assert [drift.next_look(n, spec) for n in (0, 99, 100, 799, 1199, 1200, 1300)] == [
        100, 100, 200, 800, 1200, None, None]


@pytest.mark.parametrize('sport', SPORTS)
def test_drift_rows_go_in_the_order_the_games_started(sport, tmp_path):
    """A game's id is not its date: a postponed game keeps its early id. A
    look's first n picks are the first n games played."""
    daily = SPORTS[sport][1]
    for gid, start, p in (('1', '2026-10-12T23:00:00Z', 0.7), ('2', '2026-10-10T23:00:00Z', 0.4),
                          ('3', '2026-10-11T23:00:00Z', 0.6)):
        (tmp_path / f'{gid}.json').write_text(json.dumps({'game_id': gid, 'pick': 'X', 'model_a': p,
                                                          'start_utc': start}))
    sched = pd.DataFrame([{'game_id': g, 'status': 'final', 'home_win': w} for g, w in (('1', 1), ('2', 0), ('3', 1))])
    assert daily.drift_rows(tmp_path, sched) == [(0.4, 0), (0.6, 1), (0.7, 1)]


# --- on the pages --------------------------------------------------------------

def page(sport):
    return day_script(sport)


def function_source(js, name):
    return re.search(rf'function {name}\(.*?\n\}}\n', js, re.S).group(0)


def run(sport, call):
    js = page(sport)
    prog = (function_source(js, 'pct') if 'function pct' in js else '') + function_source(js, 'driftStatus') \
        + function_source(js, 'driftLooks') + f'process.stdout.write({call});'
    return subprocess.run([NODE, '-e', prog], capture_output=True, text=True, check=True).stdout


def test_both_pages_carry_the_same_functions():
    for name in ('driftStatus', 'driftLooks'):
        assert function_source(page('nhl'), name) == function_source(page('nba'), name), name


@pytest.mark.skipif(NODE is None and not in_ci(), reason='node not installed')
@pytest.mark.parametrize('sport', SPORTS)
def test_the_page_states_the_registered_looks(sport):
    rule = json.loads((ROOT / 'data' / sport / 'drift_baseline.json').read_text(encoding='utf-8'))
    out = run(sport, f'driftLooks({json.dumps(rule)})')
    assert 'looks only at 100, 200, 400, 800 and 1,200 graded games' in out
    assert 'one-sided 99% lower bound' in out and 'one-sided 95% shared among the 5 looks' in out
    assert f"{rule['baseline']['value']:.4f}" in out


@pytest.mark.skipif(NODE is None and not in_ci(), reason='node not installed')
@pytest.mark.parametrize('sport', SPORTS)
def test_the_status_says_when_the_check_last_looked_and_will_look_next(sport):
    rule = json.loads((ROOT / 'data' / sport / 'drift_baseline.json').read_text(encoding='utf-8'))
    d = {'games': 183, 'mean_log_loss': 0.6524, 'baseline': 0.6753, 'flagged': False,
         'looks': [{'games': 100, 'lower_bound': 0.6026, 'flagged': False}], 'next_look': 200}
    out = run(sport, f'driftStatus({json.dumps(d)}, {json.dumps(rule)})')
    assert out.startswith('Not flagged.') and 'Its last look was at 100 graded games; the next is at 200.' in out
    flagged = dict(d, flagged=True, looks=[{'games': 100, 'lower_bound': 0.7, 'flagged': True}])
    assert run(sport, f'driftStatus({json.dumps(flagged)}, {json.dumps(rule)})').startswith('<b>Flagged.</b>')


def test_both_pages_print_the_looks_beside_the_status():
    assert '${driftLooks(rule)}' in function_source(page('nhl'), 'renderReliability')
    assert '${driftLooks(BD.drift_rule)}' in function_source(page('nba'), 'renderReliability')
    assert 'const status = driftStatus(d, rule);' in function_source(page('nhl'), 'renderReliability')
