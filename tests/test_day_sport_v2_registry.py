"""The day-sport v2 shadow's registrations (Stage 95 item 35 with Stage 94 items 24, 27 to 30;
experiments/nba/stage95_v2/registry.json, experiments/nhl/stage95_v2/registry.json).

Written before any v2 model is fitted or forecast saved; v2 runs beside the registered models
and is judged against them on the live forward test at the regular season's end.

Run with: pytest tests/test_day_sport_v2_registry.py -v
"""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPORTS = {'nba': ('stage61', 'stage65'), 'nhl': ('stage56', 'stage58')}


def reg(sport):
    return json.loads((ROOT / 'experiments' / sport / 'stage95_v2' / 'registry.json').read_text(encoding='utf-8'))


@pytest.mark.parametrize('sport', SPORTS)
def test_it_is_a_shadow_that_cites_the_registrations_it_sits_beside(sport):
    r = reg(sport)
    assert r['status'] == 'shadow' and r['registered'] == '2026-11-11'
    # Every amendment says what it changed and what had been seen; audit 8's (B2) came after v2's backtests.
    assert all(a['seen'] and a['change'] for a in r['amendments'])
    entries = [(a['entry'], a['before_any_result']) for a in r['amendments']]
    assert entries == ([('changes.30_slates', True)] if sport == 'nba' else []) + [('forward_test.shadow', False)]
    assert r['based_on'] == [f'experiments/{sport}/{s}/registry.json' for s in SPORTS[sport]]
    for path in r['based_on']:
        assert (ROOT / path).exists(), path
    assert 'never the board\'s pick' in r['forward_test']['shadow']['never_a_pick']


def test_a_slate_still_doubled_is_dropped_and_listed_not_guessed():
    """Item 30 as amended on 2026-11-12, before any v2 fit: ESPN's record keeps both 2020-03-01 games on one slate."""
    text = reg('nba')['changes']['30_slates']
    assert 'is dropped from' in text and 'dropped ids are written into' in text and 'no date is guessed' in text
    assert 'refuses' not in text


@pytest.mark.parametrize('sport', SPORTS)
def test_no_v2_forecast_was_saved_before_it_was_registered(sport):
    folder = ROOT / 'predictions' / sport / '2026-v2'
    for path in sorted(folder.glob('*.json')) if folder.exists() else []:
        saved = json.loads(path.read_text(encoding='utf-8'))['saved_utc']
        assert saved[:10] >= reg(sport)['registered'], path.name


@pytest.mark.parametrize('sport', SPORTS)
def test_it_is_tuned_on_the_validation_seasons_only_and_decided_live_at_975(sport):
    r = reg(sport)
    assert 'validation seasons only' in r['protocol']['tuning']
    assert 'decides nothing' in r['protocol']['confirmation']
    d = r['forward_test']['decision']
    assert set(d['comparisons']) == {'V1', 'V2'}
    assert '1 - 0.05/2 (97.5%)' in d['rule'] and 'resampling whole game days' in d['rule']
    assert 'from the 2027-28 season' in d['consequence'] and 'never during the 2026 season' in d['consequence']


def test_each_sport_registers_its_own_audit_items():
    assert set(reg('nba')['changes']) == {'24_availability', '27_history', '28_neutral', '29_ingest', '30_slates'}
    assert set(reg('nhl')['changes']) == {'35_goalie', '28_neutral', '29_ingest'}
    # Whole-minute rounding: a complete NBA box can sum to a few under 240, so the short-box rule allows it.
    assert 'by more than half a minute for each player it lists' in reg('nba')['changes']['29_ingest']
    # The NHL's prices to 2023-24 are the two sides of a three-way line, which sum below 1 by construction.
    nhl_price = reg('nhl')['changes']['29_ingest']
    assert '[1.00, 1.20] for a two-way moneyline' in nhl_price and '[0.75, 1.00] for the two sides of the three-way' in nhl_price
    grid = reg('nhl')['protocol']['tuning']
    assert 'K_shots in {1000, 2000, 4000, 8000, 16000, none}' in grid and 'H_days in {60, 120, 240}' in grid
    tuning = json.loads((ROOT / 'experiments/nhl/stage56/results/tuning.json').read_text(encoding='utf-8'))
    ks = sorted({row['K_shots'] for row in tuning['grid']})
    assert tuning['chosen']['K_shots'] == ks[-1] == 2000, 'the grid is extended because K chose its top'


def test_item_24_is_the_same_rule_in_the_backtest_and_live():
    text = reg('nba')['changes']['24_availability']
    assert "did not appear in the team's previous game" in text
    assert 'stops reading who played in the game itself' in text and 'stops reading the injury report' in text
    assert 'MV2' in reg('nba')['measurements']


def test_the_two_nhl_shadow_records_written_after_their_picks_are_kept_and_excluded():
    excluded = reg('nhl')['forward_test']['decision']['excluded']
    assert set(excluded) == {'2026020307', '2026020308'}
    assert 'excluded' not in reg('nba')['forward_test']['decision']
    for gid in excluded:
        assert gid in reg('nhl')['amendments'][-1]['change']
