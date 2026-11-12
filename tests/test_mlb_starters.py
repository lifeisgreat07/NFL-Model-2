"""MLB's starters, probable and confirmed (Stage 98 item 3): every read kept, with where and when it was made.

Run with: pytest tests/test_mlb_starters.py -v
"""
from datetime import UTC, datetime, timedelta, timezone

import pytest

from src.sports.mlb import starters
from tests.test_mlb_schedule import game

T0 = datetime(2027, 4, 1, 14, 0, tzinfo=UTC)
SRC = 'https://statsapi.mlb.com/api/v1/schedule?date=2027-04-01'


def day(home_pitcher=500, away_pitcher=None, **kw):
    g = game(pk=9, coded='S', hs=None, as_=None, **kw)
    if home_pitcher:
        g['teams']['home']['probablePitcher'] = {'id': home_pitcher}
    if away_pitcher:
        g['teams']['away']['probablePitcher'] = {'id': away_pitcher}
    return {'dates': [{'games': [g]}]}


def test_a_probable_row_per_club_with_where_and_when():
    rows = starters.probable_rows(day(), SRC, T0)
    assert [(r['side'], r['club'], r['pitcher_id']) for r in rows] == [('home', '147', '500'), ('away', '111', None)]
    assert {r['kind'] for r in rows} == {'probable'} and {r['source'] for r in rows} == {SRC}
    assert {r['read_at'] for r in rows} == {'2027-04-01T14:00:00+00:00'}


def test_read_at_must_carry_a_time_zone_and_is_stored_in_utc():
    with pytest.raises(starters.StarterError):
        starters.probable_rows(day(), SRC, datetime(2027, 4, 1, 14, 0))
    east = datetime(2027, 4, 1, 10, 0, tzinfo=timezone(timedelta(hours=-4)))
    assert starters.probable_rows(day(), SRC, east)[0]['read_at'] == '2027-04-01T14:00:00+00:00'


def test_spring_training_has_no_rows():
    assert starters.probable_rows(day(gtype='S'), SRC, T0) == []


def test_the_confirmed_starter_is_the_first_pitcher_each_box_lists():
    box = {'teams': {'home': {'team': {'id': 147}, 'pitchers': [501, 600]},
                     'away': {'team': {'id': 111}, 'pitchers': [700, 701]}}}
    rows = starters.confirmed_rows(box, '9', 'box', T0)
    assert [(r['side'], r['pitcher_id'], r['kind']) for r in rows] == [('home', '501', 'confirmed'),
                                                                        ('away', '700', 'confirmed')]
    box['teams']['away']['pitchers'] = []
    with pytest.raises(starters.StarterError, match='no pitcher'):
        starters.confirmed_rows(box, '9', 'box', T0)


def test_append_keeps_every_earlier_read_and_adds_only_changes(tmp_path):
    path = tmp_path / 'starters.csv'
    assert starters.append(path, starters.probable_rows(day(), SRC, T0)) == 2
    assert starters.append(path, starters.probable_rows(day(), SRC, T0 + timedelta(hours=3))) == 0
    later = starters.probable_rows(day(home_pitcher=502, away_pitcher=700), SRC, T0 + timedelta(hours=6))
    assert starters.append(path, later) == 2
    got = starters.read(path)
    assert list(got['pitcher_id']) == ['500', None, '502', '700']
    assert list(got['read_at'])[:2] == ['2027-04-01T14:00:00+00:00'] * 2, 'the first read is still there'


def test_an_unknown_kind_is_refused(tmp_path):
    row = starters.probable_rows(day(), SRC, T0)[0] | {'kind': 'guessed'}
    with pytest.raises(starters.StarterError, match='unknown kind'):
        starters.append(tmp_path / 's.csv', [row])
