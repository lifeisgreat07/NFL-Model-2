"""The NBA's live market price (Stage 65): ESPN first, Kalshi only when ESPN
has none, and otherwise no price, always named.

Fixtures are cut down from real reads saved on 2026-10-09 (ESPN's odds for
opening night's ATL at ORL, and Kalshi's preseason game markets).

Run with: pytest tests/test_nba_market.py -v
"""
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from src.sports.nba import market

ROOT = Path(__file__).resolve().parents[1]
REG = json.loads((ROOT / 'experiments/nba/stage65/registry.json').read_text(encoding='utf-8'))
READ = datetime(2026, 10, 21, 21, 30, tzinfo=UTC)
GAME = {'game_id': '401909834', 'slate': '2026-10-21', 'home': 'ORL', 'away': 'ATL',
        'start_utc': '2026-10-21T23:00:00Z'}


def espn(*items):
    return {'items': list(items)}


def item(provider, home, away):
    return {'provider': {'name': provider}, 'homeTeamOdds': {'moneyLine': home}, 'awayTeamOdds': {'moneyLine': away}}


def kalshi_market(event, code, bid, ask):
    return {'event_ticker': event, 'ticker': f'{event}-{code}', 'yes_bid_dollars': f'{bid:.4f}',
            'yes_ask_dollars': f'{ask:.4f}'}


def kalshi(*markets):
    return market.kalshi_prices({'markets': list(markets)})


def test_the_spread_limit_is_the_registered_one():
    assert f'at most {market.KALSHI_MAX_SPREAD:.2f}' in REG['market']['fallback']


def test_espn_is_read_at_its_current_moneyline_with_the_margin_taken_out():
    p = market.price_for(GAME, espn(item('DraftKings', -130, 110)), None, READ)
    h, a = 130 / 230, 100 / 210
    assert p['source'] == 'espn' and p['provider'] == 'DraftKings'
    assert p['home_prob'] == round(h / (h + a), 4) == 0.5427
    assert (p['home_price'], p['away_price']) == (-130, 110)


def test_live_and_projection_providers_are_skipped():
    p = market.espn_price(espn(item('ESPN BET - Live Odds', -500, 400), item('numberfire', -200, 170),
                               item('DraftKings', -130, 110)))
    assert p['provider'] == 'DraftKings'


def test_a_zero_price_from_espn_is_no_price():
    assert market.espn_price(espn(item('DraftKings', 0, 0))) is None


def test_kalshi_is_never_read_when_espn_has_a_price():
    """Even a tight Kalshi market does not replace ESPN's."""
    k = kalshi(kalshi_market('KXNBAGAME-26OCT21ATLORL', 'ORL', 0.60, 0.61),
               kalshi_market('KXNBAGAME-26OCT21ATLORL', 'ATL', 0.39, 0.40))
    assert market.price_for(GAME, espn(item('DraftKings', -130, 110)), k, READ)['source'] == 'espn'


def test_kalshi_prices_a_game_espn_does_not_by_midpoints_matched_on_the_pair():
    k = kalshi(kalshi_market('KXNBAGAME-26OCT21ATLORL', 'ORL', 0.56, 0.58),
               kalshi_market('KXNBAGAME-26OCT21ATLORL', 'ATL', 0.42, 0.44))
    p = market.price_for(GAME, espn(), k, READ)
    assert p['source'] == 'kalshi' and (p['home_price'], p['away_price']) == (0.57, 0.43)
    assert p['home_prob'] == 0.57


def test_kalshi_codes_are_mapped_to_espns():
    game = {**GAME, 'home': 'NY', 'away': 'GS'}
    k = kalshi(kalshi_market('KXNBAGAME-26OCT21GSWNYK', 'NYK', 0.50, 0.52),
               kalshi_market('KXNBAGAME-26OCT21GSWNYK', 'GSW', 0.48, 0.50))
    assert market.price_for(game, None, k, READ)['source'] == 'kalshi'


@pytest.mark.parametrize('spread', [0.06, 0.64])
def test_a_wide_kalshi_market_is_no_price(spread):
    """0.64 is a real preseason quote (0.15 bid, 0.79 ask)."""
    k = kalshi(kalshi_market('KXNBAGAME-26OCT21ATLORL', 'ORL', 0.15, 0.15 + spread),
               kalshi_market('KXNBAGAME-26OCT21ATLORL', 'ATL', 0.40, 0.41))
    p = market.price_for(GAME, espn(), k, READ)
    assert p['source'] is None and p['home_prob'] is None and 'wider than 0.05' in p['why']


def test_a_spread_of_exactly_the_limit_is_accepted():
    k = kalshi(kalshi_market('KXNBAGAME-26OCT21ATLORL', 'ORL', 0.55, 0.60),
               kalshi_market('KXNBAGAME-26OCT21ATLORL', 'ATL', 0.40, 0.45))
    assert market.price_for(GAME, espn(), k, READ)['source'] == 'kalshi'


def test_a_one_sided_or_unquoted_kalshi_market_is_no_price():
    k = kalshi(kalshi_market('KXNBAGAME-26OCT21ATLORL', 'ORL', 0.56, 0.58),
               kalshi_market('KXNBAGAME-26OCT21ATLORL', 'ATL', 0.0, 0.44))
    assert market.price_for(GAME, espn(), k, READ)['source'] is None


def test_kalshi_on_another_date_is_not_this_game():
    k = kalshi(kalshi_market('KXNBAGAME-26OCT22ATLORL', 'ORL', 0.56, 0.58),
               kalshi_market('KXNBAGAME-26OCT22ATLORL', 'ATL', 0.42, 0.44))
    p = market.price_for(GAME, espn(), k, READ)
    assert p['source'] is None and 'no quoted market' in p['why']


def test_no_price_names_every_reason():
    p = market.price_for(GAME, None, None, READ)
    assert p['source'] is None and p['why'] == 'ESPN odds not read; Kalshi not read'


def test_the_real_preseason_kalshi_quotes_would_all_be_refused():
    """Every game in the saved 2026-10-09 read has a side wider than 0.05."""
    feed = {'markets': [
        kalshi_market('KXNBAGAME-26OCT15OKCHOU', 'OKC', 0.15, 0.79),
        kalshi_market('KXNBAGAME-26OCT15OKCHOU', 'HOU', 0.21, 0.84)]}
    k = market.kalshi_prices(feed)
    game = {**GAME, 'slate': '2026-10-15', 'home': 'HOU', 'away': 'OKC'}
    assert market.price_for(game, espn(), k, READ)['source'] is None


def test_record_adds_only_moves_and_nothing_after_the_start(tmp_path):
    path = tmp_path / 'lines.json'
    p = market.price_for(GAME, espn(item('DraftKings', -130, 110)), None, READ)
    assert market.record([p], path) == 1
    assert market.record([p], path) == 0
    moved = {**p, 'home_price': -140}
    late = {**moved, 'home_price': -150, 'read_utc': '2026-10-21T23:05:00Z'}
    none = market.price_for(GAME, None, None, READ)
    assert market.record([moved, late, none], path) == 1
    assert [r['home_price'] for r in json.loads(path.read_text())] == [-130, -140]
