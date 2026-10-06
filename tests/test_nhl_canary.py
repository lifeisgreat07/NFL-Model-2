"""The NHL's nightly canary: every step runs, one failure does not hide the
others, and any failure fails the night.

Run with: pytest tests/test_nhl_canary.py -v
"""
from datetime import UTC, datetime

from src.sports.nhl import canary

NOW = datetime(2026, 10, 10, 6, 0, tzinfo=UTC)


def ok(state):
    return 'fine'


def boom(state):
    raise ValueError('the feed changed shape')


def test_a_failing_step_is_recorded_and_the_rest_still_run():
    errors, notes = canary.run(NOW, steps=[('a', boom), ('b', ok)])
    assert errors == ['a raised ValueError: the feed changed shape']
    assert notes[1] == 'b: fine' and notes[0].startswith('a: FAILED')


def test_any_error_fails_the_night_and_the_report_says_which(tmp_path, monkeypatch):
    monkeypatch.setattr(canary, 'STEPS', [('market', boom), ('roster', ok)])
    report = tmp_path / 'r.md'
    assert canary.main(['--report', str(report)], now=NOW) == 1
    text = report.read_text()
    assert '## Errors' in text and 'market raised ValueError' in text


def test_a_clean_night_passes(tmp_path, monkeypatch):
    monkeypatch.setattr(canary, 'STEPS', [('roster', ok)])
    assert canary.main([], now=NOW) == 0


def test_every_read_the_daily_run_makes_has_a_step():
    assert [name for name, _ in canary.STEPS] == ['schedule', 'lock', 'box score', 'market', 'goalies', 'roster']
