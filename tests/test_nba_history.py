"""The NBA's history: box-score rows, player minutes, possessions, the
fallback floor and the market's price, on small synthetic payloads in
ESPN's shape.

Run with: pytest tests/test_nba_history.py -v
"""
from types import SimpleNamespace

import pandas as pd
import pytest

from src.sports.nba import history as h


def team(side, abbr, fg='40-88', ft='20-25', oreb='10', tov='14'):
    return {'homeAway': side, 'team': {'abbreviation': abbr},
            'statistics': [{'name': 'fieldGoalsMade-fieldGoalsAttempted', 'displayValue': fg},
                           {'name': 'freeThrowsMade-freeThrowsAttempted', 'displayValue': ft},
                           {'name': 'offensiveRebounds', 'displayValue': oreb},
                           {'name': 'totalTurnovers', 'displayValue': tov}]}


def players(abbr, rows):
    return {'team': {'abbreviation': abbr},
            'statistics': [{'names': ['MIN', 'PTS'], 'athletes': [
                {'athlete': {'id': pid}, 'stats': stats, 'didNotPlay': dnp} for pid, stats, dnp in rows]}]}


RAW = {'boxscore': {'teams': [team('away', 'ATL', fg='50-99', ft='7-13', oreb='19', tov='16'),
                              team('home', 'BOS', fg='42-90', ft='20-24', oreb='9', tov='12')],
                    'players': [players('ATL', [('1', ['39', '18'], False), ('2', [], True)]),
                                players('BOS', [('3', ['41', '30'], False)])]}}
GAME = SimpleNamespace(game_id='401703370', season=2024, slate='2024-10-22', game_type='regular',
                       neutral_site=False, home='BOS', away='ATL', home_score=116, away_score=117)


def test_a_game_row_reads_both_teams_from_their_own_side():
    row = h.game_row(RAW, GAME)
    assert (row['home_fga'], row['home_fta'], row['home_oreb'], row['home_tov']) == (90, 24, 9, 12)
    assert (row['away_fga'], row['away_fta'], row['away_oreb'], row['away_tov']) == (99, 13, 19, 16)
    assert (row['home_score'], row['away_score']) == (116, 117)


def test_possessions_are_the_registered_formula_averaged_over_both_teams():
    home = {'fga': 90, 'fta': 24, 'oreb': 9, 'tov': 12}
    away = {'fga': 99, 'fta': 13, 'oreb': 19, 'tov': 16}
    assert h.possessions(home, away) == pytest.approx(((90 + 0.44 * 24 - 9 + 12) + (99 + 0.44 * 13 - 19 + 16)) / 2)


def test_a_box_score_whose_sides_disagree_with_the_schedule_stops_the_season():
    swapped = SimpleNamespace(**{**vars(GAME), 'home': 'ATL', 'away': 'BOS'})
    with pytest.raises(h.HistoryError, match='schedule says'):
        h.game_row(RAW, swapped)


def test_a_missing_or_garbled_count_stops_the_season():
    bad = {'boxscore': {'teams': [team('away', 'ATL', fg='fifty'), team('home', 'BOS')]}}
    with pytest.raises(h.HistoryError, match='not made-attempted'):
        h.game_row(bad, GAME)
    gone = {'boxscore': {'teams': [team('away', 'ATL', tov=''), team('home', 'BOS')]}}
    with pytest.raises(h.HistoryError, match='no totalTurnovers'):
        h.game_row(gone, GAME)


def test_a_player_who_did_not_play_has_zero_minutes():
    rows = h.minute_rows(RAW, '401703370')
    assert {(r['team'], r['player_id'], r['minutes']) for r in rows} == {('ATL', '1', 39), ('ATL', '2', 0),
                                                                       ('BOS', '3', 41)}


def fallback(rows):
    out = []
    for gid, hs, as_, hf, af in rows:
        out += [{'game_id': int(gid), 'team_home_away': 'home', 'team_score': hs, 'field_goals_attempted': hf},
                {'game_id': int(gid), 'team_home_away': 'away', 'team_score': as_, 'field_goals_attempted': af}]
    return pd.DataFrame(out)


def games(n, wrong=()):
    return pd.DataFrame([{'game_id': str(i), 'home_score': 100, 'away_score': 90, 'home_fga': 85, 'away_fga': 88}
                         for i in range(n)]), fallback(
        [(str(i), 100 if i not in wrong else 101, 90, 85, 88) for i in range(n)])


def test_the_fallback_must_agree_on_ninety_nine_games_in_a_hundred():
    ok, tb = games(200, wrong=(5, 6))
    assert h.check_against_fallback(ok, tb) == []
    bad, tb = games(200, wrong=(1, 2, 3))
    problems = h.check_against_fallback(bad, tb)
    assert 'agree on 197 of 200' in problems[0] and len(problems) == 4


def test_a_fallback_with_none_of_the_games_is_a_problem():
    g, _ = games(3)
    assert h.check_against_fallback(g, fallback([('99', 1, 1, 1, 1)])) == ['the fallback has none of this season\'s games']


def odds(provider, home, away, close=None):
    hto, ato = {'moneyLine': home}, {'moneyLine': away}
    if close:
        hto['close'] = {'moneyLine': {'american': close[0]}}
        ato['close'] = {'moneyLine': {'american': close[1]}}
    return {'provider': {'name': provider}, 'homeTeamOdds': hto, 'awayTeamOdds': ato}


def test_the_market_takes_the_close_where_there_is_one_and_the_margin_out():
    row = h.market_row({'items': [odds('DraftKings', -150, 130, close=('-200', '+170'))]}, GAME)
    assert row['closing'] is True and (row['home_price'], row['away_price']) == (-200, 170)
    ih, ia = 200 / 300, 100 / 270
    assert row['home_prob'] == pytest.approx(ih / (ih + ia), abs=1e-6)
    plain = h.market_row({'items': [odds('5Dimes.eu', -150, 130)]}, GAME)
    assert plain['closing'] is False and plain['home_price'] == -150


def test_a_live_price_is_never_used():
    row = h.market_row({'items': [odds('ESPN Bet - Live Odds', -900, 600), odds('DraftKings', -150, 130)]}, GAME)
    assert row['provider'] == 'DraftKings'
    assert h.market_row({'items': [odds('ESPN Bet - Live Odds', -900, 600)]}, GAME) is None


EMPTY = {'boxscore': {'teams': [{'homeAway': 'away', 'team': {'abbreviation': 'ATL'}, 'statistics': []},
                                {'homeAway': 'home', 'team': {'abbreviation': 'BOS'}, 'statistics': []}],
                      'players': [players('ATL', [('1', ['--', '0'], False)])]}}


def hoopr(gid='401703370', total_turnovers=(13, 15)):
    tb = pd.DataFrame([
        {'game_id': int(gid), 'team_home_away': 'home', 'team_abbreviation': 'BOS', 'team_score': 116,
         'field_goals_attempted': 90, 'free_throws_attempted': 24, 'offensive_rebounds': 9, 'turnovers': 12,
         'total_turnovers': total_turnovers[0]},
        {'game_id': int(gid), 'team_home_away': 'away', 'team_abbreviation': 'ATL', 'team_score': 117,
         'field_goals_attempted': 99, 'free_throws_attempted': 13, 'offensive_rebounds': 19, 'turnovers': 16,
         'total_turnovers': total_turnovers[1]}])
    pb = pd.DataFrame([
        {'game_id': int(gid), 'team_abbreviation': 'BOS', 'athlete_id': 3, 'minutes': 41.0, 'did_not_play': False},
        {'game_id': int(gid), 'team_abbreviation': 'ATL', 'athlete_id': 1, 'minutes': 39.0, 'did_not_play': False},
        {'game_id': int(gid), 'team_abbreviation': 'ATL', 'athlete_id': 2, 'minutes': None, 'did_not_play': True}])
    return tb, pb


def test_an_espn_box_with_no_team_figures_is_empty_and_a_full_one_is_not():
    assert h.espn_box_empty(EMPTY) and not h.espn_box_empty(RAW)
    assert h.game_row(RAW, GAME)['box_source'] == 'espn'


def test_an_empty_espn_box_is_read_from_the_fallback_and_says_so():
    row, minutes = h.fallback_rows(GAME, *hoopr())
    assert row['box_source'] == 'hoopr'
    assert (row['home_fga'], row['home_fta'], row['home_oreb'], row['home_tov']) == (90, 24, 9, 13)
    assert (row['away_fga'], row['away_tov']) == (99, 15)
    assert {(m['team'], m['player_id'], m['minutes']) for m in minutes} == {('BOS', '3', 41), ('ATL', '1', 39),
                                                                           ('ATL', '2', 0)}


def test_the_fallback_uses_player_turnovers_where_it_has_no_team_total():
    row, _ = h.fallback_rows(GAME, *hoopr(total_turnovers=(float('nan'), float('nan'))))
    assert (row['home_tov'], row['away_tov']) == (12, 16)


def test_a_fallback_whose_sides_disagree_with_the_schedule_stops_the_season():
    swapped = SimpleNamespace(**{**vars(GAME), 'home': 'ATL', 'away': 'BOS'})
    with pytest.raises(h.HistoryError, match='fallback home'):
        h.fallback_rows(swapped, *hoopr())


def test_a_game_neither_source_has_is_skipped_and_named(monkeypatch):
    import json
    monkeypatch.setattr(h.nba_schedule, 'cache_dir', lambda: None)
    sched = pd.DataFrame([{**vars(GAME), 'status': 'final'},
                          {**vars(GAME), 'game_id': '401703371', 'status': 'final'}])
    pages = {'401703370': EMPTY, '401703371': EMPTY}

    def get(url):
        return json.dumps(pages[url.split('event=')[1]]).encode()
    games_, minutes, skipped = h.boxscores(2024, get=get, schedule=sched, pause=0, fallback=hoopr())
    assert list(games_['game_id']) == ['401703370'] and games_['box_source'].tolist() == ['hoopr']
    assert len(skipped) == 1 and '401703371' in skipped[0]
    assert set(minutes['game_id']) == {'401703370'}


def test_the_agreement_check_compares_only_games_read_from_espn():
    g, tb = games(100, wrong=(1, 2))
    g['box_source'] = ['hoopr' if i < 10 else 'espn' for i in range(100)]
    # the two disagreements are fallback rows: they are the fallback, so they are not compared
    n, bad = h.fallback_disagreements(g, tb)
    assert n == 90 and bad == []


def test_main_writes_a_season_with_its_fallback_games_and_names_the_skipped(monkeypatch, tmp_path):
    import io
    import json
    monkeypatch.setattr(h, 'HISTORY', tmp_path)
    monkeypatch.setattr(h.nba_schedule, 'cache_dir', lambda: None)
    sched = pd.DataFrame([{**vars(GAME), 'status': 'final'},
                          {**vars(GAME), 'game_id': '401703371', 'status': 'final'},
                          {**vars(GAME), 'game_id': '401703372', 'status': 'final'}])
    monkeypatch.setattr(h.nba_schedule, 'load_schedule', lambda season: sched)
    tb, pb = hoopr()
    tb = pd.concat([tb, tb.assign(game_id=401703372)], ignore_index=True)
    pages = {'401703370': EMPTY, '401703371': EMPTY, '401703372': RAW}

    def parquet(df):
        buf = io.BytesIO()
        df.to_parquet(buf)
        return buf.getvalue()

    def fetch(url):
        if 'team_box' in url:
            return parquet(tb)
        if 'player_box' in url:
            return parquet(pb)
        if 'event=' in url:
            return json.dumps(pages[url.split('event=')[1]]).encode()
        return json.dumps({'items': []}).encode()
    monkeypatch.setattr(h, 'fetch', fetch)
    monkeypatch.setattr(h, 'market', lambda season, sched, pause=0.05: pd.DataFrame(columns=list(h.MARKET_FIELDS)))
    assert h.main(['2024', '2024']) == 0
    games_ = pd.read_csv(tmp_path / 'games_2024.csv', dtype={'game_id': str})
    assert dict(zip(games_['game_id'], games_['box_source'])) == {'401703370': 'hoopr', '401703372': 'espn'}
    assert '401703371' in (tmp_path / 'skipped_2024.csv').read_text(encoding='utf-8')
    assert (tmp_path / 'minutes_2024.csv').exists() and (tmp_path / 'market_2024.csv').exists()


def test_a_price_of_zero_is_no_price():
    assert h.market_row({'items': [odds('Caesars', 0, 0)]}, GAME) is None
    row = h.market_row({'items': [odds('Caesars', '0', '+120'), odds('William Hill', -140, 120)]}, GAME)
    assert row['provider'] == 'William Hill'
