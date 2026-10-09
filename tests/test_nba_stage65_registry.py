"""The NBA's forward-test registration (Stage 65), held to itself, to Stage
61's results it builds on, and to the drift baseline it names.

`experiments/nba/stage65/registry.json` fixes, before any NBA pick is saved,
which models make the picks, when a pick is saved, where its price comes
from (ESPN, then Kalshi, then "no price" and never a silent switch), how the
injury report enters and what the drift check compares against. The daily
run that carries it out is tested against it in its own files.

Run with: pytest tests/test_nba_stage65_registry.py -v
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REG_PATH = ROOT / 'experiments' / 'nba' / 'stage65' / 'registry.json'
S61 = ROOT / 'experiments' / 'nba' / 'stage61' / 'results'
BASELINE = ROOT / 'data' / 'nba' / 'drift_baseline.json'


def registry():
    return json.loads(REG_PATH.read_text(encoding='utf-8'))


def test_the_forward_test_is_this_season_from_the_first_saved_pick():
    f = registry()['forward_test']
    assert f['season'] == 2026
    assert 'nothing is backfilled' in f['starts'] and '2026-10-20' in f['starts']
    assert 'never rewritten' in f['picks'] and 'predictions/nba/2026/<game_id>.json' in f['picks']


def test_the_models_are_stage_61s_with_the_values_its_validation_chose():
    chosen = json.loads((S61 / 'tuning.json').read_text(encoding='utf-8'))['chosen']
    models = registry()['models']
    assert 'experiments/nba/stage61/registry.json' in models
    assert f"H_days {chosen['H_days']}" in models and f"lambda {chosen['lambda']}" in models


def test_model_b_makes_the_pick_when_there_is_a_price():
    assert "Model B's side when the game has a market price, Model A's otherwise" in registry()['forward_test']['the_pick']


def test_the_market_is_espn_then_kalshi_then_no_price_and_never_a_silent_switch():
    m = registry()['market']
    assert m['primary'].startswith("ESPN's pre-game moneyline") and 'not marked live' in m['primary']
    assert m['fallback'].startswith("Kalshi's game-winner market") and 'only when ESPN gives no usable price' in m['fallback']
    assert 'at most 0.05' in m['fallback']
    assert "'no price'" in m['none'] and 'never a silent switch' in m['none']
    assert "('espn', 'kalshi' or none)" in m['none']
    assert 'Picks priced by the fallback are reported on their own' in registry()['forward_test']['reported']


def test_an_unreadable_injury_report_is_said_and_never_filled_in():
    a = registry()['availability']
    assert 'not listed Out' in a['playing'] and 'Day-To-Day counts as playing' in a['playing']
    assert 'without availability_matchup' in a['unreadable'] and 'Nothing is filled in' in a['unreadable']


def test_the_drift_rule_it_registers_is_the_one_the_baseline_file_holds():
    spec = json.loads(BASELINE.read_text(encoding='utf-8'))
    reg = registry()['drift']
    assert reg['file'] == 'data/nba/drift_baseline.json'
    assert spec['registered'].startswith('experiments/nba/stage65/registry.json')
    assert spec['rule']['min_games'] == 100 and '100 games' in reg['rule']
    assert spec['rule']['one_sided_level'] == 0.95 and 'one-sided 95%' in reg['rule']
    assert (spec['model'], spec['metric']) == (reg['model'], reg['metric']) == ('model_a', 'log_loss')


def test_the_baseline_is_model_a_on_stage_61s_confirmation_seasons():
    """The printed baseline must be the confirmation file's figure, to the
    last digit, and the game count it is quoted with must be the file's."""
    conf = json.loads((S61 / 'confirmation.json').read_text(encoding='utf-8'))
    a = conf['scores']['model_a']
    spec = json.loads(BASELINE.read_text(encoding='utf-8'))
    assert spec['baseline']['value'] == a['log_loss']
    assert f"({a['games']} games)" in spec['source'] and f"{a['games']} games" in registry()['drift']['baseline']
    assert conf['seasons'] == [2024, 2025]


def test_it_was_registered_before_any_nba_pick_was_saved():
    reg = registry()
    assert reg['registered'] == '2026-10-09' and reg['amendments'] == []
    picks = ROOT / 'predictions' / 'nba'
    saved = sorted(p for p in picks.rglob('*.json')) if picks.exists() else []
    for p in saved:
        assert json.loads(p.read_text(encoding='utf-8'))['saved_utc'][:10] >= reg['registered'], p
