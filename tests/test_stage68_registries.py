"""Stage 68's measurement registrations (the 2026-10-09 audit's E22, E24, E25, E28).

Written before any of the data they read, approved by Mark, and held to
one shape: each says what it asks, why, from what data, by what method,
when it is reported and what it decides, and none changes a model.

Kept in experiments/<sport>/measurements/, not a stage folder: the Model
Lab reads every stage*/registry.json as a hypothesis registry.

Run with: pytest tests/test_stage68_registries.py -v
"""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FILES = {s: ROOT / 'experiments' / s / 'measurements' / 'stage68.json' for s in ('nfl', 'nhl', 'nba')}
FIELDS = ('id', 'audit', 'question', 'why', 'data', 'method', 'when', 'decides')
WANT = {'nfl': {'S68-N1-CLAUSE'}, 'nhl': {'S68-L1-NHL', 'S68-DRIFT-DAYBLOCK'},
        'nba': {'S68-L1-NBA', 'S68-M2-STATUS', 'S68-DRIFT-DAYBLOCK'}}


def reg(sport):
    return json.loads(FILES[sport].read_text(encoding='utf-8'))


@pytest.mark.parametrize('sport', FILES)
def test_each_is_approved_and_changes_no_model(sport):
    r = reg(sport)
    assert r['registered'] == '2026-10-10' and r['approved_by'].startswith('Mark, 2026-10-09 23:52 ET')
    assert 'No model, lock rule, market source or saved pick changes' in r['changes_no_model']
    assert r['amendments'] == []


@pytest.mark.parametrize('sport', FILES)
def test_each_measurement_says_everything(sport):
    ms = reg(sport)['measurements']
    assert {m['id'] for m in ms} == WANT[sport]
    for m in ms:
        missing = [f for f in FIELDS if not m.get(f)]
        assert not missing, (m['id'], missing)
        assert m['decides'].startswith('Nothing'), m['id']


def test_n1_is_described_not_reopened():
    m = reg('nfl')['measurements'][0]
    assert 'N1 stays a declared rule' in m['why'] and 'not narrowed or widened' in m['decides']
