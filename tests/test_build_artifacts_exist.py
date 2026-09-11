"""The guard on the guard.

The root `conftest.py` builds `index.html` and `dist/` before the session runs,
because those files stopped being tracked in Stage 8c phase 2 and roughly a
dozen tests read them.

Seven of those tests SKIP when the page is absent rather than fail. That is the
hazard: delete the conftest, rename it, break its import, or move the generator,
and the suite does not go red -- it goes *greener*, because seven guards quietly
stop asserting anything. A suite that reports more passes after a mistake is
worse than one that reports fewer.

These tests fail loudly in that case. They are deliberately not skippable and
deliberately do not build anything themselves; their whole job is to notice
that something else did.
"""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# Every artifact the built site is assembled from. .nojekyll is committed and
# is not a build output, so it is not listed here -- see .github/workflows/
# deploy-pages.yml, which asserts all three reach the uploaded artifact.
ARTIFACTS = [
    'index.html',
    'dist',
]


@pytest.mark.parametrize('relative', ARTIFACTS)
def test_the_session_built_this_artifact(relative, pytestconfig):
    """If this fails, the root conftest did not build. Nothing else is wrong.

    Note what is NOT asserted: that the file exists. Existence was the first
    version of this check and it was too weak to catch anything locally --
    these files are untracked, nothing deletes them between runs, and a stale
    copy from an earlier session passes an existence check happily. A mutation
    that stopped the conftest building anything SURVIVED against it.

    The second version compared the file's mtime against the build's start
    time, within a second. That was better and still not enough: two pytest
    runs back to back leave the artifact under a second old either way, so the
    same mutation survived again. The harness that found it is the mutation
    corpus running its cases in sequence, each one a pytest invocation -- an
    accidental but exact reproduction of the case the window cannot see.

    What is asserted is exact: the conftest records each artifact's mtime
    before and after running the generator, and a real build changes it. No
    clock, no tolerance.

    This test also deliberately does not request the `built_dashboard` fixture.
    Requesting it would trigger the build, so the test could never notice that
    the fixture had stopped being autouse -- it would be creating the condition
    it is meant to be checking.
    """
    stamps = getattr(pytestconfig, '_dashboard_build_stamps', None)
    assert stamps is not None, (
        'the root conftest.py never recorded a build, so it did not run or is '
        'no longer autouse. Roughly a dozen tests read the generated page and '
        'seven of them SKIP when it is absent, so the rest of this run is not '
        'measuring what it appears to measure.')

    assert (ROOT / relative).exists(), (
        f'{relative} is missing even though the build reported success -- '
        'src/generate_dashboard.py is no longer writing it where the tests '
        'look.')

    before, after = stamps['before'][relative], stamps['after'][relative]
    assert after is not None, (
        f'{relative} did not exist after the build step ran')
    assert after != before, (
        f'{relative} was not rewritten by this session\'s build -- its '
        'timestamp is identical before and after. The conftest ran and the '
        'generator did not actually produce anything, so every test reading '
        'the page is reading a leftover from an earlier run.')


def test_the_generated_page_is_not_empty():
    """A zero-byte index.html would satisfy every existence check above."""
    page = ROOT / 'index.html'
    size = page.stat().st_size
    assert size > 100_000, (
        f'index.html is {size} bytes, which is far too small to be the real '
        'dashboard. The generator exited 0 but produced something wrong.')


def test_the_root_conftest_is_where_the_tests_expect_it():
    """Names the file, so moving it fails here rather than in seven skips."""
    conftest = ROOT / 'conftest.py'
    assert conftest.exists(), (
        'conftest.py must sit in the repository root, not in tests/. pytest '
        'only applies a conftest to its own directory and below, and the '
        'build has to happen before ANY test collects.')
    text = conftest.read_text(encoding='utf-8')
    assert 'generate_dashboard.py' in text, (
        'the root conftest no longer names src/generate_dashboard.py, so it '
        'is probably no longer building the page')
    assert 'autouse=True' in text, (
        'the build fixture must be autouse -- the tests that need it are the '
        'ones that would silently skip without it, so they will never be the '
        'ones to request it')
    assert 'result.returncode != 0' in text and 'raise pytest.UsageError(' in text, (
        'the root conftest no longer raises when the generator exits non-zero. '
        'It must stop the session rather than continue against whatever is on '
        'disk -- otherwise a failed build leaves every test that reads the '
        'page measuring a leftover artifact.\n'
        'This is asserted on the source rather than by running it, and that '
        'is deliberate: the abort happens during fixture setup, so pytest '
        'reports a session error rather than a test failure, and no test can '
        'own it. A mutation removing the raise would otherwise be recorded as '
        'WRONG-GUARD -- red suite, nothing accountable.')
