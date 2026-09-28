"""
Stage 6's pre-registration, held to itself.

The same three promises as Stage 5 (tests/test_stage5_registry.py), for a
second family with its own budget:

  1. A question is written down BEFORE it is answered. The commit that first
     adds experiments/stage6/results/<id>.json must have a parent in which
     registry.json already registers <id>, with the same wording.
  2. The label is computed, not typed. Every stored decision is recomputed
     from the stored numbers.
  3. The budget holds. No more candidates reach confirmation than budget_m,
     and every confirmatory interval is at the level that budget implies.

And one that Stage 5 did not need: a question that is only asked if an
earlier one came out a certain way ("requires") has no result unless the
earlier result is there and says so. Otherwise N3 could be run after N2
failed, which is the second look the order exists to prevent.

The evaluation machinery is Stage 5's, unchanged; its own rules are tested
in tests/test_stage5_registry.py and are not repeated here.

Run with: pytest tests/test_stage6_registry.py -v
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / 'src'))

import stage5_eval as se  # noqa: E402

REGISTRY = REPO_ROOT / 'experiments' / 'stage6' / 'registry.json'
RESULTS = REPO_ROOT / 'experiments' / 'stage6' / 'results'
REGISTRY_REL = 'experiments/stage6/registry.json'

KINDS = ('screen', 'measurement', 'hypothesis', 'deferred')


def registry():
    return json.loads(REGISTRY.read_text(encoding='utf-8'))


def entries():
    return {h['id']: h for h in registry()['hypotheses']}


def results():
    return {p.stem: json.loads(p.read_text(encoding='utf-8')) for p in sorted(RESULTS.glob('*.json'))}


def git(*args):
    return subprocess.run(['git', '-C', str(REPO_ROOT), *args], capture_output=True, text=True)


# ------------------------------------------------------------ the registry

def test_the_registry_is_there_and_has_questions():
    r = registry()
    assert r['family'] == 'stage6'
    assert len(r['hypotheses']) >= 3, "vacuity: a registry with no questions passes every rule below"


def test_ids_are_unique_and_kinds_known():
    ids = [h['id'] for h in registry()['hypotheses']]
    assert len(ids) == len(set(ids)), ids
    for h in registry()['hypotheses']:
        assert h['kind'] in KINDS, h['id']
        if h['kind'] == 'deferred':
            assert h.get('reason'), f"{h['id']} is deferred without saying why"
        if h['kind'] in ('screen', 'measurement'):
            assert h.get('spends_slot') is False, f"{h['id']} is a {h['kind']} and cannot spend a slot"


def test_every_precondition_names_an_earlier_registered_question():
    order = [h['id'] for h in registry()['hypotheses']]
    for h in registry()['hypotheses']:
        for dep in h.get('requires', {}):
            assert dep in order, f"{h['id']} requires {dep}, which is not registered"
            assert order.index(dep) < order.index(h['id']), f"{h['id']} requires the later {dep}"


def test_the_seasons_do_not_overlap_and_the_holdout_is_last():
    p = registry()['protocol']
    val, conf = set(p['validation_seasons']), set(p['confirmation_seasons'])
    assert not val & conf
    assert p['forward_holdout_season'] > max(val | conf)


def test_the_seasons_are_stage5s():
    """Stage 6's candidates are compared with Stage 5's machinery and against
    a model Stage 5 tuned; changing the split between families would let a
    season that confirmed one decision screen the next."""
    s5 = json.loads((REPO_ROOT / 'experiments' / 'stage5' / 'registry.json').read_text(encoding='utf-8'))
    for k in ('validation_seasons', 'confirmation_seasons', 'forward_holdout_season'):
        assert registry()['protocol'][k] == s5['protocol'][k], k


def test_the_budget_covers_every_question_that_could_spend_a_slot():
    r = registry()
    could_spend = [h['id'] for h in r['hypotheses']
                   if h['kind'] == 'hypothesis' and h.get('spends_slot') is not False]
    assert could_spend, "vacuity: no question could ever spend a slot"
    assert len(could_spend) <= r['protocol']['budget_m'], (
        f"{len(could_spend)} questions could reach confirmation against a budget of "
        f"{r['protocol']['budget_m']}: {could_spend}"
    )


def test_the_confirmatory_level_is_bonferroni_over_the_budget():
    assert se.confirmatory_level(registry()) == pytest.approx(1 - 0.05 / 5)


def _shallow():
    return git('rev-parse', '--is-shallow-repository').stdout.strip() == 'true'


@pytest.mark.skipif(_shallow(), reason="needs full history to compare the registry with its first version")
def test_budget_m_has_not_moved_since_the_family_was_registered():
    added = git('log', '--diff-filter=A', '--format=%H', '--', REGISTRY_REL).stdout.split()
    if not added:
        pytest.skip("registry not committed yet")
    first = json.loads(git('show', f'{added[-1]}:{REGISTRY_REL}').stdout)
    assert registry()['protocol']['budget_m'] == first['protocol']['budget_m'], (
        "budget_m changed after the family was registered. Raising it after seeing results "
        "is a new family, not an edit."
    )


# --------------------------------------------------------------- results

def recompute(res):
    """The label a result's own numbers give, by the registry's rule for its kind."""
    kind = res['registry_entry']['kind']
    if kind == 'screen' and res['id'] == 'R1':
        # a correlation across referees: PASS only if its interval's lower end is above zero
        return 'PASS' if res['persistence']['corr_ci_95'][0] > 0 else 'FAIL'
    if kind == 'screen':
        diff = res['candidate_minus_control']
        return 'PASS' if diff['mse_diff'] < 0 and diff['mse_ci_95'][1] < 0 else 'FAIL'
    if kind == 'hypothesis':
        return se.decide(res['validation'], res.get('confirmation'))
    return res['decision']  # a measurement records what it saw


def test_every_result_answers_a_registered_question_as_worded_now():
    reg = entries()
    for hid, res in results().items():
        assert hid in reg, f"result {hid} answers a question the registry does not ask"
        assert res['registry_entry'] == reg[hid], (
            f"{hid}: the registry entry changed after the result was recorded. A question "
            "is not edited once answered; register a new one."
        )


def test_every_stored_decision_is_the_one_its_numbers_give():
    for hid, res in results().items():
        assert res['decision'] == recompute(res), f"{hid}: stored {res['decision']!r}"


def check_preconditions(reg, res_by_id):
    """[(id, missing-or-wrong precondition)] for every result that should not exist."""
    bad = []
    for hid in res_by_id:
        for dep, needed in reg[hid].get('requires', {}).items():
            got = res_by_id.get(dep, {}).get('decision')
            if got != needed:
                bad.append((hid, f"requires {dep} = {needed}, found {got}"))
    return bad


def test_no_question_is_answered_unless_its_precondition_held():
    assert check_preconditions(entries(), results()) == []


def test_the_precondition_check_fires_on_a_synthetic_breach():
    """Today's results may not reach the failing branch, so it is exercised here."""
    reg = {'A': {}, 'B': {'requires': {'A': 'ACCEPT'}}}
    assert check_preconditions(reg, {'A': {'decision': 'ACCEPT'}, 'B': {}}) == []
    assert check_preconditions(reg, {'A': {'decision': 'INCONCLUSIVE'}, 'B': {}})
    assert check_preconditions(reg, {'B': {}})


def test_deferred_and_unrun_questions_have_no_result():
    reg = entries()
    for hid in results():
        assert reg[hid]['kind'] != 'deferred', f"{hid} is deferred and has a result"


def test_the_budget_is_not_overspent_and_intervals_use_its_level():
    r = registry()
    level = se.confirmatory_level(r)
    spent = [hid for hid, res in results().items() if res.get('reached_confirmation')]
    assert len(spent) <= r['protocol']['budget_m'], spent
    for hid in spent:
        conf = results()[hid]['confirmation']
        assert conf['ci_level'] == pytest.approx(level), hid
        assert conf['seasons'] == r['protocol']['confirmation_seasons']


def test_no_result_touches_the_forward_holdout():
    holdout = registry()['protocol']['forward_holdout_season']
    for hid, res in results().items():
        for part in ('fit', 'validation', 'confirmation', 'model_b'):
            block = res.get(part)
            if block:
                assert max(block['seasons']) < holdout, (hid, part)


@pytest.mark.skipif(_shallow(), reason="needs full history to see when a result was first committed")
def test_every_committed_result_was_registered_in_an_earlier_commit():
    for path in sorted(RESULTS.glob('*.json')):
        rel = path.relative_to(REPO_ROOT).as_posix()
        added = git('log', '--diff-filter=A', '--format=%H', '--', rel).stdout.split()
        if not added:
            continue  # not committed yet; the check applies from the first commit
        first = added[-1]
        parent_registry = git('show', f'{first}^:{REGISTRY_REL}')
        assert parent_registry.returncode == 0, (
            f"{rel} was committed in {first[:7]}, whose parent has no registry at all"
        )
        before = {h['id']: h for h in json.loads(parent_registry.stdout)['hypotheses']}
        hid = path.stem
        assert hid in before, f"{hid} was answered in {first[:7]} without being registered before it"
        stored = json.loads(path.read_text(encoding='utf-8'))['registry_entry']
        assert before[hid] == stored, f"{hid}'s wording changed between registration and answer"
