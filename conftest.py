"""Build the dashboard once per test session.

`index.html` and `dist/` are build outputs and are no longer tracked (Stage 8c
phase 2). Before that change they were committed, so every checkout happened to
have them and the tests that read them happened to run.

That "happened to" is the whole problem this file exists to solve. Roughly a
dozen tests assert on the generated page, and **seven of them skip rather than
fail when it is absent**, with messages like "index.html has not been generated
in this checkout". Untracking the artifact without building it here would not
have turned the suite red -- it would have turned seven guards into green skips,
which is the failure mode this repository has been bitten by before and the
reason the phase-2 plan called this conftest load-bearing rather than
convenient.

So: build first, once, for the whole session. It costs ~0.2s. If the build
fails the session stops here, because every downstream assertion about the page
would otherwise be measuring a stale artifact or a missing one.

The skip-shaped hole is closed twice over. This fixture removes the condition,
and `tests/test_build_artifacts_exist.py` asserts the page was built -- so if
this file is deleted, renamed, or silently stops running, a test goes RED
instead of the suite going quietly greener.

**"Built", not "present", and the difference is the whole point.** The first
version of that guard only checked the files existed. Untracked files are not
cleaned up, so a stale `index.html` from an earlier run satisfied it: a
mutation that stopped this conftest building anything SURVIVED, on a working
tree where the artifact happened to be lying around. On a fresh CI checkout it
would have been caught -- which is the worst version of a guard, one that holds
everywhere except the machine the work is done on.

So the build records each artifact's modification time immediately BEFORE and
immediately AFTER running the generator, and the guard asserts the two differ.
That is an exact test of "this session rewrote this file", with no clock
comparison and no tolerance window to tune. An earlier attempt did use a
one-second window and it was not good enough: run pytest twice in quick
succession and a build that does nothing still looks fresh, which is exactly
how the mutation harness caught it.
"""
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent
GENERATOR = ROOT / 'src' / 'generate_dashboard.py'

#: Attribute the build stamps onto pytest's config object. The guard reads it
#: through the built-in `pytestconfig` fixture, so it needs no cooperation from
#: this file beyond the build actually having happened -- and, critically, it
#: does not request the build fixture itself. A guard that requested it would
#: trigger it, and could never notice it had stopped being autouse.
BUILD_STAMPS_ATTR = '_dashboard_build_stamps'

#: What the generator writes. Names only; resolved relative to ROOT.
ARTIFACTS = ('index.html', 'dist')


def written_at(path):
    """When this artifact was last written, or None if it is not there.

    A directory reports the newest file inside it rather than its own mtime:
    rewriting dist/picks_2026_week1.pdf under the same name does not touch the
    directory's timestamp. The directory is the artifact's name; the files
    inside it are the artifact.
    """
    if not path.exists():
        return None
    if path.is_dir():
        stamps = [p.stat().st_mtime for p in path.rglob('*') if p.is_file()]
        return max(stamps) if stamps else None
    return path.stat().st_mtime


def build_the_dashboard():
    """Run the real generator. Returns the CompletedProcess; raises nothing."""
    return subprocess.run(
        [sys.executable, str(GENERATOR)],
        cwd=str(ROOT), capture_output=True, text=True)


@pytest.fixture(scope='session', autouse=True)
def built_dashboard(pytestconfig):
    """Generate index.html and dist/ before any test reads them.

    autouse and session-scoped: no test has to remember to request it, which
    matters because the tests that need it are the ones that would silently
    skip if it were missing -- they would never be the ones to notice.
    """
    before = {name: written_at(ROOT / name) for name in ARTIFACTS}
    result = build_the_dashboard()
    if result.returncode != 0:
        raise pytest.UsageError(
            'src/generate_dashboard.py failed, so the tests that read the '
            'generated page would be measuring a stale or missing artifact.\n'
            f'exit {result.returncode}\n'
            f'stdout:\n{result.stdout[-2000:]}\n'
            f'stderr:\n{result.stderr[-2000:]}')
    after = {name: written_at(ROOT / name) for name in ARTIFACTS}
    setattr(pytestconfig, BUILD_STAMPS_ATTR, {'before': before, 'after': after})
    return ROOT / 'index.html'
