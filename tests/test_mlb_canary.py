"""MLB's nightly canary (Stage 98 item 2): each read the daily run will make, judged on its shape, nothing kept.

Run with: pytest tests/test_mlb_canary.py -v
"""
from datetime import UTC, datetime

from src.sports.mlb import canary
from tests.test_mlb_schedule import HOME_VENUES, game

NOW = datetime(2026, 7, 4, 20, 0, tzinfo=UTC)


def box(runs=3, pitchers=(1,)):
    side = {'teamStats': {'batting': {'runs': runs}}, 'pitchers': list(pitchers)}
    return {'teams': {'home': side, 'away': side}}


def get_for(games, boxes):
    def get(url):
        if '/teams?' in url:
            return {'teams': [{'id': k, 'venue': {'id': v}} for k, v in HOME_VENUES.items()]}
        if '/boxscore' in url:
            return boxes[url.split('/game/')[1].split('/')[0]]
        return {'dates': [{'games': games}]}
    return get


def season_games():
    return [game(pk=1, season='2026', day='2026-07-03', start='2026-07-03T23:05:00Z'),
            game(pk=2, season='2026', day='2026-07-04', start='2026-07-04T23:05:00Z', coded='S', hs=None, as_=None)]


def test_a_good_night_has_no_errors():
    errors, notes = canary.run(NOW, get_for(season_games(), {'1': box()}))
    assert errors == []
    assert notes[0] == 'schedule: 2 games in 2026'
    assert notes[1] == 'slate: 2026-07-04: 1 scheduled'
    assert notes[2] == "box score: game 1: both clubs' runs and starters"


def test_a_box_score_without_pitchers_fails_the_night():
    errors, _ = canary.run(NOW, get_for(season_games(), {'1': box(pitchers=())}))
    assert errors and errors[0].startswith('box score raised ValueError') and 'no pitchers' in errors[0]


def test_a_step_that_raises_is_recorded_and_the_rest_still_run():
    games = season_games() + [game(pk=3, season='2026', coded='Q')]
    errors, notes = canary.run(NOW, get_for(games, {}))
    assert errors[0].startswith('schedule raised MLBScheduleError') and "unknown codedGameState 'Q'" in errors[0]
    assert len(notes) == len(canary.STEPS)


def test_main_exits_one_on_an_error_and_writes_the_report(tmp_path):
    report = tmp_path / 'r.md'
    code = canary.main(['--report', str(report)], now=NOW, get=get_for(season_games(), {'1': box(pitchers=())}))
    assert code == 1 and '## Errors' in report.read_text(encoding='utf-8')
