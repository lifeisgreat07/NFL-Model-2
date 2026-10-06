"""The NBA's schedule loader: every game ESPN lists, in the core's shape, or
a stop that names what it did not recognise.

The games here are small synthetic payloads in ESPN's scoreboard shape, so
no ESPN content is committed; `docs/nba-data.md` records what the real
scoreboard returned.

Run with: pytest tests/test_nba_schedule.py -v
"""
from datetime import UTC, datetime

import pandas as pd
import pytest

from src.core.sport import SCHEDULE_COLUMNS, check_schedule
from src.sports.nba import schedule as nba

SEASON = 2026


def event(gid='401800001', home='BOS', away='NY', status='STATUS_SCHEDULED', season_type=2,
          kind='STD', start='2026-10-21T23:30Z', scores=None, year=SEASON + 1, neutral=False):
    sides = []
    for side, abbr, score in (('home', home, scores[0] if scores else None),
                              ('away', away, scores[1] if scores else None)):
        c = {'homeAway': side, 'team': {'abbreviation': abbr}}
        if score is not None:
            c['score'] = str(score)
        sides.append(c)
    return {'id': gid, 'date': start, 'season': {'year': year, 'type': season_type},
            'competitions': [{'type': {'abbreviation': kind}, 'neutralSite': neutral,
                              'venue': {'fullName': 'Arena'}, 'competitors': sides,
                              'status': {'type': {'name': status}}}]}


def final(gid='401800002', home='BOS', away='NY', scores=(110, 104), **over):
    return event(gid=gid, home=home, away=away, status='STATUS_FINAL', scores=scores, **over)


def board(events=(), days=('2026-10-21T07:00Z',)):
    return {'leagues': [{'calendar': list(days)}], 'events': list(events)}


# --- statuses ---------------------------------------------------------------

@pytest.mark.parametrize('name, status', [
    ('STATUS_SCHEDULED', 'scheduled'), ('STATUS_IN_PROGRESS', 'in_progress'),
    ('STATUS_HALFTIME', 'in_progress'), ('STATUS_FINAL', 'final'),
    ('STATUS_POSTPONED', 'postponed'), ('STATUS_CANCELED', 'cancelled'),
])
def test_each_espn_status_maps_to_one_core_status(name, status):
    ev = final() if status == 'final' else event(status=name)
    df = nba.to_schedule([('2026-10-21', ev)], SEASON)
    assert df.loc[0, 'status'] == status


def test_an_unknown_status_stops_the_load():
    with pytest.raises(nba.NBAScheduleError, match='unknown status'):
        nba.to_schedule([('2026-10-21', event(status='STATUS_RAIN_DELAY'))], SEASON)


def test_a_postponed_game_keeps_no_score():
    ev = event(status='STATUS_POSTPONED', scores=(0, 0))
    df = nba.to_schedule([('2021-12-20', ev)], SEASON)
    assert df.loc[0, 'status'] == 'postponed' and pd.isna(df.loc[0, 'home_score'])


# --- which games -------------------------------------------------------------

def test_all_star_games_are_left_out_though_espn_files_them_as_regular_season():
    assert nba.kept(event(kind='STD'))
    assert not nba.kept(event(kind='ALLSTAR', season_type=2))


def test_preseason_is_left_out_and_play_in_and_playoffs_are_kept():
    assert not nba.kept(event(season_type=1))
    assert nba.kept(event(season_type=5)) and nba.kept(event(season_type=3))
    df = nba.to_schedule([('2026-04-14', final(season_type=5)), ('2026-04-20', final(gid='9', season_type=3))], SEASON)
    assert sorted(df['game_type']) == ['playin', 'playoff']


def test_the_cup_final_is_kept_as_a_neutral_site_regular_season_game():
    df = nba.to_schedule([('2026-12-16', final(kind='CC', neutral=True))], SEASON)
    assert (df.loc[0, 'game_type'], bool(df.loc[0, 'neutral_site'])) == ('regular', True)


def test_a_game_whose_teams_are_not_known_yet_is_left_out_until_they_are():
    assert not nba.kept(event(home='TBD', away='TBD'))
    assert not nba.kept(event(home='BOS', away='TBD', kind='QTR'))
    assert nba.kept(event(home='BOS', away='NY', kind='QTR'))
    assert nba.kept(final(home='BOS', away='TBD')), 'a finished game is never a placeholder'
    with pytest.raises(nba.NBAScheduleError, match='not two teams'):
        nba.to_schedule([('2026-12-09', final(home='TBD', away='TBD'))], SEASON)


def test_an_unknown_competition_type_stops_the_load():
    with pytest.raises(nba.NBAScheduleError, match='unknown competition type'):
        nba.to_schedule([('2026-10-21', event(kind='EXHIB'))], SEASON)


# --- the rows ------------------------------------------------------------------

def test_the_frame_meets_the_core_contract_and_counts_overtime_wins():
    df = nba.to_schedule([('2026-10-21', final(scores=(120, 118))), ('2026-10-21', event(gid='3'))], SEASON)
    assert list(df.columns[:len(SCHEDULE_COLUMNS)]) == list(SCHEDULE_COLUMNS)
    assert check_schedule('nba', df) == []
    row = df[df['game_id'] == '401800002'].iloc[0]
    assert (row['home_score'], row['away_score'], row['home_win']) == (120, 118, 1)
    assert pd.isna(df[df['game_id'] == '3'].iloc[0]['home_win'])


def test_a_tied_final_or_a_missing_score_stops_the_load():
    with pytest.raises(nba.NBAScheduleError, match='tied score'):
        nba.to_schedule([('2026-10-21', final(scores=(100, 100)))], SEASON)
    ev = final()
    del ev['competitions'][0]['competitors'][1]['score']
    with pytest.raises(nba.NBAScheduleError, match='without both scores'):
        nba.to_schedule([('2026-10-21', ev)], SEASON)


def test_a_start_that_is_not_utc_stops_the_load():
    with pytest.raises(nba.NBAScheduleError, match='not UTC'):
        nba.to_schedule([('2026-10-21', event(start='2026-10-21T19:30-04:00'))], SEASON)


def test_one_team_twice_stops_the_load():
    with pytest.raises(nba.NBAScheduleError, match='not two teams'):
        nba.to_schedule([('2026-10-21', event(home='BOS', away='BOS'))], SEASON)


# --- reading a season -------------------------------------------------------------

def test_a_season_is_read_along_its_calendar_and_a_moved_game_keeps_its_later_date():
    moved = event(gid='7', status='STATUS_POSTPONED')
    replayed = final(gid='7')
    pages = {
        nba.SCOREBOARD.format(day='20270115'): board(days=['2026-10-21T07:00Z', '2026-10-22T07:00Z']),
        nba.SCOREBOARD.format(day='20261021'): board([moved, final(gid='1'), event(gid='2', kind='ALLSTAR')]),
        nba.SCOREBOARD.format(day='20261022'): board([replayed, event(gid='8', year=SEASON)]),
    }
    games = nba.season_games(SEASON, pages.__getitem__)
    assert [(day, ev['id']) for day, ev in games] == [('2026-10-21', '1'), ('2026-10-22', '7')]


def test_a_scoreboard_without_a_calendar_stops_the_load():
    with pytest.raises(nba.NBAScheduleError, match='no calendar'):
        nba.calendar({'leagues': [{}]})


def test_only_a_finished_earlier_season_is_cached(tmp_path, monkeypatch):
    calls = []

    def get(url):
        calls.append(url)
        if url.endswith('20260115&limit=1000'):
            return board(days=['2025-10-21T07:00Z'])
        return board([final(gid='1', year=2026)])

    now = datetime(2026, 10, 6, tzinfo=UTC)
    first = nba.load_schedule(2025, get, cache=tmp_path, now=now)
    again = nba.load_schedule(2025, get, cache=tmp_path, now=now)
    assert len(calls) == 2 and (tmp_path / 'schedule_2025.parquet').exists()
    pd.testing.assert_frame_equal(first, again)
    # The current season is never cached, even with every game it lists
    # final: it is still being played, so tomorrow's read must refetch it.
    nba.load_schedule(2026, lambda u: board(days=['2026-10-21T07:00Z']) if '0115' in u else board([final(gid='5')]),
                      cache=tmp_path, now=now)
    assert not (tmp_path / 'schedule_2026.parquet').exists()


def test_the_calendar_is_read_from_a_date_every_season_has_reached():
    assert nba.calendar_day(2020) == '20210115', '2020-21 began on 22 December 2020'


def test_the_season_turns_over_in_october():
    assert nba.current_season(datetime(2026, 9, 30, tzinfo=UTC)) == 2025
    assert nba.current_season(datetime(2026, 10, 1, tzinfo=UTC)) == 2026
