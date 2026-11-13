"""Stage 96 item 51 (audit 7, T5): CLAUDE.md's suite figure is split five
ways by a committed map of test files, and the wrap-up fails when the map
misses a file.

Until Stage 86 item 4 the figure stood alone; then it was split two ways,
the mutation corpus's per-case checks and "behavioural tests", which
counted a test of a workflow's wording like a test of the model. Now each
test file has a class in tests/suite_classes.json, the wrap-up collects the
whole suite, and CLAUDE.md's sentence must be the one split_sentence writes.

Run with: pytest tests/test_wrapup_suite_split.py -v
"""
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

from src.agents import session_wrapup as sw

ROOT = Path(__file__).resolve().parents[1]
CLASSES = {'tests/test_mutation_corpus.py': 'corpus checks', 'tests/test_a.py': 'isolated behavioural',
           'tests/test_b.py': 'mixed', 'tests/test_c.py': 'template/JS', 'tests/test_d.py': 'workflow/docs/tests-of-tests'}
COUNTS = Counter({'tests/test_mutation_corpus.py': 60, 'tests/test_a.py': 20, 'tests/test_b.py': 10,
                  'tests/test_c.py': 6, 'tests/test_d.py': 4})
LINE = ('Suite: **100 passing** (no skips). The split (Stage 96 item 51, by `tests/suite_classes.json`): '
        '60 corpus checks, 20 isolated behavioural, 10 mixed, 6 template/JS, 4 workflow/docs/tests-of-tests.')


def test_claude_md_states_the_split_in_the_words_the_check_reads():
    text = (ROOT / 'CLAUDE.md').read_text(encoding='utf-8')
    claimed = int(sw.COUNT_RE.search(text).group(1).replace(',', ''))
    m = sw.SPLIT_RE.search(text)
    assert m, 'CLAUDE.md no longer splits the suite figure in the words session_wrapup reads'
    assert sum(int(g.replace(',', '')) for g in m.groups()) == claimed, 'the five parts do not add up to the figure'


def test_every_test_file_has_a_class():
    """The map is checked here on every commit, not only at a wrap-up: a new
    test file without a class fails this before it reaches main."""
    classes = sw.load_classes()
    # tests/booth_fixtures/ holds Booth's fixture repositories, whose tests pytest does not collect here.
    files = {p.relative_to(ROOT).as_posix() for p in (ROOT / 'tests').rglob('test_*.py')
             if 'booth_fixtures' not in p.parts}
    assert files - set(classes) == set(), 'add these to tests/suite_classes.json'
    assert set(classes) - files == set(), 'these are in tests/suite_classes.json but no longer exist'
    assert set(classes.values()) <= set(sw.CLASSES)


def test_a_true_split_passes():
    got = sw.check_split(LINE, 100, COUNTS, CLASSES)
    assert got.ok and '60 corpus checks, 20 isolated behavioural, 10 mixed' in got.detail


def test_a_stale_split_fails_and_gives_the_real_sentence():
    counts = COUNTS + Counter({'tests/test_a.py': 5})
    got = sw.check_split(LINE.replace('100 passing', '105 passing'), 105, counts, CLASSES)
    assert not got.ok and 'stale' in got.detail and '25 isolated behavioural' in got.detail


def test_a_file_the_map_misses_fails_the_wrapup():
    counts = COUNTS + Counter({'tests/test_new.py': 3})
    got = sw.check_split(LINE, 103, counts, CLASSES)
    assert not got.ok and "misses 1 test file(s): ['tests/test_new.py']" in got.detail


def test_a_mapped_file_no_longer_collected_fails():
    got = sw.check_split(LINE, 100, COUNTS, CLASSES | {'tests/test_gone.py': 'mixed'})
    assert not got.ok and 'no longer collected' in got.detail


def test_a_figure_with_no_split_fails():
    got = sw.check_split('Suite: **100 passing**.', 100, COUNTS, CLASSES)
    assert not got.ok and 'missing' in got.detail and sw.split_sentence({'corpus checks': 60}) .startswith('The split')


def test_a_skip_makes_the_split_differ_from_the_figure():
    got = sw.check_split(LINE, 99, COUNTS, CLASSES)
    assert not got.ok and '100 tests collected but 99 passed' in got.detail


def test_node_ids_are_counted_by_file():
    out = 'tests/test_a.py::test_x\ntests\\test_a.py::test_y[1]\ntests/test_b.py::T::test_z\n\n3 tests collected in 1.0s\n'
    assert sw.per_file(out) == Counter({'tests/test_a.py': 2, 'tests/test_b.py': 1})


def test_the_collection_line_is_read():
    assert sw.parse_collected('...\n7141 tests collected in 2.10s\n') == 7141
    assert sw.parse_collected('1 test collected in 0.01s') == 1
    assert sw.parse_collected('no tests ran') is None


def test_the_wrapup_collects_the_whole_suite_and_checks_the_split(tmp_path, monkeypatch):
    doc = tmp_path / 'CLAUDE.md'
    doc.write_text(LINE, encoding='utf-8')
    monkeypatch.setattr(sw, 'DOC', doc)
    monkeypatch.setattr(sw, 'load_classes', lambda path=None: CLASSES)
    calls = []
    ids = ''.join(f'{f}::test_{i}\n' for f, n in (COUNTS + Counter({'tests/test_a.py': 1})).items() for i in range(n))

    def run(cmd, **kw):
        calls.append(cmd)
        if '--collect-only' in cmd:
            return SimpleNamespace(stdout=ids + '101 tests collected in 1.0s\n')
        return SimpleNamespace(stdout='101 passed in 9.0s\n')

    monkeypatch.setattr(sw.subprocess, 'run', run)
    doc.write_text(LINE.replace('100 passing', '101 passing'), encoding='utf-8')
    got = sw.check_suite_count()
    assert not got.ok and '21 isolated behavioural' in got.detail
    assert '--collect-only' in calls[-1] and calls[-1][-1] == '-q'
