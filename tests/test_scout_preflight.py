"""
Guards the Scout pre-flight, including against the PR it was written for.

Every check in src/scout_preflight.py exists because Booth caught the failure
on a real PR in this repository. So the load-bearing test here is not a unit
test at all -- it is a replay: PR #21's original description, against PR #21's
actual commit range, must produce the same two findings Booth produced, at the
point before the PR would have opened.

That replay is what keeps the tool honest. Unit tests prove the regexes fire;
the replay proves the thing catches the failure it claims to catch.

run_test_suite() is monkeypatched everywhere except where it is the subject.
Letting it run for real would mean pytest invoking pytest on every test in this
file, which is slow, recursive and proves nothing extra.

Run with: pytest tests/test_scout_preflight.py -v
"""
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / 'src'))

import scout_preflight as pf

# PR #21's real range. base = the workflow-fix commit it branched from;
# head = its final commit, before the merge.
PR21_BASE = '1d13116'
PR21_HEAD = '63d6175'

# The description as it actually stood when Booth audited it: one of three
# features described, a stale count, screenshots asserted and none attached.
PR21_ORIGINAL_BODY = """## The claim this PR corrects

The design audit recorded the SOS column as "an em-dash for all 32 teams" and
queued it to be removed or populated. Both were wrong.

First draft placed the note below the table. Screenshots in both themes moved
it above the table.

## Test evidence

```
125 passed, 10 warnings in 26.95s
```
"""


def _commits_available():
    r = subprocess.run(['git', 'cat-file', '-e', PR21_HEAD], cwd=REPO_ROOT,
                       capture_output=True)
    return r.returncode == 0


needs_history = pytest.mark.skipif(
    not _commits_available(),
    reason="PR #21's commits are not in this clone (shallow checkout)")


# --------------------------------------------------------------------------
# The replay. This is the test that matters.
# --------------------------------------------------------------------------

@needs_history
def test_it_catches_pr21_exactly_as_booth_did():
    """PR #21's original body, against PR #21's real commits.

    Booth reported two things about that PR: the description covered one of
    three bundled features, and it asserted screenshots while attaching none.
    Both were found after the PR was public, at the cost of a full audit. This
    asserts the same two findings are reachable from the description alone,
    before it opens.
    """
    findings, commits = pf.preflight(PR21_ORIGINAL_BODY, base=PR21_BASE,
                                     skip_tests=True, head=PR21_HEAD)
    assert len(commits) == 3, (
        f"expected PR #21's three non-merge commits, got {len(commits)}")

    by_name = {f.check: f for f in findings}
    assert not by_name['scope disclosed'].ok, (
        "the scope check passed on a body describing one of three features -- "
        "this is the discrepancy Booth found")
    assert not by_name['visual evidence'].ok, (
        "the visual check passed on a body claiming screenshots and attaching "
        "none -- Booth marked that UNVERIFIABLE three times")

    detail = by_name['scope disclosed'].detail
    for sha, _ in commits:
        assert sha in detail, f"the report does not name the undisclosed commit {sha}"


@needs_history
def test_the_corrected_pr21_body_would_have_passed():
    """The other half: the fix has to actually clear the check, or the tool is
    just a permanent red light nobody can satisfy."""
    corrected = PR21_ORIGINAL_BODY + """
| Commit | Work |
|---|---|
| `9e4ec47` | SOS empty state |
| `791b6a6` | Net Rating scale |
| `63d6175` | Changelog |

![dark](https://github.com/user-attachments/assets/example.png)
"""
    findings, _ = pf.preflight(corrected, base=PR21_BASE, skip_tests=True,
                               head=PR21_HEAD)
    by_name = {f.check: f for f in findings}
    assert by_name['scope disclosed'].ok, by_name['scope disclosed'].detail
    assert by_name['visual evidence'].ok, by_name['visual evidence'].detail


# --------------------------------------------------------------------------
# Test-count claims
# --------------------------------------------------------------------------

def test_a_stale_test_count_fails(monkeypatch):
    monkeypatch.setattr(pf, 'run_test_suite', lambda: (174, None))
    f = pf.check_test_count("Test evidence: 125 passed, 10 warnings.", False)
    assert not f.ok
    assert '125' in f.detail and '174' in f.detail


def test_a_correct_test_count_passes(monkeypatch):
    monkeypatch.setattr(pf, 'run_test_suite', lambda: (174, None))
    assert pf.check_test_count("174 passed, 10 warnings in 27s", False).ok


def test_every_claimed_count_is_checked_not_just_the_first(monkeypatch):
    """A body can quote several figures -- PR #21's correction carried three in
    a table. Checking only the first would let a wrong one through."""
    monkeypatch.setattr(pf, 'run_test_suite', lambda: (174, None))
    f = pf.check_test_count("was 174 passed, earlier 130 passed", False)
    assert not f.ok, "a second, wrong count was not checked"
    assert '130' in f.detail


def test_a_body_with_no_count_is_not_a_failure(monkeypatch):
    monkeypatch.setattr(pf, 'run_test_suite', lambda: (174, None))
    assert pf.check_test_count("A documentation-only change.", False).ok


def test_an_unrunnable_suite_fails_rather_than_passing_quietly(monkeypatch):
    """If the count cannot be checked, the claim is unverified -- which is the
    thing this tool exists to stop, so it must not report PASS."""
    monkeypatch.setattr(pf, 'run_test_suite', lambda: (None, 'collection error'))
    f = pf.check_test_count("174 passed", False)
    assert not f.ok
    assert 'could not be run' in f.detail


# --------------------------------------------------------------------------
# Scope disclosure
# --------------------------------------------------------------------------

THREE = [('aaa1111', 'First feature'),
         ('bbb2222', 'Second feature'),
         ('ccc3333', 'Third feature')]


def test_a_multi_commit_pr_must_enumerate_its_commits():
    f = pf.check_scope_disclosed("Describes only the first thing.", THREE)
    assert not f.ok
    assert all(sha in f.detail for sha, _ in THREE)


def test_enumerating_every_commit_passes():
    body = "Contains `aaa1111`, `bbb2222` and `ccc3333`."
    assert pf.check_scope_disclosed(body, THREE).ok


def test_a_partial_enumeration_still_fails():
    """The realistic version of the failure: two of three listed, which looks
    thorough."""
    f = pf.check_scope_disclosed("Covers aaa1111 and bbb2222.", THREE)
    assert not f.ok
    assert 'ccc3333' in f.detail
    assert 'aaa1111' not in f.detail, "a disclosed commit was reported missing"


def test_a_single_commit_pr_is_exempt():
    """Its title already describes the whole change; demanding a SHA there is
    noise, and a check that fires on everything gets ignored."""
    assert pf.check_scope_disclosed("Anything at all.", THREE[:1]).ok
    assert pf.check_scope_disclosed("", []).ok


@needs_history
def test_merge_commits_are_not_counted_as_undisclosed_features():
    """PR #21 merged main in to pick up the workflow fix. Requiring a reviewer
    to be told about "Merge main" is noise, and noise is how a check gets
    ignored. Its real range has 4 commits; 3 are features."""
    all_commits = subprocess.run(
        ['git', 'log', '--format=%h', f'{PR21_BASE}..{PR21_HEAD}'],
        cwd=REPO_ROOT, capture_output=True, text=True).stdout.split()
    assert len(all_commits) == 4, f"expected 4 raw commits, got {len(all_commits)}"
    assert len(pf.branch_commits(PR21_BASE, PR21_HEAD)) == 3, (
        "the merge commit is being counted as a feature to disclose")


# --------------------------------------------------------------------------
# Visual claims
# --------------------------------------------------------------------------

@pytest.mark.parametrize('claim', [
    "Screenshots in both themes moved it above the table.",
    "Verified in both themes at 1440px.",
    "I rendered it and looked at the page.",
])
def test_a_visual_claim_without_an_attachment_fails(claim):
    f = pf.check_visual_claims_have_artifacts(
        claim, ui_files=['src/dashboard_template.html'])
    assert not f.ok, f"{claim!r} was not treated as a visual claim"


@pytest.mark.parametrize('attachment', [
    "![dark theme](https://example.com/a.png)",
    '<img src="https://example.com/a.png">',
    "https://github.com/user-attachments/assets/abc123",
])
def test_a_visual_claim_with_an_attachment_passes(attachment):
    body = "Verified in both themes at 1440px.\n\n" + attachment
    assert pf.check_visual_claims_have_artifacts(
        body, ui_files=['index.html']).ok


def test_a_non_ui_pr_is_not_asked_to_screenshot_anything():
    """The false positive this tool found in its own PR. A change touching
    only Python can still discuss visual verification -- this very file does.
    There is nothing to screenshot, so the check must not be unsatisfiable."""
    f = pf.check_visual_claims_have_artifacts(
        "Booth flagged the missing screenshots three times.", ui_files=[])
    assert f.ok, f.detail
    assert 'nothing to screenshot' in f.detail


def test_a_ui_pr_making_the_same_claim_still_fails():
    """The gate must not become a way out. Same wording, a diff that changes
    the page, and the check fires."""
    f = pf.check_visual_claims_have_artifacts(
        "Booth flagged the missing screenshots three times.",
        ui_files=['src/dashboard_template.html'])
    assert not f.ok


def test_touches_ui_sees_template_changes_and_ignores_python():
    """The gate is a fact about the diff, so it has to read the diff."""
    assert pf.touches_ui('HEAD') == [], "a no-op range reported UI changes"
    ui = pf.touches_ui(PR21_BASE, PR21_HEAD) if _commits_available() else ['x.html']
    assert any(f.endswith('.html') for f in ui), (
        "PR #21 changed the dashboard template; the UI gate did not see it")


def test_a_body_making_no_visual_claim_is_not_asked_for_images():
    assert pf.check_visual_claims_have_artifacts(
        "A pandas version experiment. No UI involved.").ok


def test_the_tool_exits_nonzero_when_a_check_fails(tmp_path):
    """It has to be usable as a gate. A tool that reports problems on stdout
    and exits 0 is a tool every script ignores."""
    body = tmp_path / 'body.md'
    # An undisclosed-scope failure rather than a visual one: this branch may
    # touch no UI, and the visual check is gated on the diff.
    body.write_text("Describes nothing in particular.", encoding='utf-8')
    # The base is computed, not hardcoded as HEAD~3. HEAD~3 spanned two
    # non-merge commits when this was written and one after the next merge
    # landed, at which point the scope check passed and this test failed --
    # on a branch where nothing about scout_preflight had changed. A test
    # that manufactures its failure out of the repository's own recent
    # history fails on the shape of history rather than on the behaviour it
    # is checking. Walking back three NON-MERGE commits guarantees at least
    # two of them sit between base and HEAD however the branch was merged.
    log = subprocess.run(['git', 'log', '--no-merges', '--format=%H', '-3'],
                         cwd=REPO_ROOT, capture_output=True, text=True)
    base = log.stdout.split()[-1]
    r = subprocess.run(
        [sys.executable, str(REPO_ROOT / 'src' / 'scout_preflight.py'),
         str(body), '--skip-tests', '--base', base],
        cwd=REPO_ROOT, capture_output=True, text=True)
    assert r.returncode != 0, (
        f"a failing check exited 0, so nothing can gate on it:\n{r.stdout}")


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))


# --------------------------------------------------------------------------
# Quotation vs assertion -- found by running the tool on its own PR
# --------------------------------------------------------------------------

def test_a_count_quoted_inside_a_code_block_is_not_a_claim(monkeypatch):
    """The false positive this tool found in its OWN description.

    That PR quoted PR #21's "125 passed" inside a fenced block to explain the
    failure being fixed, and got flagged for claiming it. Pasted output is
    evidence, not assertion.
    """
    monkeypatch.setattr(pf, 'run_test_suite', lambda: (194, None))
    body = "Head is 194 passed.\n\nPR #21 wrongly said:\n```\n125 passed\n```\n"
    findings, _ = pf.preflight(body, base='HEAD', skip_tests=False)
    tc = {f.check: f for f in findings}['test count']
    assert tc.ok, f"a quoted historical figure was treated as a claim: {tc.detail}"


def test_a_wrong_count_outside_a_code_block_still_fails(monkeypatch):
    """The stripping must not become a way to smuggle a claim past the check."""
    monkeypatch.setattr(pf, 'run_test_suite', lambda: (194, None))
    body = "This PR: 125 passed.\n\n```\nirrelevant\n```\n"
    findings, _ = pf.preflight(body, base='HEAD', skip_tests=False)
    assert not {f.check: f for f in findings}['test count'].ok


def test_a_blockquoted_claim_is_treated_as_quotation(monkeypatch):
    monkeypatch.setattr(pf, 'run_test_suite', lambda: (194, None))
    body = "Booth reported:\n\n> 125 passed, 10 warnings\n\nCurrent: 194 passed.\n"
    findings, _ = pf.preflight(body, base='HEAD', skip_tests=False)
    assert {f.check: f for f in findings}['test count'].ok


@needs_history
def test_an_attachment_inside_a_code_block_still_counts_as_evidence():
    """Stripping applies to CLAIMS, not to evidence. An image is an image
    wherever it appears, and hiding one behind stripping would turn a
    principled fix into a new false positive.

    Goes through preflight() rather than calling the check directly, because
    the thing being guarded is the WIRING -- which argument preflight hands to
    the attachment search. An earlier version of this test passed both
    arguments itself and therefore could not see that wiring change at all:
    mutating preflight to search the stripped text went uncaught. That is the
    guard-claims-more-than-its-code failure, found by mutation-testing this
    file's own guards.

    Uses PR #21's range because it touches the dashboard template, so the UI
    gate is open and the attachment path is actually reached.
    """
    body = ("Verified in both themes at 1440px.\n\n"
            "```\n![dark](https://github.com/user-attachments/assets/a.png)\n```\n")
    findings, _ = pf.preflight(body, base=PR21_BASE, skip_tests=True,
                               head=PR21_HEAD)
    visual = {f.check: f for f in findings}['visual evidence']
    assert visual.ok, (
        f"an attached image was not seen because it sat inside a code block: "
        f"{visual.detail}")


def test_strip_quotations_leaves_ordinary_prose_alone():
    body = "A normal sentence.\n\n```\nquoted\n```\n\n> quoted too\n\nAnother sentence."
    stripped = pf.strip_quotations(body)
    assert 'A normal sentence.' in stripped
    assert 'Another sentence.' in stripped
    assert 'quoted' not in stripped
