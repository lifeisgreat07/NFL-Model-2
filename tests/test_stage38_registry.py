"""Stage 38's pre-registration, held to itself before any question has an
answer (registered 2026-10-04, from the fourth audit's items 8, 13, 14, 17).

The budget, the slots, the levels and the shape of each entry are checked
here so that the file cannot drift before it is answered. When a result
lands, the rules Stage 33's registry test applies -- registered before
answered, labels computed from intervals -- extend to this file.

Run with: pytest tests/test_stage38_registry.py -v
"""
import json
from pathlib import Path

from src.pipeline import model_lab as ml

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / 'experiments' / 'stage38' / 'registry.json'


def registry():
    return json.loads(REGISTRY.read_text(encoding='utf-8'))


def entry(hid):
    return next(h for h in registry()['hypotheses'] if h['id'] == hid)


def test_the_registry_asks_its_five_questions():
    assert [h['id'] for h in registry()['hypotheses']] == ['C1', 'B1', 'M1', 'L1', 'L2']


def test_two_slots_and_the_level_they_set():
    p = registry()['protocol']
    assert (p['alpha'], p['budget_m']) == (0.05, 2)
    slots = [h['id'] for h in registry()['hypotheses'] if h['spends_slot'] not in (False, 'False')]
    assert slots == ['C1', 'L2'], slots
    assert '97.5%' in p['budget_rule'] and round(1 - p['alpha'] / p['budget_m'], 4) == 0.975
    for hid in ('C1', 'L2'):
        assert '97.5%' in entry(hid)['decision_rule']


def test_the_seasons_are_the_project_split():
    p = registry()['protocol']
    assert (p['validation_seasons'], p['confirmation_seasons'], p['forward_holdout_season']) == (
        [2022, 2023], [2024, 2025], 2026)
    assert p['n_resamples'] == 5000 and p['accuracy'] == 'Reported, never decides.'


def test_c1_decides_on_every_week_and_only_reports_the_first_four():
    c1 = entry('C1')
    assert 'ALL weeks' in c1['screen'] and 'all weeks' in c1['decision_rule']
    assert any('never decides' in r for r in c1['also_report'])
    assert c1['incumbent']['offseason_gap_weeks'] == 0


def test_m1_is_registered_not_in_force_so_it_has_no_row_yet():
    assert entry('M1')['kind'] == 'monitoring_rule' and entry('M1')['status'] == 'REGISTERED'
    assert not [e for e in ml.result_entries() if e['stage'] == 'Stage 38'], (
        'a Stage 38 question is on the page before it has an answer')


def test_no_registered_question_has_a_result_yet():
    assert not (REGISTRY.parent / 'results').exists() or not any((REGISTRY.parent / 'results').iterdir())
