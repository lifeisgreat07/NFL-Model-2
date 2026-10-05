"""The NHL's per-game inputs: the market's price and the projected goalies,
each kept with where and when it was read.

Stage 55 item 3. Payloads are small and synthetic, in the shapes the
league's odds feed, Daily Faceoff's page and the league's box score had on
2026-10-05 (`docs/nhl-data.md`); no source content is committed.

Run with: pytest tests/test_nhl_inputs.py -v
"""
import json
import re
from datetime import UTC, datetime

import pandas as pd
import pytest

from src.sports.nhl import goalies, market, teams

READ = datetime(2026, 10, 5, 18, 0, tzinfo=UTC)
LATE = datetime(2026, 10, 5, 23, 30, tzinfo=UTC)


# --- clubs ------------------------------------------------------------------------

def test_every_club_is_known_by_abbreviation_and_by_full_name():
    assert len(teams.NAMES) == 32
    for abbr, name in teams.NAMES.items():
        assert teams.abbr_for(abbr) == abbr
        assert teams.abbr_for(name) == abbr


def test_spelling_differences_still_find_the_club_and_strangers_do_not():
    assert teams.abbr_for('Montreal Canadiens') == 'MTL'
    assert teams.abbr_for('St Louis Blues') == 'STL'
    assert teams.abbr_for('tampa bay lightning') == 'TBL'
    assert teams.abbr_for('Arizona Coyotes') is None
    assert teams.abbr_for('') is None


# --- the market ------------------------------------------------------------------

def odds_game(gid=2026020040, home=-218.0, away=180.0, start='2026-10-05T23:00:00Z'):
    def side(abbr, price):
        odds = [{'description': 'MONEY_LINE_3_WAY', 'value': 330.0, 'qualifier': 'Draw'},
                {'description': 'PUCK_LINE', 'value': 114.0, 'qualifier': '-1.5'}]
        if price is not None:
            odds.append({'description': 'MONEY_LINE_2_WAY', 'value': price, 'qualifier': ''})
        return {'abbrev': abbr, 'odds': odds}
    return {'gameId': gid, 'startTimeUTC': start, 'homeTeam': side('TBL', home), 'awayTeam': side('PHI', away)}


def feed(*games):
    return {'bettingPartner': {'name': 'DraftKings'}, 'games': list(games)}


def test_american_prices_become_probabilities():
    assert market.implied(-218) == pytest.approx(218 / 318)
    assert market.implied(180) == pytest.approx(100 / 280)
    assert market.implied(100) == pytest.approx(0.5)
    with pytest.raises(ValueError):
        market.implied(50)


def test_the_margin_comes_out_evenly_and_the_sides_are_not_swapped():
    p = market.no_vig_home(-218, 180)
    assert p == pytest.approx((218 / 318) / (218 / 318 + 100 / 280))
    assert p > 0.5  # the home favourite stays the favourite
    assert market.no_vig_home(180, -218) == pytest.approx(1 - p)


def test_the_two_way_line_is_read_and_the_three_way_one_is_not():
    rows, missing = market.parse(feed(odds_game()), READ)
    assert missing == []
    r = rows[0]
    assert (r['home'], r['away'], r['home_price'], r['away_price']) == ('TBL', 'PHI', -218.0, 180.0)
    assert r['book'] == 'DraftKings' and r['source'] == market.SOURCE
    assert r['read_utc'] == '2026-10-05T18:00:00Z' and r['game_id'] == '2026020040'


def test_a_game_without_both_prices_is_reported_not_filled_in():
    rows, missing = market.parse(feed(odds_game(away=None)), READ)
    assert rows == [] and 'no two-way moneyline' in missing[0]


def test_a_price_is_recorded_once_until_it_moves(tmp_path):
    path = tmp_path / 'lines.json'
    rows, _ = market.parse(feed(odds_game()), READ)
    assert market.record(rows, path) == 1
    assert market.record(rows, path) == 0
    moved, _ = market.parse(feed(odds_game(home=-230.0)), READ)
    assert market.record(moved, path) == 1
    kept = json.loads(path.read_text())
    assert [r['home_price'] for r in kept] == [-218.0, -230.0]


def test_a_price_read_after_the_start_is_never_recorded(tmp_path):
    path = tmp_path / 'lines.json'
    rows, _ = market.parse(feed(odds_game()), LATE)
    assert market.record(rows, path) == 0
    assert not path.exists()


# --- goalies --------------------------------------------------------------------------

def fo_game(home='Tampa Bay Lightning', away='Philadelphia Flyers', hl='Confirmed', al='Likely'):
    return {'homeTeamName': home, 'awayTeamName': away,
            'homeGoalieName': 'Home Goalie', 'awayGoalieName': 'Away Goalie',
            'homeNewsStrengthName': hl, 'awayNewsStrengthName': al,
            'homeNewsSourceUrl': 'https://example.com/h', 'awayNewsSourceUrl': None,
            'homeNewsDetails': 'prose that is not kept'}


def page(*games, day='2026-10-05'):
    payload = {'props': {'pageProps': {'date': day, 'data': list(games)}}}
    return f'<html><script id="__NEXT_DATA__" type="application/json">{json.dumps(payload)}</script></html>'


def test_a_projection_keeps_names_labels_and_the_report_link_only():
    (row,) = goalies.parse_faceoff(page(fo_game()), READ)
    assert (row['home'], row['away'], row['date']) == ('TBL', 'PHI', '2026-10-05')
    assert (row['home_status'], row['away_status']) == ('Confirmed', 'Likely')
    assert row['home_report'] == 'https://example.com/h'
    assert 'prose that is not kept' not in json.dumps(row)


def test_a_goalie_named_without_a_label_is_no_report_yet():
    (row,) = goalies.parse_faceoff(page(fo_game(hl=None)), READ)
    assert row['home_status'] is None and row['home_goalie'] == 'Home Goalie'


@pytest.mark.parametrize('bad, words', [
    (page(fo_game(home='Quebec Nordiques')), "unknown club 'Quebec Nordiques'"),
    (page(fo_game(al='Rumoured')), "unknown label 'Rumoured'"),
    ('<html>nothing here</html>', 'no __NEXT_DATA__'),
    (page(fo_game(), day=''), 'no games list or no date'),
])
def test_anything_unrecognised_on_the_page_stops_the_parse(bad, words):
    with pytest.raises(goalies.GoalieSourceError, match=re.escape(words)):
        goalies.parse_faceoff(bad, READ)


SLATE = [{'slate': '2026-10-05', 'home': 'TBL', 'away': 'PHI', 'game_id': '2026020040',
          'start_utc': pd.Timestamp('2026-10-05T23:00:00Z')}]


def test_a_projection_gets_the_league_game_and_its_start():
    (row,) = goalies.attach_games(goalies.parse_faceoff(page(fo_game()), READ), SLATE)
    assert row['game_id'] == '2026020040' and row['start_utc'] == '2026-10-05T23:00:00Z'


def test_a_projection_for_a_game_the_league_does_not_list_stops():
    rows = goalies.parse_faceoff(page(fo_game(home='Boston Bruins')), READ)
    with pytest.raises(goalies.GoalieSourceError, match='no league game for: PHI at BOS'):
        goalies.attach_games(rows, SLATE)


def test_a_projection_is_recorded_when_the_goalie_or_label_changes_and_not_after_the_start(tmp_path):
    path = tmp_path / 'goalies.json'
    first = goalies.attach_games(goalies.parse_faceoff(page(fo_game(hl=None)), READ), SLATE)
    assert goalies.record(first, path) == 1
    assert goalies.record(first, path) == 0
    confirmed = goalies.attach_games(goalies.parse_faceoff(page(fo_game()), READ), SLATE)
    assert goalies.record(confirmed, path) == 1
    late = goalies.attach_games(goalies.parse_faceoff(page(fo_game(al='Confirmed')), LATE), SLATE)
    assert goalies.record(late, path) == 0
    assert [r['home_status'] for r in json.loads(path.read_text())] == [None, 'Confirmed']


def box(home=(True, False), away=(True,)):
    def side(flags):
        return {'goalies': [{'playerId': 100 + i, 'name': {'default': f'G{i}'}, 'starter': f}
                            for i, f in enumerate(flags)]}
    return {'id': 2025020672, 'playerByGameStats': {'homeTeam': side(home), 'awayTeam': side(away)}}


def test_the_box_score_gives_each_side_its_one_starter():
    assert goalies.starters_from_boxscore(box()) == {
        'home': {'player_id': 100, 'name': 'G0'}, 'away': {'player_id': 100, 'name': 'G0'}}


@pytest.mark.parametrize('home', [(False, False), (True, True)])
def test_a_box_score_without_exactly_one_starter_stops(home):
    with pytest.raises(goalies.GoalieSourceError, match='starters flagged, not 1'):
        goalies.starters_from_boxscore(box(home=home))
