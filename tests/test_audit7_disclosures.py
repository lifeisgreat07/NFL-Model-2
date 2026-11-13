"""Stage 94 items 23 and 25 (audit 7, M1 and M3): two disclosures.

Item 23: every priced pick saved before 2026-11-05 came from a Model B that had
not trained on a game of this season (#600 fixed that from then on). The
registries say so, and the committed picks bear it out: until then every
pick's training_games_priced is the historical count, and it never falls.

Item 25: "the market" live is the price read at the lock, hours before the
start, while the backtest's is the closing price. The registries say so, and
the forward-test file carries the instrument, which both checks pages print
beside the forward test.

Run with: pytest tests/test_audit7_disclosures.py -v
"""
import json
from pathlib import Path

import pytest

from src.core import forward_test as ft
from tests.optional import in_ci
from tests.test_forward_on_page import NODE, a_file, render

ROOT = Path(__file__).resolve().parents[1]
REGISTRIES = {'nhl': 'experiments/nhl/stage58/registry.json', 'nba': 'experiments/nba/stage65/registry.json'}
#: The rows of data/<sport>/history/market_*.csv Model B trained on before #600 (audit 7's count).
HISTORICAL_PRICED = {'nhl': 7427, 'nba': 14017}
FIRST_SEASON_PRICES = '2026-11-05'


def registry(sport):
    return json.loads((ROOT / REGISTRIES[sport]).read_text(encoding='utf-8'))


@pytest.mark.parametrize('sport', ['nhl', 'nba'])
def test_the_registry_discloses_both(sport):
    reg = registry(sport)
    said = ' '.join(reg['disclosures'])
    assert 'Model B did not train on a game of this season until 2026-11-05' in said
    assert f'the historical count, {HISTORICAL_PRICED[sport]})' in said
    assert "the backtest's market input is the closing price" in said
    (a,) = [x for x in reg['amendments'] if x['entry'] == 'disclosures' and x['date'] == '2026-11-05']
    assert a['before_any_result'] is False and 'No model, rule or figure changes' in a['change']


@pytest.mark.parametrize('sport', ['nhl', 'nba'])
def test_the_committed_picks_bear_the_disclosure_out(sport):
    """A postcondition over committed data: before 2026-11-05 every pick that
    carries a training record was fitted with exactly the historical priced
    rows; the count never falls in the order the picks were saved."""
    recs = [json.loads(p.read_text(encoding='utf-8')) for p in (ROOT / 'predictions' / sport / '2026').glob('*.json')]
    recs = sorted((r for r in recs if r.get('data_provenance')), key=lambda r: r['saved_utc'])
    assert recs
    before = [r for r in recs if r['saved_utc'] < FIRST_SEASON_PRICES]
    assert before and {r['data_provenance']['training_games_priced'] for r in before} == {HISTORICAL_PRICED[sport]}
    counts = [r['data_provenance']['training_games_priced'] for r in recs]
    assert counts == sorted(counts), 'training_games_priced fell between two saved picks'


def test_the_forward_file_names_its_market():
    f = a_file('nba')
    assert f['market_price'] == ft.MARKET_PRICE and f['market_price']['kind'] == 'lock'
    assert 'closing price' in f['market_price']['said']


@pytest.mark.skipif(NODE is None and not in_ci(), reason='node not installed')
@pytest.mark.parametrize('sport', ['nhl', 'nba'])
def test_both_pages_print_it_beside_the_forward_test(sport):
    html = render(sport, a_file(sport))
    assert ft.MARKET_PRICE['said'].replace("'", '&#39;') in html or ft.MARKET_PRICE['said'] in html
    f = a_file(sport)
    del f['market_price']
    assert 'closing price' not in render(sport, f), 'an older file without the key prints nothing'
