"""
Stage 33's pre-registration, held to itself, before any question has an
answer. Modelled on tests/test_stage5_registry.py.

  1. Registered before answered. The commit that first adds
     experiments/nfl/stage33/results/<id>.json must have a parent whose
     registry.json already registers <id> with the same wording.
  2. Labels are computed, not typed. Every stored decision is recomputed
     from its stored intervals with stage33_eval's rules, including R3's
     non-inferiority rule and Mark's 2026-10-02 precedence amendment.
  3. The budget holds: three confirmatory slots, each interval at 98.33%.

Then the registry's own numbers and specs are tied to what they name: the
incumbents are the published MODEL_SPECS, R4's baseline is the figure in
experiments/nfl/stage5/residuals.json, and the evaluation machinery is checked
over synthetic games.
"""
import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from git_history import first_added, registry_beside

from src.core.model_specs import (
    MODEL_A_FEATURES,
    MODEL_B_FEATURES,
    MODEL_SPECS,
    ModelSpec,
)
from src.sports.nfl.research import stage33_eval as ev
from src.sports.nfl.research.stage5_eval import ForwardHoldoutError
from src.sports.nfl.weekly_update import market_prob

REPO_ROOT = Path(__file__).parent.parent
REGISTRY = REPO_ROOT / 'experiments' / 'nfl' / 'stage33' / 'registry.json'
RESULTS = REPO_ROOT / 'experiments' / 'nfl' / 'stage33' / 'results'


def registry():
    return json.loads(REGISTRY.read_text(encoding='utf-8'))


def results():
    return {p.stem: json.loads(p.read_text(encoding='utf-8')) for p in sorted(RESULTS.glob('*.json'))}


def git(*args):
    return subprocess.run(['git', '-C', str(REPO_ROOT), *args], capture_output=True, text=True)


def H(hid):
    return ev.entry(registry(), hid)


# ------------------------------------------------------------ the registry

def test_the_registry_asks_its_four_questions():
    r = registry()
    assert r['family'] == 'stage33'
    assert [h['id'] for h in r['hypotheses']] == ['R1', 'R2', 'R3', 'R4'], (
        'vacuity: a registry with no questions passes every rule below')
    for h in r['hypotheses']:
        assert h['kind'] in ('hypothesis', 'monitoring_rule'), h['id']


def test_the_seasons_do_not_overlap_and_the_holdout_is_last():
    p = registry()['protocol']
    val, conf = set(p['validation_seasons']), set(p['confirmation_seasons'])
    assert val == {2022, 2023} and conf == {2024, 2025}
    assert p['forward_holdout_season'] == 2026 > max(val | conf)


def test_the_budget_is_exactly_the_three_comparisons():
    r = registry()
    spending = [h['id'] for h in r['hypotheses'] if h['kind'] == 'hypothesis' and h.get('spends_slot')]
    assert spending == list(ev.COMPARISONS) == ['R1', 'R2', 'R3']
    assert r['protocol']['budget_m'] == len(spending)
    assert not H('R4').get('spends_slot'), 'R4 is a monitoring rule, not a confirmatory slot'


def test_the_confirmatory_level_is_bonferroni_over_the_budget():
    assert ev.confirmatory_level(registry()) == pytest.approx(1 - 0.05 / 3)


def test_the_protocol_is_what_was_registered():
    p = registry()['protocol']
    assert (p['n_resamples'], p['seed'], p['alpha'], p['primary_metric']) == (5000, 20261001, 0.05, 'log_loss')


def test_r1_and_r2_incumbents_are_the_published_model_a():
    """A registered incumbent that is not the live spec would answer a
    question about a model nobody runs."""
    for hid in ('R1', 'R2'):
        assert ev.spec_from(H(hid)['incumbent']) == MODEL_SPECS['model_a'], hid
        assert H(hid)['decision_model'] == 'model_a'
        assert H(hid)['also_report'] == ['model_b']


def test_each_candidate_changes_one_thing():
    inc = MODEL_SPECS['model_a']
    assert ev.spec_from(H('R1')['candidate']) == ModelSpec(MODEL_A_FEATURES, penalty=None, C=None)
    assert ev.spec_from(H('R2')['candidate']) == ModelSpec(MODEL_A_FEATURES, scaler='standard')
    assert ev.spec_from(H('R2')['candidate'], 'model_b') == ModelSpec(MODEL_B_FEATURES, scaler='standard')
    assert ev.spec_from(H('R1')['candidate']) != inc and ev.spec_from(H('R2')['candidate']) != inc


def test_r3_carries_its_margin_and_mark_s_precedence_as_amended():
    h = H('R3')
    assert h['margin'] == 0.002 and '+0.002' in h['decision_rule']
    assert 'Do-not-switch wins' in h['precedence']
    amended = [a for a in registry()['amendments'] if a['entry'] == 'R3']
    assert amended and all(a['before_any_result'] for a in amended)
    assert not (RESULTS / 'R3.json').exists() or results()['R3']['registry_entry'] == h


def test_r4_baseline_is_the_figure_in_its_source_file():
    """R4's two numbers were copied out of Stage 5's residuals. Prose drifts;
    hold them to the file."""
    b = H('R4')['baseline']
    src = json.loads((REPO_ROOT / 'experiments' / 'nfl' / 'stage5' / 'residuals.json').read_text(encoding='utf-8'))
    every = src['slices']['all games']
    assert b['value'] == every['log_loss_sched']
    assert b['printed_beside']['value'] == every['log_loss_lagged']
    assert every['n_games'] == 1087 and '1,087 games' in b['source']


# --------------------------------------------------------------- results

def recompute(res):
    return ev.decide(res['registry_entry'], res['validation'], res.get('confirmation'))


def test_every_result_answers_a_registered_comparison_as_worded_now():
    for hid, res in results().items():
        assert hid in ev.COMPARISONS, f'result {hid} answers a question this family does not ask'
        assert res['registry_entry'] == H(hid), (
            f'{hid}: the registry entry changed after the result was recorded')


def test_every_stored_decision_is_the_one_its_numbers_give():
    for hid, res in results().items():
        assert res['decision'] == recompute(res), f"{hid}: stored {res['decision']!r}"
        assert res['reached_confirmation'] == (res['confirmation'] is not None), hid


def test_the_budget_is_not_overspent_and_intervals_use_its_level():
    r = registry()
    level = ev.confirmatory_level(r)
    spent = [hid for hid, res in results().items() if res['reached_confirmation']]
    assert len(spent) <= r['protocol']['budget_m'], spent
    for hid in spent:
        conf = results()[hid]['confirmation']
        assert conf['ci_level'] == pytest.approx(level), hid
        assert conf['seasons'] == r['protocol']['confirmation_seasons'], hid


def test_no_result_touches_the_forward_holdout():
    holdout = registry()['protocol']['forward_holdout_season']
    for hid, res in results().items():
        blocks = [res['validation'], res.get('confirmation')]
        blocks += [b for also in res.get('also_report', {}).values() for b in also.values()]
        for block in filter(None, blocks):
            assert max(block['seasons']) < holdout, hid


def _shallow():
    return git('rev-parse', '--is-shallow-repository').stdout.strip() == 'true'


@pytest.mark.skipif(_shallow(), reason='needs full history to see when a result was first committed')
def test_every_committed_result_was_registered_in_an_earlier_commit():
    for path in sorted(RESULTS.glob('*.json')):
        rel = path.relative_to(REPO_ROOT).as_posix()
        found = first_added(REPO_ROOT, rel)
        if found is None:
            continue  # not committed yet; the check applies from the first commit
        # Following renames: Stage 52 moves these files (tests/git_history.py).
        first, then = found
        parent = git('show', f'{first}^:{registry_beside(then)}')
        assert parent.returncode == 0, f'{rel} was committed in {first[:7]} with no registry before it'
        entries = {h['id']: h for h in json.loads(parent.stdout)['hypotheses']}
        assert path.stem in entries, f'{path.stem} was answered in {first[:7]} without being registered'
        stored = json.loads(path.read_text(encoding='utf-8'))['registry_entry']
        assert entries[path.stem] == stored, f"{path.stem}'s wording changed between registration and answer"


# ------------------------------------------------------------ the rules

def test_the_forward_holdout_is_refused():
    with pytest.raises(ForwardHoldoutError):
        ev.guard_seasons([2025, 2026], registry())
    ev.guard_seasons([2024, 2025], registry())


@pytest.mark.parametrize('lo, hi, label', [
    (-0.004, -0.001, 'NON-INFERIOR'),   # better, so no worse
    (-0.003, 0.0015, 'NON-INFERIOR'),   # within the margin, not measurably worse
    (0.0005, 0.0015, 'REJECT'),         # the overlap: measurably worse wins (2026-10-02)
    (0.0001, 0.004, 'REJECT'),
    (-0.001, 0.0025, 'INCONCLUSIVE'),   # could be worse than the margin
    (-0.001, 0.002, 'INCONCLUSIVE'),    # "below" the margin is strict
    (0.0, 0.001, 'NON-INFERIOR'),       # "above" zero is strict
])
def test_r3_labels_follow_the_amended_rule(lo, hi, label):
    assert ev.decide(H('R3'), {'log_loss_diff': 0.01}, {'log_loss_ci': [lo, hi]}) == label


def test_r3_goes_to_confirmation_whatever_validation_shows():
    assert ev.reaches_confirmation(H('R3'), {'log_loss_diff': 0.05})
    with pytest.raises(ValueError):
        ev.decide(H('R3'), {'log_loss_diff': -0.01}, None)


@pytest.mark.parametrize('hid', ['R1', 'R2'])
def test_r1_and_r2_are_screened_on_validation(hid):
    h = H(hid)
    assert not ev.reaches_confirmation(h, {'log_loss_diff': 0.0})
    assert ev.decide(h, {'log_loss_diff': 0.0}, None) == 'NOT ADVANCED'
    assert ev.reaches_confirmation(h, {'log_loss_diff': -1e-6})
    with pytest.raises(ValueError):
        ev.decide(h, {'log_loss_diff': -0.001}, None)
    for (lo, hi), label in (((-0.01, -0.001), 'ACCEPT'), ((0.001, 0.01), 'REJECT'),
                            ((-0.01, 0.01), 'INCONCLUSIVE')):
        assert ev.decide(h, {'log_loss_diff': -0.001}, {'log_loss_ci': [lo, hi]}) == label


def test_every_label_this_family_can_produce_has_a_model_lab_decision():
    from src.sports.nfl.model_lab import RESULT_DECISION
    for label in ('ACCEPT', 'REJECT', 'INCONCLUSIVE', 'NOT ADVANCED', 'NON-INFERIOR'):
        assert label in RESULT_DECISION, label
    assert RESULT_DECISION['NON-INFERIOR'] == 'ACCEPT', 'R3 switches on NON-INFERIOR'


# --------------------------------------------------------- the machinery

def synthetic_hist(seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for s in range(2020, 2026):
        for w in range(1, 5):
            for _ in range(10):
                f = rng.normal(scale=[0.09, 0.09, 0.2, 0.45])
                spread = rng.normal(scale=6.0)
                logit = 6 * f[0] + 6 * f[1] + 2 * f[2] + 0.17 * spread
                rows.append({'season': s, 'week': w, **dict(zip(MODEL_A_FEATURES, f)),
                             'spread_line': np.nan if rng.random() < 0.1 else spread,
                             'home_win': int(rng.random() < 1 / (1 + np.exp(-logit)))})
    return pd.DataFrame(rows)


def small(reg):
    reg = json.loads(json.dumps(reg))
    reg['protocol']['n_resamples'] = 200
    return reg


@pytest.mark.parametrize('hid', ['R1', 'R2'])
def test_a_comparison_pairs_candidate_and_incumbent_on_the_same_games(hid):
    hist, reg = synthetic_hist(), small(registry())
    h = ev.entry(reg, hid)
    res = ev.score(h, hist, [2024, 2025], 0.95, reg)
    expected = hist[hist['season'].isin([2024, 2025])].dropna(subset=list(MODEL_A_FEATURES))
    assert res['n_games'] == len(expected) and res['seasons'] == [2024, 2025]
    b = ev.score(h, hist, [2024, 2025], 0.95, reg, 'model_b')
    assert b['n_games'] == len(expected.dropna(subset=['spread_line']))
    assert res['log_loss_diff'] != 0, 'candidate and incumbent were the same model'


def test_r3_scores_the_published_market_model_against_the_live_curve():
    hist, reg = synthetic_hist(), small(registry())
    res = ev.score(H('R3'), hist, [2024, 2025], 0.95, reg)
    scored, p_fit = ev.walk_forward(MODEL_SPECS['market'], hist, [2024, 2025])
    y = scored['home_win'].values
    eps = 1e-15
    ll = lambda p: float(np.mean(-(y * np.log(np.clip(p, eps, 1)) + (1 - y) * np.log(np.clip(1 - p, eps, 1)))))
    assert res['log_loss_candidate'] == pytest.approx(ll(p_fit))
    assert res['log_loss_incumbent'] == pytest.approx(ll(market_prob(scored['spread_line'].values)))
    assert res['n_games'] == len(scored)


def test_a_run_on_synthetic_games_is_a_result_the_rules_accept():
    """run() end to end: whatever it decides, the stored label is the one the
    numbers give, and the incumbent it refuses to substitute is real."""
    hist, reg = synthetic_hist(1), small(registry())
    for hid in ev.COMPARISONS:
        res = ev.run(hid, hist, reg)
        assert res['decision'] == recompute(res), hid
        assert res['registry_entry'] == ev.entry(reg, hid)
    bad = json.loads(json.dumps(reg))
    ev.entry(bad, 'R1')['incumbent']['C'] = 0.5
    with pytest.raises(ValueError):
        ev.run('R1', hist, bad)
