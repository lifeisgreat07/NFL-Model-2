"""MLB's history (Stage 99 item 1): each final game's pitchers from its box score, and the season checked against
Retrosheet as experiments/mlb/stage98/registry.json's fallback_check says.

Every box and game log here is built by hand, so nothing is fetched.

Run with: pytest tests/test_mlb_history.py -v
"""
import io
import zipfile

import pandas as pd
import pytest

from src.sports.mlb import history


def box(home=(501, 502), away=(701,), lines=None):
    lines = lines or {}

    def side(club, pitchers):
        return {'team': {'id': club}, 'pitchers': list(pitchers),
                'players': {f'ID{p}': {'stats': {'pitching': lines.get(p, {'outs': 15, 'runs': 2})}} for p in pitchers}}
    return {'teams': {'home': side(147, home), 'away': side(111, away)}}


def test_each_clubs_pitchers_in_order_the_first_the_starter():
    rows = history.pitcher_rows(box(lines={501: {'outs': 18, 'runs': 3}}), '9')
    assert [(r['club'], r['order'], r['pitcher_id'], r['outs'], r['runs']) for r in rows] == [
        ('147', 0, '501', 18, 3), ('147', 1, '502', 15, 2), ('111', 0, '701', 15, 2)]


def test_a_box_with_no_pitcher_or_a_line_without_outs_stops_the_season():
    with pytest.raises(history.HistoryError, match='away box lists no club or no pitcher'):
        history.pitcher_rows(box(away=()), '9')
    with pytest.raises(history.HistoryError, match='pitcher 502 has no outs or runs'):
        history.pitcher_rows(box(lines={502: {'runs': 1}}), '9')


def test_every_unusable_game_of_a_season_is_named_at_once():
    sched = pd.DataFrame({'game_id': ['1', '2', '3'], 'status': ['final'] * 3})
    boxes = {'1': box(away=()), '2': box(), '3': box(home=())}

    def get(url):
        import json
        return json.dumps(boxes[url.split('/game/')[1].split('/')[0]]).encode()
    with pytest.raises(history.HistoryError) as e:
        history.read_season(2025, sched, get=get, pause=0)
    assert 'game 1:' in str(e.value) and 'game 3:' in str(e.value) and 'game 2:' not in str(e.value)


def test_the_box_read_asks_only_for_what_the_starter_term_needs():
    assert history.BOX.format(gid=1).endswith('fields=teams,home,away,team,id,pitchers,players,person,stats,'
                                              'pitching,runs,outs')


def log(rows):
    text = '\n'.join(','.join(f'"{x}"' for x in r) for r in rows)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as z:
        z.writestr('gl2025.txt', text)
    return buf.getvalue()


def row(date, number, away, home, away_score, home_score):
    return [date, number, 'Fri', away, 'AL', 1, home, 'AL', 1, away_score, home_score]


def season_games():
    return pd.DataFrame([
        {'game_id': '1', 'slate': '2025-07-04', 'game_type': 'regular', 'home': '147', 'away': '111',
         'home_score': 5, 'away_score': 3, 'neutral_site': False, 'venue_id': 3313, 'game_number': 1},
        {'game_id': '2', 'slate': '2025-07-05', 'game_type': 'regular', 'home': '111', 'away': '147',
         'home_score': 2, 'away_score': 7, 'neutral_site': False, 'venue_id': 3, 'game_number': 1},
        {'game_id': '3', 'slate': '2025-07-06', 'game_type': 'regular', 'home': '147', 'away': '111',
         'home_score': 4, 'away_score': 1, 'neutral_site': True, 'venue_id': 999, 'game_number': 1},
    ])


VENUES = {'147': 3313, '111': 3}


def test_retrosheet_codes_are_learned_from_the_seasons_own_games():
    retro = history.retro_games(log([row('20250704', 0, 'BOS', 'NYA', 3, 5), row('20250705', 0, 'NYA', 'BOS', 7, 2)]))
    assert history.code_map(retro, season_games()) == {'NYA': '147', 'BOS': '111'}


def test_a_season_that_agrees_and_a_swapped_neutral_game_that_still_agrees():
    retro = history.retro_games(log([row('20250704', 0, 'BOS', 'NYA', 3, 5), row('20250705', 0, 'NYA', 'BOS', 7, 2),
                                     row('20250706', 0, 'NYA', 'BOS', 4, 1)]))
    n, bad = history.fallback_check(season_games(), retro, VENUES)
    assert (n, bad) == (3, []) and history.checked(n, bad)


def test_a_wrong_score_is_listed_and_a_season_under_ninety_nine_percent_is_not_used():
    retro = history.retro_games(log([row('20250704', 0, 'BOS', 'NYA', 3, 5), row('20250705', 0, 'NYA', 'BOS', 7, 2),
                                     row('20250706', 0, 'BOS', 'NYA', 2, 4)]))
    n, bad = history.fallback_check(season_games(), retro, VENUES)
    assert n == 3 and len(bad) == 1 and 'Stats API 3 says 111 1 at 147 4' in bad[0]
    assert not history.checked(n, bad)
