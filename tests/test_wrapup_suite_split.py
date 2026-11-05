"""Stage 86 item 4 (the 2026-11-02 review): the suite figure is shown with
its split, and the split is checked like the figure.

CLAUDE.md's `Suite:` line is followed by a sentence splitting it into the
mutation corpus's per-case checks and the behavioural tests. The figure was
checked against a real run at every wrap-up; the split was not, so it could
go stale while the check beside it passed. session_wrapup now collects
tests/test_mutation_corpus.py and checks both halves.

Run with: pytest tests/test_wrapup_suite_split.py -v
"""
from pathlib import Path
from types import SimpleNamespace

from src.agents import session_wrapup as sw

ROOT = Path(__file__).resolve().parents[1]

LINE = ("Suite: **100 passing** (no skips). The split (Stage 86 item 4): 60 of them are "
        "`tests/test_mutation_corpus.py`'s\nper-case checks of the corpus, and 40 are behavioural tests.")


def test_claude_md_states_the_split_in_the_words_the_check_reads():
    text = (ROOT / 'CLAUDE.md').read_text(encoding='utf-8')
    claimed = int(sw.COUNT_RE.search(text).group(1).replace(',', ''))
    m = sw.SPLIT_RE.search(text)
    assert m, 'CLAUDE.md no longer splits the suite figure in the words session_wrapup reads'
    assert int(m.group(1)) + int(m.group(2)) == claimed, 'the two halves do not add up to the figure'


def test_a_true_split_passes():
    got = sw.check_split(LINE, 100, 60)
    assert got.ok and '60 corpus checks, 40 behavioural tests' in got.detail


def test_a_stale_split_fails_and_says_what_is_real():
    got = sw.check_split(LINE, 100, 70)
    assert not got.ok
    assert 'splits 100 as 60 corpus checks and 40 behavioural' in got.detail and 'gives 70 and 30' in got.detail


def test_a_figure_with_no_split_fails():
    assert not sw.check_split('Suite: **100 passing**.', 100, 60).ok


def test_a_corpus_that_cannot_be_collected_fails():
    got = sw.check_split(LINE, 100, None)
    assert not got.ok and 'could not collect' in got.detail


def test_the_collection_line_is_read():
    assert sw.parse_collected('...\n7141 tests collected in 2.10s\n') == 7141
    assert sw.parse_collected('1 test collected in 0.01s') == 1
    assert sw.parse_collected('no tests ran') is None


def test_the_wrapup_collects_the_corpus_file_and_checks_the_split(tmp_path, monkeypatch):
    doc = tmp_path / 'CLAUDE.md'
    doc.write_text(LINE, encoding='utf-8')
    monkeypatch.setattr(sw, 'DOC', doc)
    calls = []

    def run(cmd, **kw):
        calls.append(cmd)
        if '--collect-only' in cmd:
            return SimpleNamespace(stdout='70 tests collected in 1.0s\n')
        return SimpleNamespace(stdout='100 passed in 9.0s\n')

    monkeypatch.setattr(sw.subprocess, 'run', run)
    got = sw.check_suite_count()
    assert not got.ok and 'gives 70 and 30' in got.detail
    assert calls[-1][-1] == sw.CORPUS_TESTS and '--collect-only' in calls[-1]
