"""The NHL data probe judges each source on the shape a later stage needs.

Stage 51 item 1. `src/sports/nhl/data_probe.py` reads every source the NHL's
go/no-go (`docs/nhl-data.md`) relies on; the network part runs in
`.github/workflows/nhl-data-probe.yml`, from GitHub's own runners. These tests
hold the judgement it makes on each answer, built here from small synthetic
payloads so no league content is committed, and the workflow's wiring.

Run with: pytest tests/test_nhl_data_probe.py -v
"""
import json
import re
from pathlib import Path

from src.sports.nhl import data_probe as probe

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github' / 'workflows' / 'nhl-data-probe.yml'


def game(**over):
    g = {'id': 2026020044, 'startTimeUTC': '2026-10-06T23:00:00Z', 'gameState': 'FUT',
         'homeTeam': {'abbrev': 'TOR'}, 'awayTeam': {'abbrev': 'NSH'}}
    g.update(over)
    return {'gameWeek': [{'date': '2026-10-06', 'games': [g]}]}


def test_a_complete_schedule_passes():
    assert probe.check_schedule(game()) == []


def test_a_schedule_game_missing_what_the_lock_needs_is_named():
    assert 'startTimeUTC' in probe.check_schedule(game(startTimeUTC=None))[0]
    assert 'two teams' in probe.check_schedule(game(awayTeam={'abbrev': 'TOR'}))[0]
    assert 'a UTC start' in probe.check_schedule(game(startTimeUTC='2026-10-06T19:00:00-04:00'))[0]
    assert probe.check_schedule({'gameWeek': []}) == ['no games in the week']


def shots(n=30, xy=True, goalie=True):
    detail = {}
    if xy:
        detail.update(xCoord=50, yCoord=-10)
    if goalie:
        detail['goalieInNetId'] = 8475683
    return {'plays': [{'typeDescKey': 'shot-on-goal', 'details': dict(detail)} for _ in range(n)]}


def test_play_by_play_with_coordinates_and_goalies_passes():
    assert probe.check_play_by_play(shots()) == []


def test_play_by_play_without_coordinates_or_goalies_fails():
    assert 'no coordinates' in probe.check_play_by_play(shots(xy=False))[0]
    assert 'no goalie in net' in probe.check_play_by_play(shots(goalie=False))[0]
    assert 'only 5 shots' in probe.check_play_by_play(shots(n=5))[0]


def box(home_starters=1, away_starters=1):
    def side(n):
        return {'goalies': [{'starter': True}] * n + [{'starter': False}]}
    return {'playerByGameStats': {'homeTeam': side(home_starters), 'awayTeam': side(away_starters)}}


def test_one_starter_per_team_passes_and_anything_else_fails():
    assert probe.check_box_score(box()) == []
    assert probe.check_box_score(box(home_starters=0)) == ['homeTeam: 0 starting goalies flagged, not 1']
    assert probe.check_box_score(box(away_starters=2)) == ['awayTeam: 2 starting goalies flagged, not 1']


def odds_game(gid, home=True, away=True):
    ml = [{'description': 'MONEY_LINE_2_WAY', 'value': -150.0}]
    other = [{'description': 'PUCK_LINE', 'value': 120.0}]
    return {'gameId': gid, 'homeTeam': {'odds': ml if home else other}, 'awayTeam': {'odds': ml if away else other}}


def test_live_odds_need_a_moneyline_for_both_teams():
    assert probe.check_live_odds({'games': [odds_game(1), odds_game(2)]}) == []
    assert probe.check_live_odds({'games': [odds_game(1), odds_game(2, away=False)]}) == \
        ['no two-way moneyline for games 2']
    assert probe.check_live_odds({}) == ['no games list in the odds feed']


def test_a_day_without_games_is_not_a_broken_odds_feed():
    assert probe.check_live_odds({'games': []}) == []


def test_espn_odds_need_both_moneylines():
    good = {'items': [{'homeTeamOdds': {'moneyLine': 170}, 'awayTeamOdds': {'moneyLine': -200}}]}
    assert probe.check_espn_odds(good) == []
    assert probe.check_espn_odds({'items': []}) == ['no odds for a past game']
    half = {'items': [{'homeTeamOdds': {'moneyLine': 170}, 'awayTeamOdds': {}}]}
    assert probe.check_espn_odds(half) == ['a moneyline is missing for one team']


def test_the_fallback_needs_its_three_folders():
    assert probe.check_fallback([{'name': n} for n in ('pbp', 'schedules', 'goalie_box', 'rosters')]) == []
    assert probe.check_fallback([{'name': 'pbp'}]) == ['the fallback has no goalie_box, schedules folder']
    assert probe.check_fallback({'message': 'Not Found'})


def test_daily_faceoff_needs_names_and_a_label():
    page = '<script id="__NEXT_DATA__">{"homeGoalieName": "A", "homeNewsStrengthName": "Confirmed"}</script>'
    assert probe.check_faceoff(page) == []
    assert probe.check_faceoff(page.replace('Confirmed', 'Unknown')) == ['no Confirmed or Likely label']
    assert 'no embedded data payload' in probe.check_faceoff('<html></html>')


def fake_get(responses):
    def get(url):
        for pattern, body in responses.items():
            if pattern in url:
                if isinstance(body, Exception):
                    raise body
                return body if isinstance(body, str) else json.dumps(body)
        raise AssertionError(f'unexpected url {url}')
    return get


GOOD = {
    '/schedule/': game(),
    '/play-by-play': shots(),
    '/boxscore': box(),
    '/partner-game/': {'games': [odds_game(1)]},
    'scoreboard': {'events': [{'id': '401'}]},
    '/odds': {'items': [{'homeTeamOdds': {'moneyLine': 170}, 'awayTeamOdds': {'moneyLine': -200}}]},
    'fastRhockey': [{'name': n} for n in ('pbp', 'schedules', 'goalie_box')],
    'dailyfaceoff': '__NEXT_DATA__ homeGoalieName Likely',
}


def test_every_source_usable_exits_zero(capsys):
    assert probe.main(get=fake_get(GOOD)) == 0
    out = capsys.readouterr().out
    assert out.count(': ok') == 7 and 'all usable from here' in out


def test_one_unreachable_source_fails_the_run_and_says_which(capsys):
    """ESPN's scoreboard answered GitHub's runners with 403 (#131); that is the
    failure this probe exists to find."""
    bad = dict(GOOD, scoreboard=OSError('HTTP Error 403: Forbidden'))
    assert probe.main(get=fake_get(bad)) == 1
    out = capsys.readouterr().out
    assert 'ESPN past odds: UNREACHABLE' in out and '403' in out
    assert out.count(': ok') == 6


def test_one_wrong_shape_fails_the_run():
    assert probe.main(get=fake_get(dict(GOOD, **{'/boxscore': box(home_starters=0)}))) == 1


def test_the_workflow_runs_the_probe_on_its_own_pull_requests_and_writes_nothing():
    wf = WORKFLOW.read_text(encoding='utf-8')
    assert re.search(r'^name: NHL ', wf, re.M)
    assert "'src/sports/nhl/data_probe.py'" in wf and "'.github/workflows/nhl-data-probe.yml'" in wf
    assert 'workflow_dispatch' in wf and 'schedule:' not in wf
    assert 'python -m src.sports.nhl.data_probe' in wf
    assert re.search(r'permissions:\s*\n\s*contents: read\s*\n', wf)
    assert 'git-auto-commit' not in wf and 'git add' not in wf and 'git push' not in wf
