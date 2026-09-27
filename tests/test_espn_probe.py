"""The ESPN probe finds what is missing, and runs where it has to prove itself.

Stage 15 (CLAUDE.md). Before any TV-channel code, the plan asks whether
GitHub's runners can read ESPN's public scoreboard at all.
src/espn_probe.py reads weeks 1-4 of 2026 and reports each game that lacks
something a later stage needs. The network part runs in
.github/workflows/espn-probe.yml; these tests hold the judgement it makes on
a payload, and the workflow's wiring.

Run with: pytest tests/test_espn_probe.py -v
"""
import copy
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

import espn_probe as ep  # noqa: E402

WORKFLOW = ROOT / '.github' / 'workflows' / 'espn-probe.yml'

GOOD = {
    'id': '401872964', 'date': '2026-10-02T00:15Z',
    'status': {'type': {'name': 'STATUS_SCHEDULED'}},
    'competitions': [{
        'competitors': [
            {'homeAway': 'home', 'team': {'abbreviation': 'CLE'}},
            {'homeAway': 'away', 'team': {'abbreviation': 'PIT'}},
        ],
        'broadcasts': [{'market': 'national', 'names': ['Prime Video']}],
    }],
}


def broken(path, value):
    e = copy.deepcopy(GOOD)
    target = e
    for k in path[:-1]:
        target = target[k]
    if value is ...:
        del target[path[-1]]
    else:
        target[path[-1]] = value
    return e


def test_a_complete_game_passes():
    assert ep.check_event(GOOD) == []


@pytest.mark.parametrize('path, value, missing', [
    (['id'], ..., 'id'),
    (['date'], '', 'date'),
    (['status'], {}, 'status'),
    (['competitions', 0, 'broadcasts'], [], 'broadcast'),
    (['competitions', 0, 'broadcasts'], [{'market': 'national', 'names': []}], 'broadcast'),
])
def test_each_missing_field_is_named(path, value, missing):
    assert missing in ep.check_event(broken(path, value))


def test_two_teams_must_be_one_home_one_away():
    both_home = copy.deepcopy(GOOD)
    both_home['competitions'][0]['competitors'][1]['homeAway'] = 'home'
    assert 'two teams, home and away' in ep.check_event(both_home)
    one_team = copy.deepcopy(GOOD)
    one_team['competitions'][0]['competitors'].pop()
    assert 'two teams, home and away' in ep.check_event(one_team)


def test_a_week_is_summarised_game_by_game():
    payload = {'events': [GOOD, broken(['competitions', 0, 'broadcasts'], [])]}
    games, complete, problems = ep.summarise(payload)
    assert (games, complete) == (2, 1)
    assert problems == ['401872964: missing broadcast']
    assert ep.summarise({}) == (0, 0, [])


def test_an_empty_or_unreachable_week_fails_the_run(monkeypatch, capsys):
    monkeypatch.setattr(ep, 'fetch', lambda week, season: {'events': []})
    assert ep.main(['--weeks', '1']) == 1
    def boom(week, season):
        raise OSError('blocked')
    monkeypatch.setattr(ep, 'fetch', boom)
    assert ep.main(['--weeks', '1']) == 1
    assert 'UNREACHABLE' in capsys.readouterr().out
    monkeypatch.setattr(ep, 'fetch', lambda week, season: {'events': [GOOD]})
    assert ep.main(['--weeks', '1', '2']) == 0


def test_the_probe_writes_nothing():
    src = (ROOT / 'src' / 'espn_probe.py').read_text(encoding='utf-8')
    code = re.sub(r'(?s)""".*?"""', '', src)
    assert not re.search(r"open\([^)]*['\"][wa]", code) and 'write_text' not in code and 'json.dump(' not in code


def test_the_workflow_runs_it_on_its_own_pull_requests():
    wf = WORKFLOW.read_text(encoding='utf-8')
    assert re.search(r"pull_request:\s*\n\s*paths:\s*\n\s*- 'src/espn_probe\.py'", wf), (
        'the probe no longer runs on the pull requests that change it, so its answer is not on the PR')
    assert 'python src/espn_probe.py --weeks 1 2 3 4 --season 2026' in wf
    assert re.search(r'permissions:\s*\n\s*contents: read', wf)
    assert 'schedule:' not in wf, 'the probe is not a monitor; the nightly canary is where the feed will be watched'
