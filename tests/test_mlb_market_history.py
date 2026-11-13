"""MLB's market history (Stage 99 item 2): ESPN's pre-game moneyline matched to the Stats API's finals, as
experiments/mlb/stage98/registry.json's data.market says. Every board and price here is built by hand.

Run with: pytest tests/test_mlb_market_history.py -v
"""
import pandas as pd
import pytest

from src.sports.mlb import market_history as mh


def board(*games):
    evs = []
    for eid, home, away, hs, as_, done in games:
        evs.append({'id': eid, 'competitions': [{
            'status': {'type': {'completed': done}},
            'competitors': [{'homeAway': 'home', 'team': {'abbreviation': home}, 'score': str(hs)},
                            {'homeAway': 'away', 'team': {'abbreviation': away}, 'score': str(as_)}]}]})
    return {'events': evs}


def finals():
    return pd.DataFrame([
        {'game_id': '1', 'slate': '2025-07-04', 'home': '147', 'away': '111', 'home_score': 5, 'away_score': 3},
        {'game_id': '2', 'slate': '2025-07-05', 'home': '111', 'away': '147', 'home_score': 2, 'away_score': 7},
        {'game_id': '3', 'slate': '2025-07-06', 'home': '147', 'away': '111', 'home_score': 4, 'away_score': 1},
    ])


def espn(rows):
    return pd.DataFrame(rows, columns=['slate', 'espn_id', 'home', 'away', 'home_score', 'away_score'])


def test_only_completed_events_are_read():
    got = mh.events(board(('9', 'NYY', 'BOS', 5, 3, True), ('8', 'NYY', 'BOS', 0, 0, False)))
    assert [e['espn_id'] for e in got] == ['9']


def test_codes_are_learned_and_a_relocated_game_is_matched_with_its_sides_swapped():
    e = espn([('2025-07-04', 'a', 'NYY', 'BOS', 5, 3), ('2025-07-05', 'b', 'BOS', 'NYY', 2, 7),
              ('2025-07-06', 'c', 'BOS', 'NYY', 1, 4)])
    codes = mh.code_map(e, finals())
    assert codes == {'NYY': '147', 'BOS': '111'}
    matched, missing = mh.match(e, finals(), codes)
    assert matched == {'1': ('a', False), '2': ('b', False), '3': ('c', True)} and missing == []


def test_a_final_espn_does_not_list_is_named_not_guessed():
    e = espn([('2025-07-04', 'a', 'NYY', 'BOS', 5, 3), ('2025-07-05', 'b', 'BOS', 'NYY', 2, 7)])
    _, missing = mh.match(e, finals(), {'NYY': '147', 'BOS': '111'})
    assert missing == ['game 3 (2025-07-06): 0 ESPN events']


def odds(provider, home, away, close=None):
    item = {'provider': {'name': provider}, 'homeTeamOdds': {'moneyLine': home}, 'awayTeamOdds': {'moneyLine': away}}
    if close:
        item['homeTeamOdds']['close'] = {'moneyLine': {'american': close[0]}}
        item['awayTeamOdds']['close'] = {'moneyLine': {'american': close[1]}}
    return item


def test_the_closing_price_wins_and_a_live_provider_is_never_used():
    o = {'items': [odds('ESPN BET Live Odds', -300, 250), odds('ESPN BET', -150, 130, close=(-160, 140))]}
    row = mh.market_row(o, '1', 2025, 'a', False)
    assert (row['provider'], row['home_price'], row['away_price'], row['closing']) == ('ESPN BET', -160.0, 140.0, True)
    assert row['home_prob'] == pytest.approx((160 / 260) / (160 / 260 + 100 / 240), abs=1e-6)


def test_a_swapped_game_gets_the_stats_api_home_clubs_probability():
    o = {'items': [odds('ESPN BET', -150, 130)]}
    plain, swapped = mh.market_row(o, '1', 2025, 'a', False), mh.market_row(o, '1', 2025, 'a', True)
    assert swapped['home_prob'] == pytest.approx(1 - plain['home_prob'])
    assert (swapped['home_price'], swapped['away_price'], swapped['swapped']) == (130.0, -150.0, True)


def test_no_usable_price_gives_no_row():
    assert mh.market_row({'items': [odds('ESPN BET', 0, 0)]}, '1', 2025, 'a', False) is None
