"""Stage 93 item 18: the season schedule is read with retries and under a budget.

Run with: pytest tests/test_request_budget.py -v
"""
import io
import json
import re
from pathlib import Path

import pytest

from src.core import request_budget
from src.sports.nba import history as nba_history
from src.sports.nhl import history as nhl_history

ROOT = Path(__file__).resolve().parents[1]


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def test_requests_inside_the_budget_pass_and_the_one_after_it_is_refused():
    clock = Clock()
    budget = request_budget.Budget(10, clock=clock)

    def slow(url):
        clock.now += 6        # each request takes six seconds
        return url

    get = budget.wrap(slow)
    assert get('a') == 'a' and get('b') == 'b'          # asked at 0 s and 6 s
    with pytest.raises(request_budget.BudgetSpent, match=r'2 requests in 12 s, past the budget of 10 s; stopped before c'):
        get('c')


def test_the_budget_sits_well_inside_the_daily_steps_timeout():
    assert request_budget.SCHEDULE_SECONDS <= 25 * 60 / 2


@pytest.mark.parametrize('history', [nhl_history, nba_history], ids=['nhl', 'nba'])
def test_a_read_that_fails_once_then_answers_yields_the_payload(monkeypatch, history):
    calls = []

    def urlopen(req, timeout):
        calls.append(req.full_url)
        if len(calls) == 1:
            raise OSError('connection reset')
        return io.BytesIO(json.dumps({'games': []}).encode())

    monkeypatch.setattr(history.urllib.request, 'urlopen', urlopen)
    monkeypatch.setattr(history.time, 'sleep', lambda s: None)
    get = request_budget.Budget().wrap(lambda u: json.loads(history.fetch(u)))
    assert get('https://example.test/schedule') == {'games': []}
    assert len(calls) == 2


@pytest.mark.parametrize('sport', ['nhl', 'nba'])
def test_each_daily_run_reads_its_schedule_through_the_retrying_get_under_a_budget(sport):
    src = (ROOT / 'src' / 'sports' / sport / 'daily.py').read_text(encoding='utf-8')
    main = src[src.index('\ndef main('):]
    assert re.search(r'\n    sched = \w+_schedule\.load_schedule\(season, get=request_budget\.Budget\(\)\.wrap\('
                     r'lambda u: json\.loads\(get\(u\)\)\)\)\n', main), sport
    assert 'get: Callable[[str], bytes] = history.fetch' in main.split('\n')[1]
