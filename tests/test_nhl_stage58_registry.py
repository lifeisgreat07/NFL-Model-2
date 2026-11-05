"""The NHL's forward-test registration (Stage 58 item 1), held to itself and
to the code that carries it out.

Run with: pytest tests/test_nhl_stage58_registry.py -v
"""
import json
from pathlib import Path

from src.sports.nhl import daily, drift

ROOT = Path(__file__).resolve().parents[1]
REG = json.loads((ROOT / 'experiments/nhl/stage58/registry.json').read_text(encoding='utf-8'))


def test_the_forward_test_is_this_season_from_the_first_saved_pick():
    f = REG['forward_test']
    assert f['season'] == 2026
    assert 'nothing is backfilled' in f['starts']
    assert 'never rewritten' in f['picks']


def test_the_drift_rule_it_registers_is_the_one_the_baseline_file_holds():
    spec = drift.baseline()
    assert REG['drift']['file'] == 'data/nhl/drift_baseline.json'
    assert spec['rule']['min_games'] == 100 and '100 games' in REG['drift']['rule']
    assert spec['registered'].startswith('experiments/nhl/stage58/registry.json')


def test_model_b_makes_the_pick_as_registered():
    assert "Model B's side when the game has a market price" in REG['forward_test']['the_pick']
    assert daily.CODE_VERSION == 'nhl-stage56'
    # One amendment since: the season-end decision rule (Stage 84 item 3),
    # disclosed as written after the first forward-test figures were read.
    # And a disclosed deviation: picks fitted through their own slate day (Stage 85 item 4).
    # And Stage 85 item 5: this season's games carry their recorded price into Model B's fit.
    # And Stage 85 item 1: the drift check looks at registered checkpoints.
    assert [a['entry'] for a in REG['amendments']] == ['forward_test.decision', 'deviation', 'models', 'drift',
                                                       'disclosures']
