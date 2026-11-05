"""The slow-test policy, on fixture test files (Stage 96 item 49; audit 7, T12, T13).

tests/test_tasks.py holds the real suite to tests/slow_policy.py. Here the
policy itself is held: it must catch a test marked for nothing as well as a
slow one left unmarked, read the helper a test drives the run through, and
leave a run that is expected to stop early alone.

Run with: pytest tests/test_slow_policy.py -v
"""
from tests import slow_policy

HELPER = '''
def drive():
    assert daily.main(now=NOW, get=get) == 0
'''

TESTS = '''
import pytest

from tests.test_helper import drive


@pytest.mark.slow
def test_marked_for_nothing():
    assert 1 + 1 == 2


def test_an_unmarked_run():
    assert daily.main(now=NOW, get=get) == 0


def test_a_run_through_a_helper():
    drive()


@pytest.mark.slow
def test_a_marked_bootstrap():
    paired_bootstrap(y, a, b, n_resamples=600, seed=1)


def test_a_run_that_stops_early():
    with pytest.raises(ValueError):
        daily.main(now=NOW, get=get)


@pytest.mark.slow
def test_a_marked_re_derivation():
    games = backtest.load_history(first, 2025)
    table = ratings.features(games, h, [k])


def test_a_fixture_history_read():
    g, m = backtest.load_history(2024, 2024, tmp_path)
'''


def test_a_marker_and_its_reason_go_together(tmp_path):
    (tmp_path / 'test_helper.py').write_text(HELPER, encoding='utf-8')
    (tmp_path / 'test_fixture.py').write_text(TESTS, encoding='utf-8')
    got = slow_policy.violations(tmp_path)
    assert got == [
        'test_fixture.py::test_marked_for_nothing is marked slow and does none of the slow things',
        'test_fixture.py::test_an_unmarked_run does a whole daily run and is not marked slow',
        'test_fixture.py::test_a_run_through_a_helper does a whole daily run and is not marked slow',
    ]
