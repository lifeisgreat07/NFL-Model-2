"""
Check a PR description against reality BEFORE the PR is opened.

VERIFICATION.md says the rule should be "enforced mechanically rather than
relying on an agent remembering to follow it", and then names two mechanisms:
CI, and Booth. Both run AFTER a PR exists. Nothing checks what Scout writes
into the description at the moment it is written -- so the first reader of an
unverified claim is Booth, which is an LLM, costs a real audit, and only
reports after the PR is already public.

This closes that gap. Every check here exists because Booth caught the failure
on a real PR in this repository, and every one of those failures was
deterministically checkable in advance:

  1. STALE TEST COUNT. PR #21 claimed "125 passed" while its head had 130, then
     144. Booth caught it twice, checking out the earlier commit both times to
     prove the figure had been true once. Running pytest and comparing is a
     two-second check.

  2. UNDISCLOSED SCOPE. PR #21 bundled three separate features while its title
     and body described one. Booth's words: "anyone approving based on the
     description alone is approving more than they think they're approving."
     No test could catch that; counting commits can.

  3. VISUAL CLAIMS WITH NO ARTIFACT. The same PR asserted screenshots had
     driven a design decision and attached none. Booth marked it UNVERIFIABLE
     three separate times, correctly: an unattached screenshot is not evidence.

What this is NOT: a replacement for Booth. It is deterministic, cheap and
narrow -- it checks the claims whose truth is mechanically decidable. Booth
re-executes, reasons and finds things no regex can. Running this first means
Booth spends its audit on substance rather than on arithmetic Scout could have
done itself.

Usage:
    python src/scout_preflight.py <pr_body_file> [--base origin/main] [--skip-tests]

Exit code 0 if every check passes, 1 otherwise, so it can gate a workflow.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

# "144 passed", "144 passed, 10 warnings" -- the shape pytest -q prints and the
# shape these PR bodies quote it in.
TEST_COUNT_RE = re.compile(r'\b(\d+)\s+passed\b')

# Phrases that assert somebody looked at rendered output. Deliberately narrow:
# the point is to catch a claim of visual verification, not any mention of a
# picture.
VISUAL_CLAIM_RE = re.compile(
    r'\b(screenshots?|rendered it|verified in both themes|'
    r'verified visually|looked at the page|both themes at \d+px)\b',
    re.IGNORECASE)

# Markdown image, an HTML img tag, or a GitHub user-attachment URL.
ATTACHMENT_RE = re.compile(
    r'!\[[^\]]*\]\([^)]+\)|<img\s|github\.com/user-attachments/',
    re.IGNORECASE)


# Fenced code blocks and blockquotes are QUOTATION, not assertion. A PR that
# pastes real pytest output, or quotes an earlier report to explain what went
# wrong, is not claiming those numbers as its own.
#
# Found by running this tool against its own PR description, which quoted
# PR #21's "125 passed" inside a fenced block to explain the failure being
# fixed -- and got flagged for it. Stripping quotation is the principled fix.
FENCED_RE = re.compile(r'^```.*?^```', re.MULTILINE | re.DOTALL)
BLOCKQUOTE_RE = re.compile(r'^\s*>.*$', re.MULTILINE)

# A span inside quotation marks is quotation too, and it is the form a PR uses
# when it explains a past mistake mid-sentence or in a table cell -- neither of
# which can be a fenced block.
#
# Added after Booth ran the tool this file ships against the very PR that
# shipped it (#55) and it failed: that body's history table carried the row
#     | #54 claim 4 | "`test_workflow_churn_guard.py` ... its 31 tests still
#       pass" | 3 -- the 31 was a three-file run |
# A markdown table row is neither fenced nor a blockquote, so the module name
# and the wrong number landed in one unstripped sentence and the guard fired on
# the correction rather than on the error. A check against misquoted numbers
# that forbids quoting a misquoted number is not usable.
#
# Stripping the QUOTE rather than the table row is the narrow fix: a table cell
# is frequently a real assertion (this repo's PR bodies put verification tables
# in them), so exempting rows would blind the check where it is most needed.
# Bounded and newline-free so an unpaired quote cannot swallow the document.
QUOTED_SPAN_RE = re.compile(r'"[^"\n]{0,400}"|“[^”\n]{0,400}”')


def strip_quotations(body):
    """Remove quoted regions so only the body's own assertions are checked."""
    return QUOTED_SPAN_RE.sub('', BLOCKQUOTE_RE.sub('', FENCED_RE.sub('', body)))


class Finding:
    def __init__(self, check, ok, detail):
        self.check = check
        self.ok = ok
        self.detail = detail


def _git(*args):
    out = subprocess.run(['git'] + list(args), cwd=REPO_ROOT,
                         capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {out.stderr.strip()}")
    return out.stdout.strip()


def branch_commits(base, head='HEAD'):
    """Non-merge commits on this branch that are not on base.

    Merges are excluded deliberately: "Merge main" is not a feature a reviewer
    needs the description to disclose, and requiring its SHA would be noise
    that trains people to ignore this check.

    `head` is settable so a PR that already exists can be audited after the
    fact without checking anything out. Reconstructing the failure this tool
    was written for meant reading a merged branch, and doing that by moving
    HEAD around a dirty working tree is how this repo has lost edits before.
    """
    raw = _git('log', '--no-merges', '--format=%h%x1f%s', f'{base}..{head}')
    if not raw:
        return []
    return [tuple(line.split('\x1f', 1)) for line in raw.splitlines()]


def run_test_suite():
    """Returns the real passing count, or None if pytest could not be run."""
    out = subprocess.run([sys.executable, '-m', 'pytest', '-q', '--no-header'],
                         cwd=REPO_ROOT, capture_output=True, text=True)
    m = TEST_COUNT_RE.search(out.stdout)
    if not m:
        return None, out.stdout[-500:]
    return int(m.group(1)), None


def check_test_count(body, skip_tests):
    """The PR #21 failure: a figure that was true at some earlier commit."""
    claims = {int(m) for m in TEST_COUNT_RE.findall(body)}
    if not claims:
        return Finding('test count', True,
                       "no test-count claim in the body (nothing to verify)")
    if skip_tests:
        return Finding('test count', True,
                       f"claims {sorted(claims)} NOT verified (--skip-tests)")

    actual, err = run_test_suite()
    if actual is None:
        return Finding('test count', False,
                       f"the body claims {sorted(claims)} but the suite could "
                       f"not be run to check it:\n{err}")
    wrong = sorted(c for c in claims if c != actual)
    if wrong:
        return Finding('test count', False,
                       f"the body claims {wrong} passing but a real run at "
                       f"HEAD gives {actual}. This is the PR #21 failure: a "
                       f"figure that was true at an earlier commit.")
    return Finding('test count', True, f"claimed and actual both {actual}")


def check_scope_disclosed(body, commits):
    """Booth's scope discrepancy: a description covering part of the branch.

    The rule is deliberately mechanical rather than a fuzzy match on commit
    subjects: a multi-commit PR must enumerate its commits by short SHA. A
    single-commit branch is exempt, because its title already describes the
    whole change and demanding a SHA there is noise.
    """
    if len(commits) <= 1:
        return Finding('scope disclosed', True,
                       f"{len(commits)} non-merge commit(s) -- title covers it")
    missing = [(sha, subj) for sha, subj in commits if sha not in body]
    if missing:
        lines = '\n'.join(f"      {sha}  {subj}" for sha, subj in missing)
        return Finding('scope disclosed', False,
                       f"{len(commits)} commits on this branch, but the body "
                       f"never mentions {len(missing)} of them:\n{lines}\n"
                       f"      A reviewer approving on the description alone "
                       f"would be approving more than they think.")
    return Finding('scope disclosed', True,
                   f"all {len(commits)} commits enumerated in the body")


def touches_ui(base, head='HEAD'):
    """Does this branch change anything a screenshot could show?"""
    changed = _git('diff', '--name-only', f'{base}...{head}').splitlines()
    return [f for f in changed if f.endswith(('.html', '.css', '.svg'))]


def check_visual_claims_have_artifacts(claims, full_body=None, ui_files=None):
    """Booth marked the same claim UNVERIFIABLE three times in one PR.

    Scoped to PRs that actually change the page. Without that gate the check
    is unsatisfiable for a PR that merely DISCUSSES visual verification -- and
    this tool's own PR is exactly that, so on its first run it flagged the
    paragraph explaining the flag. Keyword-matching cannot tell a claim about
    this PR from prose about the subject; "does the diff contain anything a
    screenshot could show" can, mechanically.

    Consequence worth knowing: a PR that changes only Python cannot fail this
    check. That is correct -- there is nothing to screenshot -- and it is why
    the gate is the diff rather than a phrase whitelist, which would have been
    a guess about wording rather than a fact about the change.
    """
    full_body = full_body if full_body is not None else claims
    claim = VISUAL_CLAIM_RE.search(claims)
    if not claim:
        return Finding('visual evidence', True, "no visual claim made")
    if not ui_files:
        return Finding('visual evidence', True,
                       f"visual wording present ({claim.group(0)!r}) but the "
                       f"diff changes no .html/.css/.svg, so there is nothing "
                       f"to screenshot -- read as discussion, not a claim")
    if ATTACHMENT_RE.search(full_body):
        return Finding('visual evidence', True,
                       f"visual claim ({claim.group(0)!r}) has an attachment")
    return Finding('visual evidence', False,
                   f"the body claims visual verification ({claim.group(0)!r}) "
                   f"but attaches no image. An unattached screenshot is not "
                   f"evidence -- attach it, or state it as a process note "
                   f"rather than proof.")


# A count of tests attributed to a NAMED test module: "`tests/test_x.py` -- 8
# tests", "its 31 tests still pass". Both orders occur, so the pairing below
# scans for modules and counts separately and matches them within a sentence.
TEST_MODULE_RE = re.compile(r'(?:tests/)?(test_\w+)(?:\.py)?\b')
# "8 tests", "its 31 tests", "11 collected", "9 passed".
#
# `collected` and `passed` were added after this check MISSED the defect it was
# written for. PR #56's body carried
#     | `pytest tests/test_motion_system.py -q --collect-only` | 12 collected |
# and the guard stayed green because it only matched the word "tests". The
# actual figure was 11. The phrasing it could not see is the one pytest itself
# prints -- so the check matched the wording a person might invent and missed
# the wording the tool emits, which is the wording that will always be there.
SCOPED_COUNT_RE = re.compile(
    r'\b(\d+)\s+(?:of\s+(?:its|them|these)\s+)?(?:tests?|collected|passed|passing)\b')
# Sentence-ish. A count and a module in the same sentence are being associated
# by the reader whether or not the writer meant to.
SENTENCE_SPLIT_RE = re.compile(r'(?<=[.!?])\s+|\n{2,}|\n\|')


def collected_count(module):
    """How many cases pytest actually collects from tests/<module>.py."""
    path = REPO_ROOT / 'tests' / f'{module}.py'
    if not path.exists():
        return None
    out = subprocess.run(
        [sys.executable, '-m', 'pytest', str(path), '-q', '--collect-only'],
        cwd=REPO_ROOT, capture_output=True, text=True)
    m = re.search(r'\b(\d+)\s+tests?\s+collected\b', out.stdout)
    return int(m.group(1)) if m else None


def check_scoped_test_counts(body, skip_tests):
    """A count that is real output from a command with a DIFFERENT scope.

    The failure this exists for, stated exactly: on PR #54 the body said
    `test_workflow_churn_guard.py` -- "its 31 tests still pass". That file has
    3. The 31 was not invented; it was the true total of a three-file pytest
    run (3 + 20 + 8) quoted against a sentence about one of them.

    That is the same shape as two earlier Booth findings. PR #51 claim 17 said
    `--shadow-sm/md/lg` was "still used in ten places" -- 9 token references,
    10 box-shadow declarations, a number counted on one thing attached to a
    sentence naming another. PR #52 claim 5 said "seven pairs sit between 14.9
    and 15.25" when the script printed nine, read by eye off a wider band.

    None of the three was a fabrication, which is precisely why self-review
    misses them: the author remembers running a real command and getting a real
    number, so the figure feels earned. What went unchecked was the
    ATTRIBUTION -- whether the command's scope is the sentence's scope.

    So this check does the one thing that closes it mechanically: when the body
    names a test module and a count in the same sentence, collect that module
    and compare. `--skip-tests` does not disable it; collection is a parse, not
    a run, and takes milliseconds.
    """
    findings = []
    for sentence in SENTENCE_SPLIT_RE.split(strip_quotations(body)):
        counts = SCOPED_COUNT_RE.findall(sentence)
        modules = set(TEST_MODULE_RE.findall(sentence))
        if not counts or not modules:
            continue
        for module in sorted(modules):
            actual = collected_count(module)
            if actual is None:
                continue
            for claimed in {int(c) for c in counts}:
                if claimed != actual:
                    findings.append(
                        f"{module}.py: the body says {claimed} where pytest "
                        f"collects {actual}\n"
                        f"      in: \"{' '.join(sentence.split())[:160]}\"")
    if findings:
        return Finding('scoped test counts', False,
                       "a count attributed to a named test module does not "
                       "match that module:\n      " +
                       "\n      ".join(findings) +
                       "\n      Usually the number is real but came from a "
                       "wider command -- a multi-file pytest run quoted "
                       "against one file. Collect the file on its own.")
    return Finding('scoped test counts', True,
                   "no test-module count in the body disagrees with collection")


def preflight(body, base='origin/main', skip_tests=False, head='HEAD'):
    commits = branch_commits(base, head)
    # Assertions are checked against quotation-stripped text; the attachment
    # search runs on the FULL body, because an image is evidence wherever it
    # appears and stripping could hide one.
    claims = strip_quotations(body)
    ui_files = touches_ui(base, head)
    return [
        check_test_count(claims, skip_tests),
        check_scoped_test_counts(claims, skip_tests),
        check_scope_disclosed(claims, commits),
        check_visual_claims_have_artifacts(claims, body, ui_files),
    ], commits


def main():
    ap = argparse.ArgumentParser(
        description="Check a PR description against reality before opening it.")
    ap.add_argument('body_file', help="file containing the PR description")
    ap.add_argument('--base', default='origin/main',
                    help="branch this PR targets (default: origin/main)")
    ap.add_argument('--skip-tests', action='store_true',
                    help="do not run the suite; test-count claims go unchecked")
    ap.add_argument('--head', default='HEAD',
                    help="tip of the branch under review (default: HEAD). Set "
                         "it to audit an existing PR without checking it out.")
    args = ap.parse_args()

    body = Path(args.body_file).read_text(encoding='utf-8')
    findings, commits = preflight(body, args.base, args.skip_tests, args.head)

    print(f"Scout pre-flight -- {len(commits)} non-merge commit(s) "
          f"vs {args.base}\n")
    for f in findings:
        print(f"  [{'PASS' if f.ok else 'FAIL'}] {f.check}")
        for line in f.detail.splitlines():
            print(f"      {line}" if not line.startswith('      ') else line)
        print()

    failed = [f for f in findings if not f.ok]
    if failed:
        print(f"{len(failed)} check(s) failed. Fix the description before "
              f"opening the PR -- every one of these was caught by Booth on a "
              f"real PR, after the fact, at the cost of an audit.")
        return 1
    print("All checks passed. Booth's audit can go on substance.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
