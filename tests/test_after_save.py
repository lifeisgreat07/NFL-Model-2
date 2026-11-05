"""Stage 91 item 3 (audit 7, R3): nothing after save_once can lose the slate.

Audit 7 made the steps after the picks are saved raise on real inputs (a final
with no score in the standings, an unknown team code, a duplicated game id in
grading): the picks were on disk, the run failed, the workflow skipped its
commit, and the slate lived only in the run's artifact. Here the same steps
raise inside a whole daily run of each sport; the run must exit 0 with every
locked game's pick saved and a DEGRADED line for each failed step, which the
workflow raises an issue on.

Run with: pytest tests/test_after_save.py -v
"""
import json
from datetime import UTC, datetime

import pytest

from src.core import after_save
from tests.test_daily_end_to_end import committed_schedule, temp_paths
from tests.test_nhl_sources_down import drive


def test_a_step_that_raises_says_degraded_and_returns_none(capsys):
    def boom(x):
        raise TypeError(f'no score for {x}')
    assert after_save.guarded('standings', boom, 'game 1') is None
    assert capsys.readouterr().out == 'DEGRADED: standings: TypeError: no score for game 1\n'
    assert after_save.guarded('grading', lambda a, b=0: a + b, 1, b=2) == 3


def fail(why):
    def raise_it(*a, **k):
        raise ValueError(why)
    return raise_it


@pytest.mark.slow
def test_the_nhl_run_keeps_its_picks_when_every_later_step_fails(tmp_path, monkeypatch, capsys):
    from src.sports.nhl import daily
    for name in ('write_standings', 'grade', 'write_page_inputs'):
        monkeypatch.setattr(daily, name, fail(f'{name} broke'))
    monkeypatch.setattr(daily.forward_test, 'write', fail('forward broke'))
    monkeypatch.setattr(daily.m2, 'write', fail('m2 broke'))
    monkeypatch.setattr(daily.drift, 'baseline', fail('drift broke'))
    out, picks = drive(tmp_path, monkeypatch, capsys)   # asserts exit 0 and one pick per locked game
    for step in ('standings', 'grading', 'page inputs', 'drift check', 'forward test', 'M2'):
        assert f'DEGRADED: {step}: ValueError' in out, step


@pytest.mark.slow
def test_the_nba_run_keeps_its_picks_when_every_later_step_fails(tmp_path, monkeypatch, capsys):
    from src.sports.nba import daily, history
    now = datetime(2026, 10, 20, 16, 5, tzinfo=UTC)
    sched = committed_schedule('nba', 2026, now)
    monkeypatch.setattr(daily, 'PATHS', temp_paths(tmp_path, 'nba'))
    monkeypatch.setattr(daily.nba_schedule, 'load_schedule', lambda s, *a, **k: sched.copy())
    real_refresh = daily.refresh_season
    monkeypatch.setattr(daily, 'refresh_season',
                        lambda s, sc, *a, **k: real_refresh(s, sc, folder=history.HISTORY, get=k.get('get')))
    monkeypatch.setattr(daily, 'grade', fail('duplicate game id 1'))
    monkeypatch.setattr(daily.market, 'record', fail('market broke'))
    monkeypatch.setattr(daily.forward_test, 'write', fail('forward broke'))
    monkeypatch.setattr(daily.m2, 'write', fail('m2 broke'))
    monkeypatch.setattr(daily.drift, 'baseline', fail('drift broke'))

    def get(url):
        raise OSError(f'offline: {url}')
    assert daily.main(now=now, get=get) == 0
    out = capsys.readouterr().out
    saved = [ln for ln in out.splitlines() if ln.startswith('saved ')]
    picks = sorted((tmp_path / 'predictions' / '2026').glob('*.json'))
    assert saved and len(picks) == len(saved), out[-2000:]
    assert all(json.loads(p.read_text(encoding='utf-8'))['pick'] for p in picks)
    for step in ('market record', 'grading', 'drift check', 'forward test', 'M2'):
        assert f'DEGRADED: {step}: ValueError' in out, step
