"""MLB's forward test (Stage 101 item 1), registered before any MLB pick is saved.

`experiments/mlb/stage101/registry.json` fixes, on Mark's answers of 2026-11-24, how the 2027 picks are made, locked,
graded and judged. Its run times cannot be known until spring training shows when clubs name their probable pitchers,
so what is registered is the rule that turns that measurement into the times. These tests hold the registration to
its answers, and to the lessons the NBA's forward test needed amendments for, so a change has to be an amendment.

Run with: pytest tests/test_mlb_stage101_registry.py -v
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / 'experiments' / 'mlb' / 'stage101' / 'registry.json'
STAGE98 = ROOT / 'experiments' / 'mlb' / 'stage98'


def registry():
    return json.loads(REGISTRY.read_text(encoding='utf-8'))


def test_it_is_registered_before_opening_day():
    r = registry()
    assert r['registered'] == '2026-11-24' < '2027-03-25'
    assert 'before any MLB pick was saved' in r['approved_by']


def test_the_models_are_stage98s_with_the_settings_its_validation_chose():
    chosen = json.loads((STAGE98 / 'results' / 'tuning.json').read_text(encoding='utf-8'))['chosen']
    models = registry()['models']
    assert 'experiments/mlb/stage98/registry.json' in models
    for key, value in (('H_days', chosen['H_days']), ('lambda', chosen['lambda']), ('K_outs', chosen['K_outs'])):
        assert f'{key} {value}' in models, f'{key}: the registration does not name the chosen {value}'
    # The NBA's lessons, registered here from the start rather than by amendment.
    assert 'strictly before the pick\'s official date' in models
    assert 'with the price the daily runs recorded for them' in models


def test_the_run_times_come_from_a_rule_fixed_now():
    runs = registry()['forward_test']['runs']
    assert runs['count'].startswith('Three scheduled runs a day')
    assert 'Not fixed here' in runs['times'] and 'probables_timing.json' in runs['times']
    assert 'every 30 minutes' in runs['measurement'] and '2027-03-21' in runs['measurement']
    rule = runs['rule']
    assert '48 half-hour marks' in rule and 'highest share' in rule and 'one percentage point' in rule
    assert 'below 90%' in rule and 'disclosed by amendment before the first pick' in rule
    assert 'at least one hour before its listed first pitch' in runs['lock']


def test_a_side_with_no_probable_gets_the_league_rate_and_the_pick_says_so():
    s = registry()['forward_test']['starters']
    assert 'league rate' in s['unknown'] and 'starter_named false' in s['unknown']
    assert 'never redone' in s['changed']


def test_the_market_is_espn_then_kalshi_never_silently():
    m = registry()['market']
    assert m['primary'].startswith("ESPN's pre-game moneyline") and '1.00 and 1.20' in m['primary']
    assert 'KXMLBGAME' in m['fallback'] and 'only when ESPN gives no usable price' in m['fallback']
    assert "'no price'" in m['none'] and 'never a silent switch' in m['none']


def test_the_verdict_is_taken_once_after_the_regular_season_by_the_backtests_rule():
    d = registry()['forward_test']['decision']
    assert 'Once' in d['when'] and 'regular season' in d['when'] and 'the postseason never does' in d['when']
    assert '98.33%' in d['rule'] and 'whole game days 5,000 times' in d['what'] and '20261112' in d['what']
    assert (ROOT / d['implemented_by']).exists()


def test_the_drift_check_waits_for_baselines_from_the_confirmation():
    drift = registry()['drift']
    assert '100, 200, 400, 800 and 1,600' in drift['looks'] and '99%' in drift['looks']
    assert 'once Stage 99 has run' in drift['baseline'] and 'the drift check does not run' in drift['baseline']
    assert 'whole game days' in drift['rule']


def test_it_discloses_registering_before_the_confirmation():
    assert any("before Stage 99's confirmation" in d for d in registry()['disclosures'])
