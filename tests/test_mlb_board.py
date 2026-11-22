"""MLB's day board (Stage 100 item 1; layout A, Mark 2026-11-22): what baseball adds to the NHL's and NBA's board.

The series line ("Game 2 of 4 · DET leads 1-0") and the doubleheader and start-time fields are worked out in
src/sports/mlb/site.py and printed by src/sports/mlb/pages/mlb.js. The games here are built by hand in the shape
the daily run will write (src/sports/mlb/schedule.py's rows), so nothing is fetched. April 13, 2024's MIN at DET
doubleheader is the worked example: games 2 and 3 of a four-game series, DET having won game 1.

Run with: pytest tests/test_mlb_board.py -v
"""
import json
import re
import subprocess
from pathlib import Path

import pytest

from src.sports.mlb import site
from tests.js_source import function_source
from tests.optional import require_tool

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / 'src' / 'sports' / 'mlb' / 'pages' / 'mlb.js').read_text(encoding='utf-8').replace('\r\n', '\n')
ESCAPE = (ROOT / 'src' / 'core' / 'escape.js').read_text(encoding='utf-8').replace('\r\n', '\n') + '\n'
DET, MIN = '116', '142'


def game(pk, start, n, of=4, home=DET, away=MIN, status='final', home_win=None, **extra):
    g = {'game_id': str(pk), 'season': 2024, 'slate': start[:10], 'start_utc': start, 'home': home, 'away': away,
         'status': status, 'home_score': None, 'away_score': None, 'home_win': home_win, 'game_type': 'regular',
         'game_number': 1, 'double_header': 'N', 'series_game': n, 'series_games': of, 'start_time_tbd': False}
    g.update(extra)
    return g


SERIES = [game(1, '2024-04-11T22:40:00Z', 1, home_win=1),
          game(2, '2024-04-13T17:10:00Z', 2, home_win=0, double_header='Y', game_number=1),
          game(3, '2024-04-13T21:15:00Z', 3, status='scheduled', double_header='Y', game_number=2,
               start_time_tbd=True),
          game(4, '2024-04-14T17:40:00Z', 4, status='scheduled')]


# ---------- the series line
def test_a_series_counts_its_earlier_finished_games():
    assert site.series_line(SERIES[1], SERIES) == {'game': 2, 'of': 4, 'home_won': 1, 'away_won': 0}
    assert site.series_line(SERIES[2], SERIES) == {'game': 3, 'of': 4, 'home_won': 1, 'away_won': 1}
    assert site.series_line(SERIES[0], SERIES) == {'game': 1, 'of': 4, 'home_won': 0, 'away_won': 0}


def test_a_later_game_or_one_not_final_is_not_counted():
    games = [*SERIES[:2], game(3, '2024-04-13T21:15:00Z', 3, status='in_progress', home_win=None), SERIES[3]]
    assert site.series_line(games[3], games) == {'game': 4, 'of': 4, 'home_won': 1, 'away_won': 1}
    assert site.series_line(games[0], games) == {'game': 1, 'of': 4, 'home_won': 0, 'away_won': 0}


def test_a_final_with_no_winner_is_not_counted():
    """2016-09-29's called CHC at PIT: final, tied, no winner (src/sports/mlb/schedule.py)."""
    games = [game(1, '2024-04-11T22:40:00Z', 1, home_win=None), game(2, '2024-04-12T22:40:00Z', 2, status='scheduled')]
    assert site.series_line(games[1], games) == {'game': 2, 'of': 4, 'home_won': 0, 'away_won': 0}


def test_the_same_clubs_earlier_in_the_season_are_another_series():
    april = game(9, '2024-04-02T22:40:00Z', 1, of=3, home_win=1)
    may = [game(10, '2024-05-20T22:40:00Z', 1, of=3, home_win=0), game(11, '2024-05-21T22:40:00Z', 2, of=3,
                                                                       status='scheduled')]
    assert site.series_line(may[1], [april, *may]) == {'game': 2, 'of': 3, 'home_won': 0, 'away_won': 1}
    # Week apart, same length: still another series, kept apart by the week before.
    week_ago = game(12, '2024-05-12T22:40:00Z', 1, of=3, home_win=1)
    assert site.series_line(may[1], [week_ago, *may])['home_won'] == 0


def test_the_other_clubs_series_and_the_return_series_are_not_counted():
    at_min = game(5, '2024-04-12T22:40:00Z', 1, home=MIN, away=DET, home_win=1)
    other = game(6, '2024-04-12T22:40:00Z', 1, home=DET, away='147', home_win=1)
    min_at_nyy = game(7, '2024-04-12T22:40:00Z', 1, home='147', away=MIN, home_win=1)
    games = [at_min, other, min_at_nyy, *SERIES]
    assert site.series_line(SERIES[1], games) == {'game': 2, 'of': 4, 'home_won': 1, 'away_won': 0}


@pytest.mark.parametrize('place', [(None, None), (None, 4), (1, 0), (5, 4), (0, 3), (True, 3)],
                         ids=['none', 'no-game', 'of-none', 'past-the-end', 'game-zero', 'boolean'])
def test_no_place_or_one_that_makes_no_sense_is_no_series_line(place):
    g = game(7, '2024-04-13T17:10:00Z', place[0], of=place[1])
    assert site.series_line(g, [g]) is None


# ---------- a game's own fields
@pytest.mark.parametrize('dh, number, tbd, want', [
    ('N', 1, False, (0, 'set')), ('Y', 1, False, (1, 'set')), ('Y', 2, True, (2, 'after')),
    ('S', 2, False, (2, 'set')), ('S', 2, True, (2, 'tbd')), ('N', 1, True, (0, 'tbd')), ('Y', 3, False, (0, 'set'))],
    ids=['single', 'dh-game-1', 'dh-game-2-after-game-1', 'split-game-2', 'split-game-2-unset', 'unset', 'no-game-3'])
def test_a_doubleheaders_game_and_an_unset_start(dh, number, tbd, want):
    g = game(8, '2024-04-13T08:33:00Z', 1, double_header=dh, game_number=number, start_time_tbd=tbd)
    s = site.slim_game(g, [g])
    assert (s['dh'], s['time']) == want


def test_clubs_are_codes_and_an_unknown_club_is_a_question_mark():
    s = site.slim_game(game(9, '2024-04-13T17:10:00Z', 1, home='999'), [])
    assert (s['away'], s['home']) == ('MIN', '?')


def test_a_starter_is_shown_by_name_once_named():
    g = game(10, '2024-04-13T17:10:00Z', 1, home_starter={'id': 1, 'name': 'Kenta Maeda'}, away_starter={'id': 2})
    s = site.slim_game(g, [g])
    assert (s['asp'], s['hsp']) == (None, 'Kenta Maeda')


# ---------- the build
def board_with(tmp_path, monkeypatch, sched):
    res = tmp_path / 'results' / 'mlb'
    res.mkdir(parents=True)
    if sched is not None:
        (res / 'schedule_2024.json').write_text(json.dumps(sched), encoding='utf-8')
    monkeypatch.setattr(site, 'PATHS', type('P', (), {'results': res})())
    return site.board(2024)


def test_before_the_first_run_the_board_has_no_games_and_says_so(tmp_path, monkeypatch):
    b = board_with(tmp_path, monkeypatch, None)
    assert (b['games'], b['picks'], b['schedule_as_of']) == ([], {}, None)
    assert 'The board fills from the first daily run' in JS


def test_an_empty_schedule_stops_the_build(tmp_path, monkeypatch):
    with pytest.raises(ValueError, match='no games'):
        board_with(tmp_path, monkeypatch, {'as_of': '2024-04-13', 'games': []})


def test_no_game_has_a_pick_until_stage_101_defines_the_file(tmp_path, monkeypatch):
    b = board_with(tmp_path, monkeypatch, {'as_of': '2024-04-13', 'games': SERIES})
    assert b['picks'] == {} and [g['id'] for g in b['games']] == ['1', '2', '3', '4']
    assert b['games'][1]['series'] == {'game': 2, 'of': 4, 'home_won': 1, 'away_won': 0}
    assert set(b['teams']) == {code for code, _ in site.teams.NAMES.values()}


def test_the_page_builds_with_every_placeholder_filled_and_its_scripts_hashed(tmp_path, monkeypatch):
    b = board_with(tmp_path, monkeypatch, {'as_of': '2024-04-13', 'games': SERIES})
    html = site.render({'built_utc': '2024-04-13T15:00:00Z', 'board': b})
    assert '<html lang="en" data-sport="mlb">' in html and 'id="mlb-data"' in html
    assert not re.search(r'__[A-Z0-9_]+__', html)
    assert "script-src 'sha256-" in html and "script-src 'unsafe-inline'" not in html


def test_the_page_is_not_published_yet():
    """Stage 101 makes MLB live; until then the site build does not list it."""
    from src.site import build
    assert 'mlb' not in build.SPORTS


# ---------- what the page prints
def run_node(names, body):
    node = require_tool('node')
    src = (ESCAPE + ''.join(function_source(JS, n, at_line_start=True) for n in names) + body)
    r = subprocess.run([node, '-e', src], capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_the_series_line_names_the_leader_or_says_tied():
    out = run_node(['seriesText'], """
const g = s => ({home: 'DET', away: 'MIN', series: s});
console.log(JSON.stringify([
  seriesText(g({game: 2, of: 4, home_won: 1, away_won: 0})),
  seriesText(g({game: 3, of: 4, home_won: 1, away_won: 1})),
  seriesText(g({game: 3, of: 3, home_won: 0, away_won: 2})),
  seriesText(g({game: 1, of: 3, home_won: 0, away_won: 0})),
  seriesText(g(null))]));""")
    assert out == ['Game 2 of 4 · DET leads 1-0', 'Game 3 of 4 · tied 1-1', 'Game 3 of 3 · MIN leads 2-0',
                   'Game 1 of 3', '']


def test_the_starters_are_away_first_and_an_unnamed_one_says_so():
    out = run_node(['startersText'], """
console.log(JSON.stringify([
  startersText({asp: 'Joe Ryan', hsp: 'Kenta Maeda'}), startersText({asp: 'Joe Ryan', hsp: null}),
  startersText({asp: null, hsp: null}), startersText({asp: '<b>x</b>', hsp: 'y'})]));""")
    assert out == ['Joe Ryan v Kenta Maeda', 'Joe Ryan v to be named', '', '&lt;b&gt;x&lt;/b&gt; v y']


def test_an_unset_start_is_never_printed_as_a_time():
    out = run_node(['mlbTime'], """
const FMT_HOUR = {format: d => 'HOUR'};
console.log(JSON.stringify([
  mlbTime({status: 'scheduled', start: '2027-03-25T08:33:00Z', time: 'tbd'}),
  mlbTime({status: 'scheduled', start: '2024-04-13T21:15:00Z', time: 'after'}),
  mlbTime({status: 'scheduled', start: '2024-04-13T17:10:00Z', time: 'set'}),
  mlbTime({status: 'final', start: '2024-04-13T17:10:00Z', time: 'set'})]));""")
    assert out == ['TBD', 'After G1', 'HOUR', 'Final']


def test_a_day_lists_unset_starts_last_and_game_two_after_game_one():
    out = run_node(['firstPitchOrder'], """
const day = [{id: 'tbd', start: '2027-03-25T08:33:00Z', time: 'tbd'}, {id: 'late', start: '2027-03-25T23:10:00Z', time: 'set'},
             {id: 'g2', start: '2027-03-25T21:15:00Z', time: 'after'}, {id: 'early', start: '2027-03-25T17:10:00Z', time: 'set'}];
console.log(JSON.stringify(day.sort(firstPitchOrder).map(g => g.id)));""")
    assert out == ['early', 'g2', 'late', 'tbd']
