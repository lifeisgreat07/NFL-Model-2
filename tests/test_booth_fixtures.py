"""
Free, always-on integrity checks for the Booth regression fixtures.

These never invoke Booth. Running a fixture costs subscription usage, so it is
a manual dispatch; keeping the corpus honest costs nothing and therefore runs
on every suite run, exactly like tests/test_mutation_corpus.py does for the
mutation cases.

The failure these guard against is the worst kind: a fixture whose seeded
defect has quietly stopped being present. It would still "pass" when Booth
reported no discrepancy against it, and the suite would read as green while
measuring nothing. Same shape as the churn guard that covered one of two
workflows, and as a mutation caught by the wrong assertion.

Run with: pytest tests/test_booth_fixtures.py -v
"""
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent / 'booth_fixtures'))

import loader  # noqa: E402

FIXTURES = loader.load_all()
IDS = [m['id'] for m in FIXTURES]


def test_there_is_at_least_one_fixture():
    """Guard against an empty corpus passing every parametrised test."""
    assert FIXTURES, (
        "no fixtures found under tests/booth_fixtures/ -- every check below "
        "would vacuously pass"
    )


@pytest.mark.parametrize('meta', FIXTURES, ids=IDS)
def test_the_body_exists_and_says_something(meta):
    text = loader.body(meta)
    assert len(text.strip()) > 200, (
        f"{meta['id']}: body.md is too short to be a plausible PR description; "
        "Booth would have almost nothing to audit"
    )


@pytest.mark.parametrize('meta', FIXTURES, ids=IDS)
def test_head_actually_differs_from_base(meta):
    base, head = loader.base_tree(meta), loader.head_tree(meta)
    assert head, f"{meta['id']}: head/ is empty, so the fixture has no diff"
    assert base != head, (
        f"{meta['id']}: head/ is identical to base/. There is no pull request "
        "here for Booth to audit."
    )


@pytest.mark.parametrize(
    'meta', [m for m in FIXTURES if m['assertion'] == 'file-locus'],
    ids=[m['id'] for m in FIXTURES if m['assertion'] == 'file-locus'],
)
def test_the_seeded_defect_is_actually_present(meta):
    """The check that keeps this corpus meaningful.

    If the seeded string drifts out of the fixture, Booth reporting no
    discrepancy becomes correct, the fixture reports a pass, and the suite is
    green while testing nothing at all.
    """
    defect = meta['seeded_defect']
    head = loader.head_tree(meta)
    assert defect['file'] in head, (
        f"{meta['id']}: seeded_defect names {defect['file']!r}, which is not "
        f"in head/. Present: {sorted(head)}"
    )
    assert defect['contains'] in head[defect['file']], (
        f"{meta['id']}: {defect['file']} no longer contains "
        f"{defect['contains']!r}. The defect this fixture exists to seed is "
        "gone, so a clean audit would wrongly count as a pass."
    )


@pytest.mark.parametrize(
    'meta', [m for m in FIXTURES if m.get('seeded_defect', {}).get('unique_in_head')],
    ids=[m['id'] for m in FIXTURES if m.get('seeded_defect', {}).get('unique_in_head')],
)
def test_the_defect_string_survives_in_exactly_one_place(meta):
    """For 'partially fixed' fixtures, the partiality is the whole point.

    If the string is still in several files, the PR did not credibly fix
    anything and the defect is obvious rather than missable. If it is in none,
    see the test above.
    """
    defect = meta['seeded_defect']
    head = loader.head_tree(meta)
    carriers = sorted(p for p, text in head.items() if defect['contains'] in text)
    assert carriers == [defect['file']], (
        f"{meta['id']}: expected {defect['contains']!r} in exactly "
        f"{defect['file']!r}, found it in {carriers}. The fixture models a PR "
        "that fixed the string everywhere it looked and missed one place."
    )


@pytest.mark.parametrize(
    'meta', [m for m in FIXTURES if m['assertion'] == 'file-locus'],
    ids=[m['id'] for m in FIXTURES if m['assertion'] == 'file-locus'],
)
def test_the_implicated_path_exists_in_head(meta):
    head = loader.head_tree(meta)
    wanted = meta['expect_discrepancy_implicating']
    assert wanted in head, (
        f"{meta['id']}: expects a DISCREPANCY implicating {wanted!r}, but no "
        f"such file exists in head/. Booth could not name it. Present: "
        f"{sorted(head)}"
    )


@pytest.mark.parametrize(
    'meta', [m for m in FIXTURES if 'head_suite' in m],
    ids=[m['id'] for m in FIXTURES if 'head_suite' in m],
)
def test_the_fixtures_own_suite_behaves_as_declared(meta, tmp_path):
    """A fixture must isolate EXACTLY ONE defect.

    If the fixture's own tests fail, its body's test-count claim is false and
    Booth finds a second, unseeded discrepancy -- at which point the fixture
    no longer measures the class it names.
    """
    head = loader.head_tree(meta)
    for rel, text in head.items():
        dest = tmp_path / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding='utf-8')

    result = subprocess.run(
        [sys.executable, '-B', '-m', 'pytest', '-q'],
        cwd=tmp_path, capture_output=True, text=True,
    )
    expect_pass = meta['head_suite']['expect'] == 'passes'
    assert (result.returncode == 0) == expect_pass, (
        f"{meta['id']}: head_suite says the fixture's own tests "
        f"{meta['head_suite']['expect']}, but pytest returned "
        f"{result.returncode}.\n{result.stdout[-1500:]}"
    )


# --- the expectation logic itself, tested against synthetic verdicts ---

def _verdict(claims, overall='NEEDS HUMAN REVIEW'):
    return {'pr': 1, 'head': 'aaa', 'claims': claims, 'overall': overall}


def test_file_locus_is_satisfied_by_a_discrepancy_naming_the_path():
    meta = {'assertion': 'file-locus', 'expect_discrepancy_implicating': 'a.py'}
    ok, why = loader.satisfied_by(meta, _verdict([
        {'id': 1, 'verdict': 'DISCREPANCY', 'implicates': ['a.py']},
    ]))
    assert ok, why


def test_file_locus_is_not_satisfied_by_a_confirmed_naming_the_path():
    """Booth mentioning the file is not Booth finding a defect in it."""
    meta = {'assertion': 'file-locus', 'expect_discrepancy_implicating': 'a.py'}
    ok, why = loader.satisfied_by(meta, _verdict([
        {'id': 1, 'verdict': 'CONFIRMED', 'implicates': ['a.py']},
    ]))
    assert not ok
    assert 'a.py' in why


def test_file_locus_is_not_satisfied_by_a_discrepancy_elsewhere():
    meta = {'assertion': 'file-locus', 'expect_discrepancy_implicating': 'a.py'}
    ok, why = loader.satisfied_by(meta, _verdict([
        {'id': 1, 'verdict': 'DISCREPANCY', 'implicates': ['b.py']},
    ]))
    assert not ok
    assert 'b.py' in why


def test_no_locus_is_satisfied_only_when_the_pr_is_not_waved_through():
    meta = {'assertion': 'no-locus'}
    blocked, _ = loader.satisfied_by(meta, _verdict([], 'NEEDS HUMAN REVIEW'))
    waved, _ = loader.satisfied_by(meta, _verdict([], 'SAFE TO MERGE'))
    assert blocked and not waved


def test_a_missing_verdict_block_never_satisfies_anything():
    """Absence is not success -- the lesson from a skipped workflow
    reporting green."""
    for meta in ({'assertion': 'no-locus'},
                 {'assertion': 'file-locus', 'expect_discrepancy_implicating': 'a.py'}):
        ok, why = loader.satisfied_by(meta, None)
        assert not ok
        assert 'no booth-verdict block' in why


def test_generated_directories_are_not_read_as_fixture_content(tmp_path):
    """Regression guard for a failure that only appeared in the full suite.

    pytest collected head/test_guard.py as an ordinary test, which created a
    __pycache__ beside it; the tree walk then read a .pyc as UTF-8 and five
    fixture tests failed for a reason unrelated to anything they assert. In
    isolation nothing collected the file, so they passed -- the expensive kind
    of failure to chase. conftest.py now stops the collection; this stops the
    residue mattering if anything else creates it.
    """
    (tmp_path / '__pycache__').mkdir()
    (tmp_path / '__pycache__' / 'x.pyc').write_bytes(b'\x00\x01\x02\xfe\xff')
    (tmp_path / 'real.md').write_text('content', encoding='utf-8')

    tree = loader._tree(tmp_path)
    assert tree == {'real.md': 'content'}, (
        f"generated directories leaked into the fixture tree: {sorted(tree)}"
    )


def test_a_stray_binary_file_is_an_error_rather_than_a_silent_omission(tmp_path):
    """Dropping it quietly would hide a tool writing into a hand-written tree."""
    (tmp_path / 'rogue.bin').write_bytes(b'\x00\xfe\xff')
    with pytest.raises(loader.FixtureError, match="not UTF-8"):
        loader._tree(tmp_path)


def test_a_malformed_fixture_is_rejected_loudly(tmp_path):
    (tmp_path / 'fixture.json').write_text('{"id": "x"}', encoding='utf-8')
    with pytest.raises(loader.FixtureError, match="missing"):
        loader.load(tmp_path)


def test_an_id_that_does_not_match_its_directory_is_rejected(tmp_path):
    d = tmp_path / 'real-name'
    d.mkdir()
    (d / 'fixture.json').write_text(
        '{"id": "other-name", "why": "w", "provenance": "p", '
        '"assertion": "no-locus", "assertion_strength": "s"}',
        encoding='utf-8',
    )
    with pytest.raises(loader.FixtureError, match="must match the directory"):
        loader.load(d)
