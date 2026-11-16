"""The market for NCAA tournament games (Stage 103 item 2), on odds built by hand.

Run with: pytest tests/test_ncaam_market.py -v
"""
import json
from datetime import UTC, datetime

import pandas as pd
import pytest

from src.sports.ncaam import market as m

BOOKS, NOT_BOOKS = ['DraftKings', 'MGM', 'Unibet'], ['accuscore', 'consensus']


def item(provider, home=None, away=None, close=None):
    h, a = {'moneyLine': home}, {'moneyLine': away}
    if close:
        h['close'], a['close'] = {'moneyLine': {'american': close[0]}}, {'moneyLine': {'american': close[1]}}
    return {'provider': {'name': provider}, 'homeTeamOdds': h, 'awayTeamOdds': a}


def rows(*items, game='g1'):
    return pd.DataFrame(m.provider_rows({'items': list(items)}, game, 2024, 'x'), columns=list(m.MARKET_FIELDS))


def probs(*items):
    out, unknown = m.home_probs(rows(*items), BOOKS, NOT_BOOKS)
    return out.set_index('game_id'), unknown


def test_a_price_has_its_margin_taken_out_evenly():
    out, _ = probs(item('DraftKings', -150, 130))
    want = (150 / 250) / (150 / 250 + 100 / 230)
    assert out.loc['g1', 'home_prob'] == pytest.approx(want) and out.loc['g1', 'books'] == 1


def test_the_closing_price_is_used_where_espn_gives_one():
    out, _ = probs(item('DraftKings', -300, 250, close=('-150', '+130')))
    listed, _ = probs(item('DraftKings', -150, 130))
    assert out.loc['g1', 'home_prob'] == pytest.approx(listed.loc['g1', 'home_prob'])
    half, _ = probs(item('DraftKings', -150, 130, close=('-300', None)))
    assert half.loc['g1', 'home_prob'] == pytest.approx(listed.loc['g1', 'home_prob']), 'half a close is no close'


def test_the_market_is_the_median_of_the_books():
    out, _ = probs(item('DraftKings', -110, -110), item('MGM', -200, 170), item('Unibet', -400, 320))
    middle, _ = probs(item('MGM', -200, 170))
    assert out.loc['g1', 'home_prob'] == pytest.approx(middle.loc['g1', 'home_prob']) and out.loc['g1', 'books'] == 3
    two, _ = probs(item('DraftKings', -110, -110), item('MGM', -200, 170))
    assert two.loc['g1', 'home_prob'] == pytest.approx((0.5 + middle.loc['g1', 'home_prob']) / 2)


def test_a_live_feed_a_model_and_an_unknown_provider_are_never_the_market():
    out, unknown = probs(item('DraftKings - Live Odds', -900, 600), item('accuscore', -900, 600),
                         item('NewBook', -900, 600), item('MGM', -110, -110))
    assert out.loc['g1', 'home_prob'] == pytest.approx(0.5) and out.loc['g1', 'books'] == 1
    assert unknown == ['NewBook'], 'named, so an amendment can classify it'
    none, _ = probs(item('consensus', -150, 130))
    assert none.empty, 'a game with no book has no market'


def test_an_incoherent_price_and_a_missing_one_are_not_used():
    out, _ = probs(item('DraftKings', -400, -400), item('MGM', 150, 150), item('Unibet', None, 130))
    assert out.empty
    assert m._num('EVEN') == 100.0 and m._num('+120') == 120.0 and m._num(0) is None and m._num(None) is None
    edge, _ = probs(item('DraftKings', -150, -150))  # implied sum exactly 1.20
    assert len(edge) == 1


def test_every_listed_provider_is_stored_as_read_and_the_file_is_read_back(tmp_path):
    (tmp_path / 'games_2024.csv').write_text(
        'game_id,tournament_id\n7,22\n8,\n9,22\n', encoding='utf-8')
    asked = []

    def get(url):
        asked.append(url)
        return json.dumps({'items': [item('accuscore', -500, 400), item('MGM', -120, 100, close=('-130', 'EVEN'))]}
                          ).encode()

    df = m.season_market(2024, datetime(2026, 11, 15, tzinfo=UTC), get, tmp_path, pause=0)
    assert asked == [m.ODDS.format(e='7'), m.ODDS.format(e='9')], 'tournament games only'
    assert list(df['provider']) == ['accuscore', 'MGM'] * 2 and set(df['read_utc']) == {'2026-11-15T00:00:00Z'}
    m.write(df, tmp_path / 'market_2024.csv')
    out, unknown = m.load([2024], BOOKS, NOT_BOOKS, tmp_path)
    want = (130 / 230) / (130 / 230 + 0.5)
    assert list(out['game_id']) == ['7', '9'] and out['home_prob'].tolist() == pytest.approx([want, want])
    with pytest.raises(FileNotFoundError):
        m.load([2023], BOOKS, NOT_BOOKS, tmp_path)
