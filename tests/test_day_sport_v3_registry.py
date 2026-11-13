"""The day sports' v3 registrations (Stage 105): a shadow beside v2, fixed before any v3 forecast exists.

Run with: pytest tests/test_day_sport_v3_registry.py -v
"""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def reg(sport):
    return json.loads((ROOT / 'experiments' / sport / 'stage105_v3' / 'registry.json').read_text(encoding='utf-8'))


@pytest.mark.parametrize('sport', ['nba', 'nhl'])
def test_it_is_a_shadow_beside_v2_that_changes_nothing_registered(sport):
    r = reg(sport)
    assert r['status'] == 'shadow' and r['based_on'] == [f'experiments/{sport}/stage95_v2/registry.json']
    assert 'never the board\'s pick' in r['forward_test']['shadow']['never_a_pick']
    assert "v2's decision" in r['forward_test']['shadow']['never_a_pick']
    assert f'predictions/{sport}/2026-v3/' in r['forward_test']['shadow']['what']
    assert 'Nothing is backfilled' in r['forward_test']['shadow']['what']


@pytest.mark.parametrize('sport', ['nba', 'nhl'])
def test_it_is_registered_on_its_day_and_unamended(sport):
    assert reg(sport)['registered'] == '2026-11-13' and reg(sport)['amendments'] == []


def test_each_sport_registers_its_own_changes_and_nothing_tuned():
    assert set(reg('nba')['changes']) == {'b2b', 'star_availability'}
    assert set(reg('nhl')['changes']) == {'b2b'}
    assert 'p = 2 is fixed here, not tuned' in reg('nba')['changes']['star_availability']
    for sport in ('nba', 'nhl'):
        assert "v2's tuned values, not re-tuned" in reg(sport)['protocol']['tuning']
        assert reg(sport)['changes']['b2b'].startswith('b2b_matchup = (1 if the away team played')


@pytest.mark.parametrize('sport', ['nba', 'nhl'])
def test_it_is_decided_once_after_the_season_at_975_and_says_what_it_expects(sport):
    d = reg(sport)['forward_test']['decision']
    assert set(d['comparisons']) == {'W1', 'W2'} and 'level 97.5%' in d['rule']
    assert d['when'].startswith('Once,') and 'No earlier look decides anything' in d['when']
    assert d['expected'].startswith('INCONCLUSIVE')


@pytest.mark.parametrize('sport', ['nba', 'nhl'])
def test_it_discloses_that_its_evidence_is_from_training_seasons_only(sport):
    text = ' '.join(reg(sport)['disclosures'])
    assert 'training seasons only' in text and 'no validation, confirmation, forward-test' in text
    assert 'only the plain flag is registered' in text


@pytest.mark.parametrize('sport', ['nba', 'nhl'])
def test_on_a_neutral_site_model_b_keeps_its_intercept(sport):
    m = reg(sport)['protocol']['models']
    assert "Model A's forecast loses the fitted intercept" in m and "Model B's loses nothing" in m
