"""The nfl.com schedule probe finds what is missing, and runs where it has to prove itself.

Stage 15 (CLAUDE.md). ESPN answers GitHub's runners with 403 (#131), so the
next candidate for TV channels is the league's own by-week schedule page.
src/nfl_schedule_probe.py reads weeks 1-4 of 2026 from it and reports each game
that lacks something a later stage needs. The network part runs in
.github/workflows/nfl-schedule-probe.yml; these tests hold the judgement it
makes on a page, built here from synthetic games so no league content is
committed, and the workflow's wiring.

Run with: pytest tests/test_nfl_schedule_probe.py -v
"""
import copy
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

import nfl_schedule_probe as probe  # noqa: E402

WORKFLOW = ROOT / '.github' / 'workflows' / 'nfl-schedule-probe.yml'

GOOD = {
    'id': 'aa29da01-4feb-11f1-abca-2c54536568a9',
    'homeTeam': {'fullName': 'Cleveland Browns'},
    'awayTeam': {'fullName': 'Pittsburgh Steelers'},
    'time': '2026-10-02T00:15:00Z',
    'broadcastInfo': {'homeNetworkChannels': ['Prime Video'], 'territory': 'NATIONAL'},
    'season': 2026, 'seasonType': 'REG', 'week': 4,
    'externalIds': [{'source': 'elias', 'id': '2026100100'}, {'source': 'gsis', 'id': '60226'}],
}


def game(**changes):
    g = copy.deepcopy(GOOD)
    for dotted, value in changes.items():
        target, keys = g, dotted.split('__')
        for k in keys[:-1]:
            target = target[k]
        target[keys[-1]] = value
    return g


def page(*chunks):
    """A page shaped like nfl.com's: each chunk is one push of payload text."""
    pushes = ''.join(f'<script>self.__next_f.push([1,{json.dumps(c)}])</script>' for c in chunks)
    return f'<html><body>{pushes}</body></html>'


def test_a_complete_game_passes():
    assert probe.check_game(GOOD, 2026, 4) == []


@pytest.mark.parametrize('changes, missing', [
    ({'externalIds': [{'source': 'gsis', 'id': '60226'}]}, 'elias id'),
    ({'externalIds': [{'source': 'elias', 'id': 'tbd'}]}, 'elias id'),
    ({'time': ''}, 'kickoff'),
    ({'homeTeam': {}}, 'two teams'),
    ({'broadcastInfo__territory': 'UNKNOWN'}, 'territory'),
    ({'broadcastInfo__homeNetworkChannels': []}, 'network'),
    ({'broadcastInfo__homeNetworkChannels': ['']}, 'network'),
])
def test_each_missing_field_is_named(changes, missing):
    assert missing in probe.check_game(game(**changes), 2026, 4)


def test_one_team_twice_is_not_two_teams():
    same = game(awayTeam={'fullName': 'Cleveland Browns'})
    assert 'two teams' in probe.check_game(same, 2026, 4)


@pytest.mark.parametrize('changes', [{'week': 3}, {'season': 2025}, {'seasonType': 'PRE'}])
def test_a_game_from_another_week_is_not_this_weeks_game(changes):
    """nfl.com's ways-to-watch page served another slate under week 4 on
    2026-09-27; a page answering with the wrong week must fail, not count."""
    assert any(m.startswith('this week') for m in probe.check_game(game(**changes), 2026, 4))


def test_games_are_read_from_the_payload_once_each_across_pushes():
    other = game(id='bb00', externalIds=[{'source': 'elias', 'id': '2026100400'}])
    not_a_game = {'id': 'x1', 'fullName': 'Arizona Cardinals'}
    blob = json.dumps({'data': [GOOD, not_a_game]})
    html = page(blob[:40], blob[40:], json.dumps({'again': [GOOD, other]}))
    got = probe.extract_games(html)
    assert [g['id'] for g in got] == [GOOD['id'], 'bb00']


def test_a_page_without_the_payload_has_no_games():
    assert probe.extract_games('<html>Watch on CBS</html>') == []


def test_a_week_is_summarised_game_by_game():
    games, complete, problems = probe.summarise([GOOD, game(broadcastInfo__homeNetworkChannels=[])], 2026, 4)
    assert (games, complete) == (2, 1)
    assert problems == ['2026100100: missing network']
    assert probe.summarise([], 2026, 4) == (0, 0, [])


def test_an_empty_or_unreachable_week_fails_the_run(monkeypatch, capsys):
    monkeypatch.setattr(probe, 'fetch', lambda week, season: page(json.dumps({'data': []})))
    assert probe.main(['--weeks', '4']) == 1
    def boom(week, season):
        raise OSError('blocked')
    monkeypatch.setattr(probe, 'fetch', boom)
    assert probe.main(['--weeks', '4']) == 1
    assert 'UNREACHABLE' in capsys.readouterr().out
    monkeypatch.setattr(probe, 'fetch',
                        lambda week, season: page(json.dumps({'data': [game(week=week)]})))
    assert probe.main(['--weeks', '3', '4']) == 0


def test_the_probe_writes_nothing():
    src = (ROOT / 'src' / 'nfl_schedule_probe.py').read_text(encoding='utf-8')
    code = re.sub(r'(?s)""".*?"""', '', src)
    assert not re.search(r"open\([^)]*['\"][wa]", code) and 'write_text' not in code and 'json.dump(' not in code


def test_the_workflow_runs_it_on_its_own_pull_requests():
    wf = WORKFLOW.read_text(encoding='utf-8')
    assert re.search(r"pull_request:\s*\n\s*paths:\s*\n\s*- 'src/nfl_schedule_probe\.py'", wf), (
        'the probe no longer runs on the pull requests that change it, so its answer is not on the PR')
    assert 'python src/nfl_schedule_probe.py --weeks 1 2 3 4 --season 2026' in wf
    assert re.search(r'permissions:\s*\n\s*contents: read', wf)
    assert 'schedule:' not in wf, 'the probe is not a monitor; the nightly canary is where the feed will be watched'
