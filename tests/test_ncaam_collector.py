"""Men's college results collector (Stage 103 item 1): each final game stored once, with when it was read.

Every scoreboard here is built by hand, so nothing is fetched.

Run with: pytest tests/test_ncaam_collector.py -v
"""
import json
from datetime import UTC, date, datetime

import pytest

from src.sports.ncaam import collector as c

NOW = datetime(2026, 11, 13, 13, 30, tzinfo=UTC)


def event(gid, home=('248', 'HOU'), away=('2', 'AUB'), hs='70', as_='65', done=True, neutral=False,
          tournament=None, note=None):
    comp = {'status': {'type': {'completed': done}}, 'neutralSite': neutral, 'conferenceCompetition': False,
            'competitors': [{'homeAway': 'home', 'team': {'id': home[0], 'abbreviation': home[1]}, 'score': hs},
                            {'homeAway': 'away', 'team': {'id': away[0], 'abbreviation': away[1]}, 'score': as_}]}
    if tournament:
        comp['tournamentId'] = tournament
    if note:
        comp['notes'] = [{'type': 'event', 'headline': note}]
    return {'id': gid, 'date': '2026-11-12T23:00Z', 'competitions': [comp]}


def test_a_final_game_is_one_row_with_when_it_was_read():
    [row] = c.finals({'events': [event('1'), event('2', done=False)]}, date(2026, 11, 12), NOW)
    assert (row['game_id'], row['season'], row['day'], row['home_id'], row['away_id']) == (
        '1', 2026, '2026-11-12', '248', '2')
    assert (row['home_score'], row['away_score'], row['read_utc']) == (70, 65, '2026-11-13T13:30:00Z')


def test_a_tournament_game_keeps_its_id_note_and_neutral_site():
    [row] = c.finals({'events': [event('3', neutral=True, tournament='22', note='Midwest Region - 1st Round')]},
                     date(2027, 3, 18), NOW)
    assert (row['neutral_site'], row['tournament_id'], row['note'], row['season']) == (
        True, '22', 'Midwest Region - 1st Round', 2026)


def test_a_final_without_a_winner_or_two_clubs_stops_the_run_naming_each():
    board = {'events': [event('4', hs='60', as_='60'), event('5', away=('248', 'HOU')), event('6')]}
    with pytest.raises(c.CollectorError) as e:
        c.finals(board, date(2026, 11, 12), NOW)
    assert 'game 4' in str(e.value) and 'game 5' in str(e.value) and 'game 6' not in str(e.value)


def test_the_season_is_labelled_by_the_year_it_starts():
    assert c.season_of(date(2026, 11, 3)) == 2026
    assert c.season_of(date(2027, 4, 5)) == 2026
    assert c.season_of(date(2027, 8, 1)) == 2027


def test_a_stored_game_is_never_written_twice(tmp_path):
    rows = c.finals({'events': [event('1'), event('2')]}, date(2026, 11, 12), NOW)
    assert c.add(rows, tmp_path) == 2
    later = c.finals({'events': [event('1', hs='99'), event('7')]}, date(2026, 11, 12), NOW)
    assert c.add(later, tmp_path) == 1
    stored = c.stored(tmp_path / 'games_2026.csv')
    assert list(stored['game_id']) == ['1', '2', '7'] and stored.loc[0, 'home_score'] == '70'


def test_the_run_reads_one_scoreboard_a_day_and_defaults_to_the_last_three(tmp_path, monkeypatch):
    asked = []

    def get(url):
        asked.append(url.split('dates=')[1][:8])
        return json.dumps({'events': [event(url.split('dates=')[1][:8])]}).encode()
    monkeypatch.setattr(c, 'HISTORY', tmp_path)
    monkeypatch.setattr(c, 'collect', lambda days, now, get, folder=tmp_path, pause=0: c.add(
        [r for d in days for r in c.finals(json.loads(get(c.SCOREBOARD.format(day=d.strftime('%Y%m%d')))), d, now)],
        folder))
    assert c.main([], now=NOW, get=get) == 0
    assert asked == ['20261110', '20261111', '20261112']
