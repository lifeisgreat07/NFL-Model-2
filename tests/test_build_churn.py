"""
Tests for src/prune_build_churn.py.

The interesting ones run against this repository's own history. Seven commits
on main changed nothing but a build timestamp, and nineteen others were real
regenerations; a classifier for "is this commit worth making" should be
checked against those, not only against bytes invented for the test. If it
ever calls one of the real nineteen churn, the workflow would start silently
discarding genuine dashboard output -- which is a far worse failure than the
noisy commits it was written to prevent.

Run with: pytest tests/test_build_churn.py -v
"""
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / 'src'))

from prune_build_churn import is_churn_only, normalise  # noqa: E402


def git(*args):
    return subprocess.run(['git', *args], cwd=REPO_ROOT, capture_output=True)


def blob(sha, path):
    """File contents at a commit, or None if absent/unknown."""
    out = git('show', f'{sha}:{path}')
    return out.stdout if out.returncode == 0 else None


def commit_exists(sha):
    return git('cat-file', '-e', f'{sha}^{{commit}}').returncode == 0


# ============================================================
# The normaliser
# ============================================================
def test_freshness_stamp_is_blanked_but_the_markup_survives():
    """Only the text inside the span goes. If the surrounding markup were
    eaten too, a real change to that region would be normalised away with
    it."""
    a = b"<p>x</p><span class='foot-freshness'>Data as of 2026-09-04 16:52 UTC</span><p>y</p>"
    b = b"<p>x</p><span class='foot-freshness'>Data as of 2026-09-04 16:56 UTC</span><p>y</p>"
    assert normalise(a, 'index.html') == normalise(b, 'index.html')
    assert b"<span class='foot-freshness'></span>" in normalise(a, 'index.html')
    assert b"<p>x</p>" in normalise(a, 'index.html')


def test_pdf_dates_and_derived_id_are_blanked():
    a = (b"/CreationDate (D:20260904165205+00'00') /ModDate (D:20260904165205+00'00')"
         b"\ntrailer\n<<\n/ID \n[<bf86e6714d14c9ae8321fc8f0911e3c8><bf86e6714d14c9ae8321fc8f0911e3c8>]\n")
    b = (b"/CreationDate (D:20260904173032+00'00') /ModDate (D:20260904173032+00'00')"
         b"\ntrailer\n<<\n/ID \n[<0eb886108ae1b37b0608e79a13fb06d9><0eb886108ae1b37b0608e79a13fb06d9>]\n")
    assert normalise(a, 'picks.pdf') == normalise(b, 'picks.pdf')


def test_a_real_content_change_is_not_normalised_away():
    """The whole risk of this module: normalising too much would make the
    workflow throw away real dashboard output."""
    a = b"<span class='foot-freshness'>Data as of A</span><td>Model B 68.2%</td>"
    b = b"<span class='foot-freshness'>Data as of B</span><td>Model B 71.9%</td>"
    assert normalise(a, 'index.html') != normalise(b, 'index.html')


def test_visible_generated_date_inside_a_pdf_is_left_alone():
    """The picks sheet prints its own date on the page. That is content
    somebody reads off paper, so a rebuild on a different day is a real
    change and must still commit."""
    a = b"BT (14 games | model v2.4 | generated 2026-09-04) Tj ET"
    b = b"BT (14 games | model v2.4 | generated 2026-09-05) Tj ET"
    assert normalise(a, 'picks.pdf') != normalise(b, 'picks.pdf')


# ============================================================
# The predicate
# ============================================================
def test_an_unchanged_file_is_not_reported_as_churn():
    """There is nothing to restore, and calling it churn would make the
    script's own report wrong."""
    data = b"<span class='foot-freshness'>Data as of X</span>"
    assert is_churn_only(data, data, 'index.html') is False


def test_timestamp_only_difference_is_churn():
    a = b"<span class='foot-freshness'>Data as of 2026-09-04 16:52 UTC</span>"
    b = b"<span class='foot-freshness'>Data as of 2026-09-04 16:56 UTC</span>"
    assert is_churn_only(a, b, 'index.html') is True


def test_unknown_file_types_are_never_churn():
    """Anything the normaliser doesn't understand is treated as real. Failing
    safe here means a redundant commit; failing the other way means lost
    output."""
    assert is_churn_only(b'a', b'b', 'src/config.py') is False


# ============================================================
# Against this repository's real history
# ============================================================
# Commits whose entire diff was the build stamp. Each was verified by hand:
# zero non-freshness lines in index.html, and only date/ID bytes in the PDF.
KNOWN_CHURN = ['849ce5f', 'c944c03', 'a9518bc', 'cd7ba62', 'ff5cea7', '5bf703f', '9e77f51']

# Auto-regenerate commits that carried real dashboard changes, by their
# non-timestamp line counts at the time of writing: 155, 506, 128, 51, 21.
KNOWN_REAL = ['2e26bf5', 'bddba38', '6763302', 'cc6c611', '1b0aa0e']


@pytest.mark.parametrize('sha', KNOWN_CHURN)
def test_known_no_op_commits_are_classified_as_churn(sha):
    if not commit_exists(sha):
        pytest.skip(f"{sha} not in this checkout (shallow clone or rewritten history)")
    for path in ('index.html', 'dist/picks_2026_week1.pdf'):
        old, new = blob(f'{sha}~1', path), blob(sha, path)
        if old is None or new is None or old == new:
            continue
        assert is_churn_only(old, new, path), (
            f"{sha} changed {path} in a way this would commit, but the commit "
            f"was verified to be build-stamp only")


@pytest.mark.parametrize('sha', KNOWN_REAL)
def test_known_substantive_commits_are_never_discarded(sha):
    """The failure that would actually hurt: a real regeneration silently
    dropped because the normaliser is too aggressive."""
    if not commit_exists(sha):
        pytest.skip(f"{sha} not in this checkout")
    old, new = blob(f'{sha}~1', 'index.html'), blob(sha, 'index.html')
    if old is None or new is None:
        pytest.skip(f"{sha} has no index.html on both sides")
    assert not is_churn_only(old, new, 'index.html'), (
        f"{sha} carried real dashboard changes but would have been discarded")


# ============================================================
# The workflow actually runs it
# ============================================================
def test_workflow_prunes_before_it_commits():
    """A guard that outlives the reasoning: if the pruning step is removed or
    reordered after the commit step, it stops doing anything at all and the
    only symptom is the slow return of no-op commits."""
    wf = (REPO_ROOT / '.github' / 'workflows' / 'generate-dashboard.yml').read_text()
    assert 'prune_build_churn.py' in wf, "the workflow no longer prunes build churn"
    assert wf.index('prune_build_churn.py') < wf.index('git-auto-commit-action'), (
        "pruning must run before the auto-commit step, or it has no effect")


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))
