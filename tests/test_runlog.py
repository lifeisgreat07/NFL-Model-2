"""
The pipeline logs through src/pipeline/runlog.py, and what it writes is exactly what
print() wrote (Stage 32 item 17).

src/pipeline/weekly_summary.py parses the weekly run's log, so a changed line is a
broken summary. The handler must write the bare message and a newline, to
whatever sys.stdout is at that moment, and fail the way print failed.

Run with: pytest tests/test_runlog.py -v
"""
import importlib
import io
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

from src.pipeline import runlog

#: The modules converted from print(). A module joins when it is converted.
LOGGED = ['weekly_update', 'grade_predictions', 'weekend_refresh', 'check_drift']


def test_a_line_is_the_bare_message_and_a_newline(capsys):
    log = runlog.get_logger('test_bare')
    log.info('Saved 4 predictions to predictions/2026_week5.json')
    log.warning('WARNING: KC@BUF has already kicked off and gets NO pick.')
    log.info('\nNOTE: run grade_predictions.py separately.')
    assert capsys.readouterr().out == (
        'Saved 4 predictions to predictions/2026_week5.json\n'
        'WARNING: KC@BUF has already kicked off and gets NO pick.\n'
        '\nNOTE: run grade_predictions.py separately.\n')


def test_the_stream_is_whatever_stdout_is_when_the_line_is_written(monkeypatch):
    """Made first, then stdout swapped: the line must follow the swap."""
    log = runlog.get_logger('test_swap')
    first, second = io.StringIO(), io.StringIO()
    monkeypatch.setattr(sys, 'stdout', first)
    log.info('one')
    monkeypatch.setattr(sys, 'stdout', second)
    log.info('two')
    assert (first.getvalue(), second.getvalue()) == ('one\n', 'two\n')


def test_a_percent_sign_is_written_as_it_is(capsys):
    """print wrote '62.7%' as it was; so must the log, with no %-formatting."""
    runlog.get_logger('test_pct').info('Model A: 62.7% (5/8) correct')
    assert capsys.readouterr().out == 'Model A: 62.7% (5/8) correct\n'


def test_asking_twice_adds_no_second_handler(capsys):
    """Every module import asks for its logger; a second handler would print
    every line twice."""
    runlog.get_logger('test_twice')
    runlog.get_logger('test_twice').info('once')
    assert capsys.readouterr().out == 'once\n'


def test_nothing_reaches_the_root_logger(capsys):
    """A root handler (pytest's, or a caller's basicConfig) would print the
    line a second time."""
    import logging
    seen = []

    class Grab(logging.Handler):
        def emit(self, record):
            seen.append(record.getMessage())
    root = logging.getLogger()
    grab = Grab()
    root.addHandler(grab)
    try:
        runlog.get_logger('test_root').info('only once')
    finally:
        root.removeHandler(grab)
    assert seen == [] and capsys.readouterr().out == 'only once\n'


def test_a_line_that_cannot_be_written_fails_like_print(monkeypatch):
    """logging's default reports a write error to stderr and carries on,
    dropping the line; print raised."""
    class Broken(io.StringIO):
        def write(self, s):
            raise UnicodeEncodeError('cp1252', s, 0, 1, 'cannot encode')
    monkeypatch.setattr(sys, 'stdout', Broken())
    with pytest.raises(UnicodeEncodeError):
        runlog.get_logger('test_broken').info('−')


@pytest.mark.parametrize('name', LOGGED)
def test_the_converted_modules_log_and_never_print(name):
    code = re.sub(r'(?m)#.*$', '', next((ROOT / 'src').glob(f'*/{name}.py')).read_text(encoding='utf-8'))
    assert not re.search(r'(?<![\w.])print\(', code), f'{name} prints again'
    assert re.search(r'(?m)^log = get_logger\(__name__\)$', code), f'{name} has no logger'


@pytest.mark.parametrize('name', LOGGED)
def test_the_converted_modules_are_bound_to_the_one_handler(name):
    module = importlib.import_module(f'src.pipeline.{name}')
    assert any(isinstance(h, runlog._StdoutHandler) for h in module.log.handlers)
