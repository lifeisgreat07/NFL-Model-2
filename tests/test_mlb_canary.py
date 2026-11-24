"""MLB's nightly canary (Stage 98 item 2, per-source since Stage 101 item 4): each source the daily run reads, judged
on its own, nothing kept.

Run with: pytest tests/test_mlb_canary.py -v
"""
from datetime import UTC, datetime
from pathlib import Path

from src.sports.mlb import canary
from tests.test_mlb_schedule import HOME_VENUES, game

NOW = datetime(2026, 7, 4, 20, 0, tzinfo=UTC)
ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / '.github' / 'workflows' / 'mlb-canary.yml').read_text(encoding='utf-8')


def box(pitchers=(1,)):
    def side(club):
        return {'team': {'id': club}, 'pitchers': list(pitchers),
                'players': {f'ID{p}': {'stats': {'pitching': {'outs': 18, 'runs': 2}}} for p in pitchers}}
    return {'teams': {'home': side(147), 'away': side(111)}}


ODDS = {'items': [{'provider': {'name': 'DraftKings'}, 'homeTeamOdds': {'moneyLine': -140},
                   'awayTeamOdds': {'moneyLine': 120}}]}
NO_ODDS = {'items': []}
BOARD = {'events': [{'id': 'e2', 'date': '2026-07-04T23:05Z', 'competitions': [{'competitors': [
    {'homeAway': 'home', 'team': {'abbreviation': 'NYY'}}, {'homeAway': 'away', 'team': {'abbreviation': 'BOS'}}]}]}]}


def get_for(games, boxes, odds=ODDS, kalshi=None):
    def get(url):
        if '/teams?' in url:
            return {'teams': [{'id': k, 'venue': {'id': v}} for k, v in HOME_VENUES.items()]}
        if '/boxscore' in url:
            return boxes[url.split('/game/')[1].split('/')[0]]
        if 'scoreboard' in url:
            return BOARD
        if '/odds' in url:
            return odds
        if 'kalshi' in url:
            return {'markets': []} if kalshi is None else kalshi
        return {'dates': [{'games': games}]}
    return get


def season_games():
    return [game(pk=1, season='2026', day='2026-07-03', start='2026-07-03T23:05:00Z'),
            game(pk=2, season='2026', day='2026-07-04', start='2026-07-04T23:05:00Z', coded='S', hs=None, as_=None)]


def test_a_good_night_names_every_source_and_fails_none():
    failed, notes = canary.run(NOW, get_for(season_games(), {'1': box()}))
    assert failed == []
    assert [n.split(':')[0] for n in notes] == list(canary.SOURCES)
    assert notes[0] == 'Stats API schedule: 2 games in 2026; 2026-07-04: 1 scheduled'
    assert notes[2] == 'Stats API box score: game 1: 2 pitcher lines, both starters'
    assert notes[3] == 'ESPN odds: 1 of the next 1 games priced'
    assert notes[4] == 'Kalshi: 0 games quoted on both sides (fallback only)'


def test_a_box_score_without_pitchers_fails_its_source_alone():
    failed, _ = canary.run(NOW, get_for(season_games(), {'1': box(pitchers=())}))
    assert failed == ['Stats API box score']


def test_odds_that_price_no_upcoming_game_fail_their_source():
    failed, notes = canary.run(NOW, get_for(season_games(), {'1': box()}, odds=NO_ODDS))
    assert failed == ['ESPN odds'] and 'priced none of the next 1 games' in notes[3]


def test_no_game_in_the_next_week_is_not_an_odds_failure():
    winter = datetime(2026, 12, 1, 7, 0, tzinfo=UTC)
    failed, notes = canary.run(winter, get_for(season_games(), {'1': box()}))
    assert 'ESPN odds' not in failed and 'no game scheduled in the next week' in notes[3]


def test_a_kalshi_feed_without_a_market_list_fails():
    failed, _ = canary.run(NOW, get_for(season_games(), {'1': box()}, kalshi={'error': 'x'}))
    assert failed == ['Kalshi']


def test_an_unreadable_schedule_skips_what_needs_it_rather_than_failing_twice():
    games = season_games() + [game(pk=3, season='2026', coded='Q')]
    failed, notes = canary.run(NOW, get_for(games, {}))
    assert failed == ['Stats API schedule'] and "unknown codedGameState 'Q'" in notes[0]
    assert notes[2] == 'Stats API box score: not checked, the schedule could not be read tonight'
    assert len(notes) == len(canary.SOURCES)


def test_main_exits_one_and_writes_each_failing_source(tmp_path):
    report, failed = tmp_path / 'r.md', tmp_path / 'f.txt'
    code = canary.main(['--report', str(report), '--failed', str(failed)], now=NOW,
                       get=get_for(season_games(), {'1': box(pitchers=())}))
    assert code == 1 and failed.read_text(encoding='utf-8') == 'Stats API box score\n'
    assert 'FAILED' in report.read_text(encoding='utf-8')


def test_the_workflow_raises_and_closes_one_issue_per_source():
    for source in canary.SOURCES:
        title = f'MLB: {source} failing in the nightly canary'
        assert f'--title "{title}" --body-file mlb-canary-report.md' in WORKFLOW
        assert f'--resolve --title "{title}"' in WORKFLOW
        assert f"grep -qx '{source}' mlb-canary-failed.txt" in WORKFLOW
    assert 'MLB: nightly canary failing' in WORKFLOW
