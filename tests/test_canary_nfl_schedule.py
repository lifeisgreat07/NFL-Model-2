"""The nightly canary watches nfl.com's schedule page (Stage 15, item 6).

The TV-channel data comes from nfl.com's by-week page, an undocumented
payload that can change without notice. src/pipeline/canary.py checks the shape of
the next week's page every night: a changed feed is an ERROR and opens
"Nightly canary failing"; a game missing its kickoff or network is a
WARNING, because the TV code already holds that channel back and week 18's
kickoffs are not set until late December. Pages are built here from
synthetic games, so no league content is committed and no network is used.

Run with: pytest tests/test_canary_nfl_schedule.py -v
"""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from src.pipeline import canary  # noqa: E402

GOOD = {
    'id': 'g1', 'time': '2026-10-02T00:15:00Z', 'season': 2026, 'week': 4, 'seasonType': 'REG',
    'homeTeam': {'fullName': 'Cleveland Browns'}, 'awayTeam': {'fullName': 'Pittsburgh Steelers'},
    'broadcastInfo': {'homeNetworkChannels': ['Prime Video'], 'territory': 'NATIONAL'},
    'externalIds': [{'source': 'elias', 'id': '2026100100'}],
}


def page(*games):
    blob = json.dumps({'data': list(games)}, separators=(',', ':'))
    return f'<script>self.__next_f.push([1,{json.dumps(blob)}])</script>'


def game(**changes):
    g = copy.deepcopy(GOOD)
    for k, v in changes.items():
        g[k] = v
    return g


def test_a_complete_week_is_clean():
    r = canary.check_schedule_page(page(GOOD), 2026, 4)
    assert r.errors == [] and r.warnings == []


def test_a_page_with_no_games_is_an_error():
    r = canary.check_schedule_page('<html>no payload</html>', 2026, 4)
    assert r.errors and 'no games in the page payload' in r.errors[0]


def test_a_game_that_lost_its_id_or_teams_is_an_error():
    # Distinct ids: the payload reader keeps one game per id.
    r = canary.check_schedule_page(page(game(id='a', externalIds=[]), game(id='b', homeTeam={})), 2026, 4)
    assert len(r.errors) == 2
    assert 'elias id' in r.errors[0] and 'two teams' in r.errors[1]


def test_a_game_from_another_week_is_an_error():
    r = canary.check_schedule_page(page(game(week=3)), 2026, 4)
    assert r.errors and 'this week' in r.errors[0]


def test_a_missing_kickoff_or_network_is_only_a_warning():
    """Week 18's kickoffs are not set until late December; a nightly failure
    for that would be noise, and the TV code already holds such a channel back."""
    no_time = game(id='a', time=None)
    no_network = game(id='b', broadcastInfo={'homeNetworkChannels': [], 'territory': 'NATIONAL'})
    r = canary.check_schedule_page(page(no_time, no_network), 2026, 4)
    assert r.errors == []
    assert len(r.warnings) == 2 and 'kickoff' in r.warnings[0] and 'network' in r.warnings[1]


def _step():
    return dict(canary.default_steps())['nfl.com schedule']


def test_the_step_checks_the_next_week_to_predict(monkeypatch):
    from src.pipeline import nfl_schedule_probe
    asked = []
    def fetch(week, season):
        asked.append((week, season))
        return page(game(week=week))
    monkeypatch.setattr(nfl_schedule_probe, 'fetch', fetch)
    r = _step()({'season': 2026, 'next_week': 4})
    assert asked == [(4, 2026)] and r.errors == []


def test_the_step_skips_the_playoffs_and_an_unknown_week(monkeypatch):
    from src.pipeline import nfl_schedule_probe
    def fetch(week, season):
        raise AssertionError('nothing may be fetched')
    monkeypatch.setattr(nfl_schedule_probe, 'fetch', fetch)
    assert _step()({'season': 2026, 'next_week': 19}).startswith('skipped')
    assert _step()({'season': 2026}).startswith('skipped')


def test_an_unreachable_page_fails_the_canary(monkeypatch):
    from src.pipeline import nfl_schedule_probe
    def fetch(week, season):
        raise OSError('HTTP Error 403: Forbidden')
    monkeypatch.setattr(nfl_schedule_probe, 'fetch', fetch)
    report, _ = canary.run(2026, [('nfl.com schedule', lambda s: _step()({'season': 2026, 'next_week': 4}))])
    assert report.errors and 'OSError' in report.errors[0]
