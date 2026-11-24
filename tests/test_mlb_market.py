"""MLB's market at the run that saves a pick (Stage 101 item 3): ESPN, then Kalshi, else no price, always named.

Every feed here is built by hand, so nothing is fetched.

Run with: pytest tests/test_mlb_market.py -v
"""
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest

from src.sports.mlb import market as m
from src.sports.mlb.teams import NAMES

ROOT = Path(__file__).resolve().parents[1]
REG = json.loads((ROOT / 'experiments/mlb/stage101/registry.json').read_text(encoding='utf-8'))
READ = datetime(2027, 4, 1, 16, 0, tzinfo=UTC)
NYY, BOS, TB = '147', '111', '139'


def odds(*items):
    return {'items': [{'provider': {'name': name}, 'homeTeamOdds': {'moneyLine': h}, 'awayTeamOdds': {'moneyLine': a}}
                      for name, h, a in items]}


def game(gid='1', home=NYY, away=BOS, number=1, dh='N', day='2027-04-01', start='2027-04-01 23:05'):
    return {'game_id': gid, 'home': home, 'away': away, 'game_number': number, 'double_header': dh, 'slate': day,
            'start_utc': pd.Timestamp(start, tz='UTC')}


def kalshi(*markets):
    return {'markets': [{'event_ticker': ev, 'ticker': f'{ev}-{code}', 'yes_bid_dollars': bid, 'yes_ask_dollars': ask}
                        for ev, code, bid, ask in markets]}


def test_espn_first_provider_that_is_a_book_with_the_margin_taken_out():
    got = m.espn_price(odds(('ESPN BET - Live Odds', -300, 250), ('AccuScore', -150, 130),
                            ('DraftKings', -150, 130), ('FanDuel', -110, -110)))
    assert got['provider'] == 'DraftKings' and (got['home_price'], got['away_price']) == (-150, 130)
    h, a = 150 / 250, 100 / 230
    assert got['home_prob'] == round(h / (h + a), 4)


def test_a_price_whose_sides_sum_outside_the_backtests_range_is_not_used():
    assert m.espn_price(odds(('DraftKings', -400, 350))) is not None  # sums to 1.022
    assert m.espn_price(odds(('Book', 100, 100))) is not None  # sums to 1.00 exactly: inside
    assert m.espn_price(odds(('Book', -300, -300))) is None  # sums to 1.50


def test_a_relocated_game_is_priced_for_the_stats_apis_home_club():
    got = m.espn_price(odds(('DraftKings', -150, 130)), swapped=True)
    assert (got['home_price'], got['away_price']) == (130, -150) and got['home_prob'] < 0.5


def test_espn_events_match_by_date_and_clubs_and_a_doubleheader_in_order():
    board = {'events': [
        {'id': 'b', 'date': '2027-04-01T23:05Z', 'competitions': [{'competitors': [
            {'homeAway': 'home', 'team': {'abbreviation': 'NYY'}}, {'homeAway': 'away', 'team': {'abbreviation': 'TB'}}]}]},
        {'id': 'a', 'date': '2027-04-01T17:05Z', 'competitions': [{'competitors': [
            {'homeAway': 'home', 'team': {'abbreviation': 'NYY'}}, {'homeAway': 'away', 'team': {'abbreviation': 'TB'}}]}]},
        {'id': 'c', 'date': '2027-04-01T23:10Z', 'competitions': [{'competitors': [
            {'homeAway': 'home', 'team': {'abbreviation': 'BOS'}}, {'homeAway': 'away', 'team': {'abbreviation': 'CHW'}}]}]},
    ]}
    games = pd.DataFrame([game('g2', NYY, TB, 2, 'Y'), game('g1', NYY, TB, 1, 'Y'), game('w', '145', BOS)])
    matched, missing = m.espn_match(games, m.espn_events(board))
    assert matched == {'g1': ('a', False), 'g2': ('b', False), 'w': ('c', True)} and missing == []


def test_a_game_espn_lists_a_different_number_of_times_is_left_unmatched():
    board = {'events': [{'id': 'a', 'date': '2027-04-01T17:05Z', 'competitions': [{'competitors': [
        {'homeAway': 'home', 'team': {'abbreviation': 'NYY'}}, {'homeAway': 'away', 'team': {'abbreviation': 'TB'}}]}]}]}
    games = pd.DataFrame([game('g1', NYY, TB, 1, 'Y'), game('g2', NYY, TB, 2, 'Y')])
    matched, missing = m.espn_match(games, m.espn_events(board))
    assert matched == {} and len(missing) == 2 and '1 ESPN events for 2 games' in missing[0]


def test_espns_codes_cover_every_club_and_kalshis_are_the_stats_apis_own():
    assert sorted(m.ESPN_CODES.values()) == sorted(NAMES) and len(m.ESPN_CODES) == 30
    assert m.KALSHI_CODES['AZ'] == '109' and m.KALSHI_CODES['CWS'] == '145' and len(m.KALSHI_CODES) == 30


def test_kalshi_tickers_name_the_date_and_a_doubleheaders_game():
    assert m.kalshi_date('KXMLBGAME-26OCT282000MILTB') == ('2026-10-28', None)
    assert m.kalshi_date('KXMLBGAME-26SEP221305TBNYYG1') == ('2026-09-22', 1)
    assert m.kalshi_date('KXMLBGAME-26SEP221905TBNYYG2') == ('2026-09-22', 2)
    assert m.kalshi_date('KXNBAGAME-26OCT21ATLORL') is None


def test_kalshi_prices_only_a_game_espn_did_not_and_says_so():
    feed = m.kalshi_prices(kalshi(('KXMLBGAME-27APR011905BOSNYY', 'NYY', 0.58, 0.62),
                                  ('KXMLBGAME-27APR011905BOSNYY', 'BOS', 0.38, 0.42)))
    espn = m.price_for(game(), odds(('DraftKings', -150, 130)), False, feed, READ)
    assert espn['source'] == 'espn'
    k = m.price_for(game(), odds(('AccuScore', -150, 130)), False, feed, READ)
    assert (k['source'], k['provider'], k['home_price'], k['away_price']) == ('kalshi', 'Kalshi', 0.6, 0.4)
    assert k['home_prob'] == 0.6 and k['start_utc'] == '2027-04-01T23:05:00Z'


def test_kalshi_needs_both_sides_quoted():
    feed = m.kalshi_prices(kalshi(('KXMLBGAME-27APR011905BOSNYY', 'NYY', 0.58, 0.62),
                                  ('KXMLBGAME-27APR011905BOSNYY', 'BOS', 0, 0.42)))
    assert feed == {}
    none = m.price_for(game(), None, False, feed, READ)
    assert none['source'] is None and none['home_prob'] is None
    assert none['why'] == 'ESPN odds not read; Kalshi lists no quoted market for the game'


def test_a_doubleheader_game_takes_its_own_kalshi_market():
    feed = m.kalshi_prices(kalshi(('KXMLBGAME-27APR011305TBNYYG1', 'NYY', 0.50, 0.52),
                                  ('KXMLBGAME-27APR011305TBNYYG1', 'TB', 0.48, 0.50),
                                  ('KXMLBGAME-27APR011905TBNYYG2', 'NYY', 0.60, 0.62),
                                  ('KXMLBGAME-27APR011905TBNYYG2', 'TB', 0.38, 0.40)))
    g2 = m.price_for(game('g2', NYY, TB, 2, 'Y'), None, False, feed, READ)
    assert g2['home_price'] == 0.61
    single = m.price_for(game('s', NYY, TB), None, False, feed, READ)
    assert single['source'] is None


def test_neither_read_is_no_price_with_both_reasons():
    got = m.price_for(game(), odds(('Book', -300, -300)), False, None, READ)
    assert got['source'] is None and got['why'] == 'ESPN has no usable pre-game price; Kalshi not read'


def test_the_record_keeps_a_row_only_when_the_price_moves_and_never_after_the_start(tmp_path):
    path = tmp_path / 'lines' / '2027.json'
    a = m.price_for(game(), odds(('DraftKings', -150, 130)), False, None, READ)
    assert m.record([a], path) == 1 and m.record([a], path) == 0
    moved = m.price_for(game(), odds(('DraftKings', -160, 140)), False, None, READ)
    late = m.price_for(game('2'), odds(('DraftKings', -160, 140)), False, None, datetime(2027, 4, 2, tzinfo=UTC))
    unpriced = m.price_for(game('3'), None, False, None, READ)
    assert m.record([moved, late, unpriced], path) == 1
    assert [r['home_price'] for r in json.loads(path.read_text(encoding='utf-8'))] == [-150, -160]


def test_the_market_is_the_registered_one():
    market = REG['market']
    assert 'AccuScore' in market['primary'] and '1.00 and 1.20' in market['primary'] and 'accuscore' in m.EXCLUDED
    assert m.SUM_RANGE == (1.00, 1.20)
    assert 'KXMLBGAME' in market['fallback'] and 'series_ticker=KXMLBGAME' in m.KALSHI
    assert "'no price'" in market['none'] and 'data/mlb/lines/<season>.json' in market['record']


def test_not_an_american_price():
    with pytest.raises(ValueError):
        m.implied(50)
