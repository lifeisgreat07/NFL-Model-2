"""Stage 91 item 2 (audit 7, R2): an empty or shrunken schedule feed stops the
day sports' daily runs before anything is written.

Audit 7 injected a feed in which every club returned an empty games list: the
NHL's run exited 0, wrote schedule_2026.json with 0 games, reset every grade
to pending and emptied the forward test, and committed it. These drive both
daily runs with that feed over a temporary results folder holding the
committed schedule, and check the run stops and writes nothing.

Run with: pytest tests/test_schedule_guard.py -v
"""
import json
import shutil
from datetime import UTC, datetime

import pandas as pd
import pytest

from src.core import schedule_guard as sg
from tests.test_daily_end_to_end import ROOT, committed_schedule, temp_paths


def write(path, n):
    path.write_text(json.dumps({'as_of': '2026-11-04', 'games': [{'game_id': str(i)} for i in range(n)]}),
                    encoding='utf-8')


def test_an_empty_feed_is_refused_even_with_nothing_committed(tmp_path):
    with pytest.raises(sg.ScheduleShrank, match='no games at all'):
        sg.check(0, tmp_path / 'schedule_2026.json')


def test_a_first_run_with_no_committed_schedule_passes(tmp_path):
    sg.check(10, tmp_path / 'schedule_2026.json')


def test_a_few_lost_games_pass_and_more_stop_the_run(tmp_path):
    path = tmp_path / 'schedule_2026.json'
    write(path, 1344)
    allowed = max(sg.ALLOWED_MIN, int(1344 * sg.ALLOWED_SHARE))
    assert allowed == 26
    sg.check(1344, path)
    sg.check(1344 - allowed, path)
    with pytest.raises(sg.ScheduleShrank, match='1317 games against 1344'):
        sg.check(1344 - allowed - 1, path)


def test_a_small_season_still_allows_a_few(tmp_path):
    path = tmp_path / 'schedule_2026.json'
    write(path, 40)
    sg.check(35, path)
    with pytest.raises(sg.ScheduleShrank):
        sg.check(34, path)


NOW = datetime(2026, 10, 10, 16, 30, tzinfo=UTC)


@pytest.mark.parametrize('sport', ['nhl', 'nba'])
def test_an_empty_feed_stops_the_daily_run_before_anything_is_written(sport, tmp_path, monkeypatch):
    if sport == 'nhl':
        from src.sports.nhl import daily
        target = daily.nhl_schedule
    else:
        from src.sports.nba import daily
        target = daily.nba_schedule
    paths = temp_paths(tmp_path, sport)
    monkeypatch.setattr(daily, 'PATHS', paths)
    paths.results.mkdir(parents=True, exist_ok=True)
    committed = paths.results / 'schedule_2026.json'
    shutil.copy(ROOT / 'results' / sport / 'schedule_2026.json', committed)
    before = committed.read_bytes()
    empty = committed_schedule(sport, 2026, NOW).iloc[0:0]
    monkeypatch.setattr(target, 'load_schedule', lambda *a, **k: empty.copy())

    def nothing_else(*a, **k):
        raise AssertionError('the run went on past an empty schedule')
    monkeypatch.setattr(daily, 'refresh_season', nothing_else)
    with pytest.raises(sg.ScheduleShrank, match='no games at all'):
        daily.main(now=NOW, get=nothing_else)
    assert committed.read_bytes() == before
    assert sorted(p.name for p in paths.results.iterdir()) == ['schedule_2026.json']
    assert not (tmp_path / 'predictions').exists() or not any((tmp_path / 'predictions').rglob('*.json'))


def test_a_season_feed_does_not_shrink_in_the_committed_record():
    """The premise: a schedule keeps a postponed game with its status, so the
    committed files hold whole seasons."""
    for sport, n in (('nhl', 1300), ('nba', 1200)):
        doc = json.loads((ROOT / 'results' / sport / 'schedule_2026.json').read_text(encoding='utf-8'))
        assert len(doc['games']) >= n
        assert len(pd.DataFrame(doc['games'])['game_id'].unique()) == len(doc['games'])
