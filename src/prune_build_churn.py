"""
Drop regenerated files whose only difference is a build timestamp.

The problem this solves, with real numbers: of the 26 "Auto-regenerate
dashboard" commits on main as of 2026-09-04, seven changed nothing except
the moment the build ran. A representative one, c944c03:

    -  ...<span class='foot-freshness'>Data as of 2026-09-04 16:52 UTC</span>
    +  ...<span class='foot-freshness'>Data as of 2026-09-04 16:56 UTC</span>

plus 72 bytes of reportlab's /CreationDate, /ModDate and the /ID hash it
derives from them. Four minutes of wall clock, committed to main.

That is not merely untidy. index.html and dist/*.pdf are tracked generated
artifacts, so a no-op commit to them collides with any open branch that also
regenerated them -- which is exactly how PR #13 arrived with a merge conflict
whose entire content was two timestamps disagreeing. The cost is paid by
whoever has a branch open, every time.

The fix deliberately keeps the timestamp. "Data as of ..." is real
information for anyone reading the dashboard, and a build that genuinely
produces new numbers should say when. What is removed is the *commit* for a
build that produced nothing else: this script restores such files from HEAD
before the auto-commit step sees them, so the workflow simply finds nothing
to commit rather than manufacturing a commit against its own output.

Note what is NOT normalised: the "generated <date>" line printed inside the
picks PDF. That is visible content on a page someone prints, so a rebuild on
a different day is a real change and should commit.

Usage: python src/prune_build_churn.py [path ...]
Defaults to the artifacts the dashboard workflow writes. Prints what it
restored; exit code is 0 either way, since "nothing changed" is a normal
outcome, not a failure.
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

# Artifacts the generate-dashboard workflow rewrites on every run.
DEFAULT_PATHS = ['index.html', 'dist']

# The dashboard's freshness stamp. Matched on the class attribute rather than
# on a date shape, so a change to the date FORMAT doesn't silently stop this
# from matching and quietly reintroduce the churn.
FRESHNESS_RE = re.compile(rb"(<span class='foot-freshness'>)[^<]*(</span>)")

# reportlab stamps both dates and then derives /ID from them, so all three
# move together on every build even when the page content is byte-identical.
PDF_DATE_RE = re.compile(rb"/(?:CreationDate|ModDate)\s*\([^)]*\)")
PDF_ID_RE = re.compile(rb"/ID\s*\n?\s*\[(?:\s*<[0-9a-fA-F]*>)+\s*\]")


def normalise(data: bytes, name: str) -> bytes:
    """Blank out the parts of a generated file that change on every build."""
    if name.endswith('.html'):
        return FRESHNESS_RE.sub(rb'\1\2', data)
    if name.endswith('.pdf'):
        return PDF_ID_RE.sub(b'/ID[]', PDF_DATE_RE.sub(b'/Date()', data))
    return data


def is_churn_only(old: bytes, new: bytes, name: str) -> bool:
    """True when the file changed, but only in its build stamps.

    Both halves matter. An unchanged file is not churn -- there is nothing to
    restore and saying otherwise would make the caller's report wrong."""
    if old == new:
        return False
    return normalise(old, name) == normalise(new, name)


def _git(*args, **kw):
    return subprocess.run(['git', *args], cwd=ROOT, capture_output=True, **kw)


def changed_files(paths):
    out = _git('diff', '--name-only', 'HEAD', '--', *paths, text=True)
    return [line for line in out.stdout.splitlines() if line.strip()]


def head_bytes(path):
    """Contents of a path at HEAD, or None if it isn't tracked there yet."""
    out = _git('show', f'HEAD:{path}')
    return out.stdout if out.returncode == 0 else None


def main(argv):
    paths = argv[1:] or DEFAULT_PATHS
    restored, kept = [], []

    for path in changed_files(paths):
        old = head_bytes(path)
        if old is None:
            # Brand new file. Never churn -- there is no previous build to
            # compare it against, and dropping it would lose real output.
            kept.append(path)
            continue
        new = (ROOT / path).read_bytes()
        if is_churn_only(old, new, path):
            _git('checkout', 'HEAD', '--', path)
            restored.append(path)
        else:
            kept.append(path)

    for p in restored:
        print(f"  build-stamp only, restored from HEAD: {p}")
    for p in kept:
        print(f"  real change, keeping: {p}")
    if not restored and not kept:
        print("  no generated artifacts changed")
    elif not kept:
        print("Nothing but build stamps changed -- there is no commit to make.")
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
