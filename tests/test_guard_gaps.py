"""
The queued preflight and README guard gaps, closed 2026-09-22. One test group
per gap, each written from the failure that queued it:

  1. check_test_count read '125 passed' in single quotes, and `125 passed` in
     inline code, as the body's own claim. Double quotes were already stripped.
  2. The commit-message count check matched suite-shaped counts only; PR #68's
     "147 individual cases" walked through it.
  3. The README said "N cases" where its guard counts FILES.
  4. A mutation figure quoted from an `--id` glob had no check at all (#72).
  5. check_visual_claims_have_artifacts told authors to write a process note
     and had no process-note branch (2026-09-21).
  6. VISUAL_CLAIM_RE fired on "screenshot" inside a disclaimer and missed
     "rendered ... and read on screen".
  7. session_wrapup.py read only the PASSED count, so a red suite looked like
     a stale figure. scout_preflight.py had been fixed for this in 9c3e320.

Plus one tool defect in the same family: runner.py kept only the LAST --id and
still printed "all caught".

Run with: pytest tests/test_guard_gaps.py -v
"""
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tests' / 'mutation'))

import scout_preflight as pf  # noqa: E402
import session_wrapup as sw  # noqa: E402
import runner  # noqa: E402


# ------------------------------------------------------------ 1. quotations

@pytest.fixture
def suite_of(monkeypatch):
    def set_(n):
        monkeypatch.setattr(pf, 'run_test_suite', lambda: (n, 0, None))
    return set_


@pytest.mark.parametrize('quoted', [
    "Booth said '125 passed' on #21.",
    "Booth's report said `125 passed` on #21.",
    "Booth said ‘125 passed’ on #21.",
])
def test_a_quoted_past_count_is_not_a_claim(suite_of, quoted):
    suite_of(1383)
    f = pf.check_test_count(pf.strip_quotations(quoted + " Now 1383 passed."), False)
    assert f.ok, f.detail


def test_an_apostrophe_is_not_a_quote_mark():
    # Both kinds of apostrophe: one inside a word, one closing a plural
    # possessive. Paired up as quote marks they would swallow the claim.
    body = "Booth's run gave 1300 passed and the teams' notes agree."
    assert '1300 passed' in pf.strip_quotations(body)


def test_inline_code_naming_a_module_survives_so_scoped_counts_still_see_it():
    body = "`tests/test_guard_gaps.py`: 9 tests."
    assert 'test_guard_gaps' in pf.strip_quotations(body)


def test_an_unquoted_wrong_count_still_fails(suite_of):
    suite_of(1383)
    assert not pf.check_test_count(pf.strip_quotations("Now 1380 passed."), False).ok


# ------------------------------------------------------- 2. commit messages

@pytest.mark.parametrize('text', [
    '147 individual cases', '13 mutation cases', '237 CAUGHT', '22 tests',
    '1383 passed', '1383 passing', '682 collected',
])
def test_verification_counts_in_a_commit_message_are_caught(text):
    assert pf.COMMIT_SUITE_COUNT_RE.search(f"Adds a guard. {text}.")


@pytest.mark.parametrize('text', [
    '3 tests still pass', 'the 2026 week 3 slate', 'matched on 1599 rows', 'Stage 5 accepted nothing',
])
def test_ordinary_numbers_in_a_commit_message_are_not(text):
    assert not pf.COMMIT_SUITE_COUNT_RE.search(text)


# ------------------------------------------------------------- 3. README

def test_the_readme_calls_its_count_case_files():
    text = (ROOT / 'README.md').read_text(encoding='utf-8')
    m = re.search(r'`tests/mutation/`,\s*(\d+)\s*case files', text)
    assert m, "the README's mutation figure must say what it counts"
    assert int(m.group(1)) == len(list((ROOT / 'tests' / 'mutation' / 'cases').glob('*.json')))


# ------------------------------------------------ 4. mutation count scope

@pytest.mark.parametrize('body, ok', [
    ('`python tests/mutation/runner.py --id "p*"` gave 42 CAUGHT.', False),
    ("`python tests/mutation/runner.py --id 'stage5-*'` gave 6 CAUGHT.", False),
    ('`python tests/mutation/runner.py --id stage5-screen-passes-a-tie` CAUGHT.', True),
    ('`python tests/mutation/runner.py` (full corpus) gave 237 cases, all CAUGHT.', True),
    ('```\npython tests/mutation/runner.py --id "p*"\n```\nThat was the #72 mistake.', True),
])
def test_a_mutation_figure_from_a_glob_fails(body, ok):
    stripped = pf.BLOCKQUOTE_RE.sub('', pf.FENCED_RE.sub('', body))
    assert pf.check_mutation_count_scope(stripped).ok is ok


def test_preflight_runs_the_scope_check_on_text_where_the_glob_is_still_visible():
    src = (ROOT / 'src' / 'scout_preflight.py').read_text(encoding='utf-8')
    body = src[src.index('def preflight('):]
    assert "check_mutation_count_scope(BLOCKQUOTE_RE.sub('', FENCED_RE.sub('', body)))" in body, (
        "run over the quote-stripped text, the double-quoted glob is removed before it is looked for"
    )


# ------------------------------------------------- 5 and 6. visual claims

@pytest.mark.parametrize('sentence', [
    'I rendered the page and read the card on screen.',
    'Checked the new tooltip on screen in both themes.',
    'Here is a screenshot of the board.',
    'I looked at the page at 390px.',
    'Checked on screen that the card does not overflow at 320px.',
])
def test_real_visual_claims_are_seen(sentence):
    assert pf.visual_claim(sentence)


@pytest.mark.parametrize('sentence', [
    'Process note, not attached evidence: the screenshot tool here writes no file.',
    'Process note: I rendered the page and read the card on screen.',
    'Nobody has looked at the page yet.',
    'No screenshot is attached, because the tool writes no image.',
    'I took a screenshot but it is not attached.',
])
def test_disclosures_are_not_claims(sentence):
    assert pf.visual_claim(sentence) is None


def test_the_remedy_the_failure_names_is_a_branch_that_passes():
    claim = "I rendered the page and read the card on screen."
    failed = pf.check_visual_claims_have_artifacts(claim, claim, ['src/dashboard_template.html'])
    assert not failed.ok
    assert 'Process note:' in failed.detail
    remedied = "Process note: " + claim
    assert pf.check_visual_claims_have_artifacts(remedied, remedied, ['src/dashboard_template.html']).ok


# -------------------------------------------------------- 7. wrap-up count

@pytest.mark.parametrize('stdout, expected', [
    ('....\n1383 passed, 1 skipped, 26 warnings in 41.0s\n', (1383, 0)),
    ('F...\nFAILED tests/test_x.py::test_a\n1 failed, 1382 passed in 40s\n', (1382, 1)),
    ('E\n1 error, 1382 passed in 40s\n', (1382, 1)),
    ('FAILED tests/test_x.py::test_a - AssertionError: 12 failed rows\n1 failed, 5 passed\n', (5, 1)),
    ('no tests ran\n', (None, 0)),
])
def test_the_wrapup_reads_failures_from_the_final_summary_only(stdout, expected):
    assert sw.parse_summary(stdout) == expected


def test_the_wrapup_uses_the_parser():
    src = (ROOT / 'src' / 'session_wrapup.py').read_text(encoding='utf-8')
    body = src[src.index('def check_suite_count('):]
    assert 'parse_summary(run.stdout)' in body and 'if broken:' in body


# -------------------------------------------------------- runner --id

def test_every_id_given_is_run_once_in_corpus_order():
    corpus = [{'id': i} for i in ('a-1', 'b-1', 'a-2', 'c-1')]
    got = [c['id'] for c in runner.select_cases(corpus, ['c-1', 'a-*', 'a-1'])]
    assert got == ['a-1', 'a-2', 'c-1']


def test_repeated_id_flags_all_reach_the_selection(monkeypatch, capsys):
    monkeypatch.setattr(runner, 'load_corpus', lambda: [
        {'id': 'x', 'target': 't', 'expect_caught_by': 'g'},
        {'id': 'y', 'target': 't', 'expect_caught_by': 'g'},
        {'id': 'z', 'target': 't', 'expect_caught_by': 'g'}])
    assert runner.main(['--id', 'x', '--id', 'z', '--list']) == 0
    out = capsys.readouterr().out
    assert '2 case(s)' in out and ' x ' in out and ' z ' in out and ' y ' not in out
