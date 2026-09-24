"""
Tests for src/booth_fixture_runner.py, and the free re-check of every baseline.

Two jobs. The first is ordinary: does the runner assemble a fixture into a
repo that faithfully models the pull request it describes. The second is the
one that matters continuously -- every recorded baseline must still satisfy
its fixture's expectation, checked on every suite run at no cost, so that a
result recorded weeks ago cannot quietly stop meaning what it said.

The subtle failure this guards against: someone edits a fixture's expectation
-- names a different path, switches assertion form -- while a baseline sits
there recording a pass for the OLD question. The corpus would keep reporting
green for a question nobody is asking any more. So check_one() re-derives the
answer from the stored verdict rather than trusting the stored flag, and
test_a_baseline_is_rechecked_not_trusted proves it.

Run with: pytest tests/test_booth_fixture_runner.py -v
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / 'src'))
sys.path.insert(0, str(REPO / 'tests' / 'booth_fixtures'))

import booth_fixture_runner as runner  # noqa: E402
import loader  # noqa: E402

FIXTURES = loader.load_all()
IDS = [m['id'] for m in FIXTURES]


def _git(cwd, *args):
    return subprocess.run(
        ('git',) + args, cwd=cwd, capture_output=True, text=True,
    ).stdout


# --- assembling -------------------------------------------------------------

@pytest.mark.parametrize('meta', FIXTURES, ids=IDS)
def test_assemble_builds_two_real_commits(meta, tmp_path):
    """Booth's procedure runs git commands, so the fixture must answer them.

    A patch file would test something different from the audits this is
    modelling -- the protocol says to re-execute `git log`, `git diff`,
    `git show`, and a fixture that cannot is not a rehearsal of the real thing.
    """
    base, head = runner.assemble(meta, tmp_path / 'r')
    assert base != head
    log = _git(tmp_path / 'r', 'log', '--oneline', 'main..fixture-pr')
    assert log.strip(), 'no commit separates the head branch from main'


@pytest.mark.parametrize(
    'meta', [m for m in FIXTURES if m['assertion'] == 'file-locus'],
    ids=[m['id'] for m in FIXTURES if m['assertion'] == 'file-locus'],
)
def test_the_seeded_defect_reaches_the_diff(meta, tmp_path):
    """If the defect is not in the diff, Booth is being asked a question the
    fixture does not actually pose."""
    runner.assemble(meta, tmp_path / 'r')
    diff = _git(tmp_path / 'r', 'diff', 'main..fixture-pr')
    defect = meta['seeded_defect']
    assert defect['file'] in diff, (
        '{}: {} does not appear in the diff'.format(meta['id'], defect['file']))
    assert defect['contains'] in diff, (
        '{}: the seeded string {!r} is not in the diff Booth would '
        'read'.format(meta['id'], defect['contains']))


@pytest.mark.parametrize('meta', FIXTURES, ids=IDS)
def test_the_description_is_written_where_the_prompt_says(meta, tmp_path):
    runner.assemble(meta, tmp_path / 'r')
    body = (tmp_path / 'r' / 'PR_BODY.md')
    assert body.is_file(), 'PR_BODY.md missing; the prompt points at it'
    assert body.read_text(encoding='utf-8') == loader.body(meta)


@pytest.mark.parametrize('meta', FIXTURES, ids=IDS)
def test_the_protocol_travels_with_the_fixture(meta, tmp_path):
    """The prompt says to read BOOTH_PROTOCOL.md 'in this checkout'."""
    runner.assemble(meta, tmp_path / 'r')
    assert (tmp_path / 'r' / 'BOOTH_PROTOCOL.md').is_file()


@pytest.mark.parametrize('meta', FIXTURES, ids=IDS)
def test_assembling_twice_does_not_accumulate(meta, tmp_path):
    """A stale file left from a previous run would silently change the diff."""
    dest = tmp_path / 'r'
    runner.assemble(meta, dest)
    (dest / 'LEFTOVER.md').write_text('junk', encoding='utf-8')
    runner.assemble(meta, dest)
    assert not (dest / 'LEFTOVER.md').exists()


def test_a_file_dropped_by_head_is_deleted_not_left_behind(tmp_path):
    """A deletion must show as a deletion in the diff.

    Written against a synthetic fixture rather than a real one, because no
    current fixture removes a file -- and a guard that no fixture exercises
    would pass while doing nothing.
    """
    meta = {
        'id': 'synthetic', 'assertion': 'no-locus',
        '_path': tmp_path / 'fx',
    }
    (tmp_path / 'fx' / 'base').mkdir(parents=True)
    (tmp_path / 'fx' / 'head').mkdir(parents=True)
    (tmp_path / 'fx' / 'base' / 'gone.md').write_text('x', encoding='utf-8')
    (tmp_path / 'fx' / 'head' / 'kept.md').write_text('y', encoding='utf-8')
    (tmp_path / 'fx' / 'body.md').write_text('A body\n', encoding='utf-8')

    runner.assemble(meta, tmp_path / 'r')
    diff = _git(tmp_path / 'r', 'diff', 'main..fixture-pr', '--stat')
    assert 'gone.md' in diff, 'the removed file does not appear in the diff'
    assert not (tmp_path / 'r' / 'gone.md').exists()


def test_the_default_output_directory_is_hidden_from_pytest():
    """An assembled fixture must not become part of this project's suite.

    A fixture's head tree contains `test_guard.py` at its root. Assembled into
    a plainly-named directory in the repo -- `fixture-repo/`, say -- pytest
    collects it as an ordinary test of THIS project. That happened: a stray
    assembled repo added a test to the suite and the count moved by one with
    no code change, which took real time to explain.

    `tests/booth_fixtures/conftest.py` does not help, because the assembled
    copy lives outside that tree. What saves it is that pytest skips
    dot-prefixed directories by default -- load-bearing behaviour resting on a
    naming coincidence, so it is asserted here rather than left implicit.

    A fixture is a deliberately bad pull request. The first one that seeds a
    genuinely failing test would fail this project's real suite from a
    directory nobody thinks of as source.
    """
    meta = FIXTURES[0]
    default = runner.REPO / '.fixture-run' / meta['id']
    rel = default.relative_to(runner.REPO)
    assert any(part.startswith('.') for part in rel.parts), (
        'the default assemble target is {}, which pytest will collect from. '
        'An assembled fixture carries its own test files; they would join '
        'this suite.'.format(rel)
    )


# --- the prompt -------------------------------------------------------------

def test_the_prompt_names_the_head_and_the_body():
    meta = FIXTURES[0]
    text = runner.prompt(meta, 'abcdef1234')
    assert 'abcdef1' in text
    assert 'PR_BODY.md' in text
    assert 'git diff main..fixture-pr' in text
    assert 'booth-verdict' in text, (
        'the prompt must ask for the machine-readable block, or record() has '
        'nothing to parse'
    )


# --- recording and re-checking ---------------------------------------------

def _report(verdict_json, discrepancies=1, confirmed=0, overall='NEEDS HUMAN REVIEW'):
    return (
        '## Booth Audit: PR #0\n\n'
        'Head commit audited: `abc1234`\n'
        'Description read at: 2026-09-07T00:00:00Z\n\n'
        'Claims checked: {}\nConfirmed: {}\nDiscrepancies: {}\nUnverifiable: 0\n\n'
        '### Overall verdict\n{}\n\n'
        '```booth-verdict\n{}\n```\n'
    ).format(confirmed + discrepancies, confirmed, discrepancies, overall,
             verdict_json)


def _satisfying_verdict(meta):
    if meta['assertion'] == 'file-locus':
        claims = [{'id': 1, 'verdict': 'DISCREPANCY',
                   'implicates': [meta['expect_discrepancy_implicating']]}]
    else:
        claims = [{'id': 1, 'verdict': 'DISCREPANCY', 'implicates': []}]
    return json.dumps({'pr': 0, 'head': 'abc1234', 'claims': claims,
                       'overall': 'NEEDS HUMAN REVIEW'}, indent=2)


#: The full SHA of the commit the synthetic verdicts above say they audited
#: (they report the short form, `abc1234`, as Booth does).
FULL_HEAD = 'abc1234' + '0' * 33


def test_record_writes_a_baseline_and_reports_satisfied(tmp_path, monkeypatch):
    meta = dict(FIXTURES[0])
    meta['_path'] = tmp_path
    ok, why = runner.record(meta, _report(_satisfying_verdict(meta)), FULL_HEAD)
    assert ok, why
    saved = json.loads((tmp_path / 'baseline.json').read_text(encoding='utf-8'))
    assert saved['fixture'] == meta['id']
    assert saved['satisfied'] is True
    assert saved['fixture_head'] == FULL_HEAD
    assert saved['verdict']['claims'][0]['verdict'] == 'DISCREPANCY'


def test_a_failing_result_is_still_recorded(tmp_path):
    """A fixture Booth MISSED is the most important thing to have on record.

    Writing only successes would mean the corpus silently forgets the runs
    that matter most, and the failure would be invisible until someone
    happened to spend an audit re-running it.
    """
    meta = dict(FIXTURES[0])
    meta['_path'] = tmp_path
    clean = json.dumps({
        'pr': 0, 'head': 'abc1234',
        'claims': [{'id': 1, 'verdict': 'CONFIRMED', 'implicates': []}],
        'overall': 'SAFE TO MERGE',
    })
    ok, why = runner.record(meta, _report(clean, discrepancies=0, confirmed=1,
                                          overall='SAFE TO MERGE'), 'deadbee')
    assert not ok
    saved = json.loads((tmp_path / 'baseline.json').read_text(encoding='utf-8'))
    assert saved['satisfied'] is False
    assert 'no DISCREPANCY implicated' in saved['explanation']


def test_a_missing_block_records_as_unsatisfied(tmp_path):
    meta = dict(FIXTURES[0])
    meta['_path'] = tmp_path
    ok, why = runner.record(meta, '## Booth Audit\n\nno block here\n', 'dead')
    assert not ok
    assert 'no booth-verdict block' in why


def test_a_baseline_is_rechecked_not_trusted(tmp_path):
    """The subtle one.

    A baseline records `satisfied: true` for the question asked at the time.
    If the fixture's expectation is later edited to name a different path, the
    recorded pass must stop counting -- otherwise the corpus keeps reporting
    green for a question nobody is asking any more.
    """
    meta = dict(FIXTURES[0])
    meta['_path'] = tmp_path
    meta['assertion'] = 'file-locus'
    meta['expect_discrepancy_implicating'] = 'original.py'
    verdict = json.dumps({
        'pr': 0, 'head': 'abc1234',
        'claims': [{'id': 1, 'verdict': 'DISCREPANCY',
                    'implicates': ['original.py']}],
        'overall': 'NEEDS HUMAN REVIEW'})
    ok, _ = runner.record(meta, _report(verdict), FULL_HEAD)
    assert ok

    # The expectation moves; the stored flag still says true.
    saved = json.loads((tmp_path / 'baseline.json').read_text(encoding='utf-8'))
    assert saved['satisfied'] is True
    meta['expect_discrepancy_implicating'] = 'somewhere_else.py'

    rechecked, why = runner.check_one(meta)
    assert rechecked is False, (
        'check_one trusted the stored flag instead of re-deriving the answer; '
        'a moved expectation would keep reporting a stale pass'
    )
    assert 'somewhere_else.py' in why


# --- the free, always-on check ---------------------------------------------

@pytest.mark.parametrize('meta', FIXTURES, ids=IDS)
def test_every_recorded_baseline_still_satisfies_its_fixture(meta):
    """Free on every suite run. A fixture with no baseline yet is not a
    failure -- recording one costs usage and is done deliberately."""
    ok, why = runner.check_one(meta)
    if ok is None:
        pytest.skip('{}: {}'.format(meta['id'], why))
    assert ok, '{}: {}'.format(meta['id'], why)


# --- the commit a baseline is about ----------------------------------------

def test_a_verdict_about_another_commit_is_not_a_pass(tmp_path):
    """The first CI run recorded head dad39d0 for an audit of 9d2d81e.

    The record job re-assembled the fixture, and a fresh assembly makes fresh
    commits with fresh hashes. A result is only about the commit Booth
    audited, so a verdict naming a different head must not record as
    satisfied -- and must still be written, so the mismatch is on the record.
    """
    meta = dict(FIXTURES[0])
    meta['_path'] = tmp_path
    ok, why = runner.record(meta, _report(_satisfying_verdict(meta)), 'deadbee' * 5)
    assert not ok
    assert 'Booth audited' in why
    saved = json.loads((tmp_path / 'baseline.json').read_text(encoding='utf-8'))
    assert saved['satisfied'] is False


def test_a_baseline_whose_heads_disagree_fails_the_recheck(tmp_path):
    """check_one re-derives from the verdict, so it must re-check the head too."""
    meta = dict(FIXTURES[0])
    meta['_path'] = tmp_path
    ok, why = runner.record(meta, _report(_satisfying_verdict(meta)), FULL_HEAD)
    assert ok, why
    path = tmp_path / 'baseline.json'
    saved = json.loads(path.read_text(encoding='utf-8'))
    saved['fixture_head'] = 'dad39d0' + '0' * 33
    path.write_text(json.dumps(saved), encoding='utf-8')
    rechecked, why = runner.check_one(meta)
    assert rechecked is False
    assert 'Booth audited' in why


@pytest.mark.parametrize('booth, ours, expected', [
    ('abc1234', 'abc1234' + '0' * 33, True),
    ('ABC1234', 'abc1234' + '0' * 33, True),
    ('abc1235', 'abc1234' + '0' * 33, False),
    ('', 'abc1234', False),
    ('abc1234', None, False),
    # Under seven characters a prefix matches too many commits to name one.
    ('abc12', 'abc1234' + '0' * 33, False),
    # The corrected fixed-everywhere baseline stores the short form Booth
    # reported, so a short recorded head must still match a full one.
    ('abc1234' + '0' * 33, 'abc1234', True),
])
def test_head_matching(booth, ours, expected):
    assert runner.head_matches(ours, {'head': booth}) is expected


def test_record_with_a_head_does_not_reassemble(tmp_path, monkeypatch):
    """`record --head` is what the CI record job uses. It must record that
    head, not build a second repository and record the new one's."""
    meta = FIXTURES[0]

    def _no_assembly(*_a, **_k):
        raise AssertionError('record --head re-assembled the fixture')

    monkeypatch.setattr(runner, 'assemble', _no_assembly)
    monkeypatch.setattr(runner, 'baseline_path', lambda m: tmp_path / 'baseline.json')
    report = tmp_path / 'r.md'
    report.write_text(_report(_satisfying_verdict(meta)), encoding='utf-8')
    code = runner.main(['record', meta['id'], '--report', str(report),
                        '--head', FULL_HEAD])
    saved = json.loads((tmp_path / 'baseline.json').read_text(encoding='utf-8'))
    assert saved['fixture_head'] == FULL_HEAD
    assert code == 0


# --- the description has to describe the fixture ----------------------------

_COUNT_WORDS = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5}


@pytest.mark.parametrize('meta', FIXTURES, ids=IDS)
def test_the_description_counts_the_commits_the_fixture_has(meta, tmp_path):
    """A fixture must hold exactly the defect it names.

    fixed-everywhere's description said "Two commits." while assemble() builds
    one commit over main: an unplanted discrepancy sitting beside the planted
    one (the first run's claim 1 came back as a DISCREPANCY implicating
    PR_BODY.md). A body that states a commit count must state the one the
    assembled branch has.
    """
    import re
    stated = re.findall(r'\b(one|two|three|four|five|\d+) commits?\b',
                        loader.body(meta), flags=re.IGNORECASE)
    if not stated:
        pytest.skip('{} states no commit count'.format(meta['id']))
    runner.assemble(meta, tmp_path / 'r')
    actual = len(_git(tmp_path / 'r', 'rev-list', 'main..fixture-pr').split())
    for word in stated:
        n = int(word) if word.isdigit() else _COUNT_WORDS[word.lower()]
        assert n == actual, (
            '{}: the description says {} commit(s); the assembled branch has '
            '{}'.format(meta['id'], word, actual))
