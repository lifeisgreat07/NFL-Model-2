"""The Pages deploy workflow publishes a built page, and cannot publish a broken one.

This is the workflow that makes index.html removable. Until it exists and is
proven, index.html has to stay committed, and while it stays committed every
branch that touches the template conflicts with it the moment anything else
merges -- four rebase cycles on PR #52 in a single afternoon.

So the risk this file guards is not "the workflow is missing." It is that the
workflow quietly stops being a *build* and becomes a publish of whatever
happens to be in the checkout -- which would look green forever while serving a
stale page, and would do it silently, because nobody reads a passing deploy.

Parsed by line position rather than PyYAML, matching test_workflow_churn_guard.py:
yaml is not installed on the machine this suite runs on, and the assertions here
are about which steps are PRESENT and in what ORDER, which line numbers capture
exactly.
"""
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
WORKFLOW = REPO_ROOT / '.github' / 'workflows' / 'deploy-pages.yml'


@pytest.fixture(scope='module')
def lines():
    if not WORKFLOW.exists():
        pytest.fail(f"{WORKFLOW.name} is missing -- the site has no builder")
    return WORKFLOW.read_text(encoding='utf-8').splitlines()


def line_of(lines, needle):
    for i, line in enumerate(lines):
        if needle in line:
            return i
    return None


def test_the_page_is_built_before_it_is_uploaded(lines):
    """The whole point. Upload without a build publishes the checked-out file,
    which is exactly the committed artifact this change exists to delete."""
    build = line_of(lines, 'run: python -m src.site.build')
    upload = line_of(lines, 'upload-pages-artifact')
    assert build is not None, (
        "the deploy workflow never runs src.site.build, so it publishes "
        "whatever is in the checkout rather than building the site")
    assert upload is not None, "the deploy workflow never uploads a Pages artifact"
    assert build < upload, (
        f"the site build runs at line {build + 1} but the upload is at "
        f"line {upload + 1} -- building after the upload publishes the old site")


def test_a_page_that_did_not_build_is_refused(lines):
    """A page with unfilled __PLACEHOLDER__ tokens renders as literal
    underscores in the browser. It has shipped before; it must not ship
    silently."""
    check = line_of(lines, '__[A-Z0-9_]+__')
    upload = line_of(lines, 'upload-pages-artifact')
    assert check is not None, (
        "nothing checks the built page for unfilled template placeholders")
    assert check < upload, (
        "the placeholder check runs after the upload, so a broken page is "
        "published and then complained about")
    assert line_of(lines, 'test -s _site/index.html') is not None, (
        "nothing checks that the built index.html is non-empty")
    assert line_of(lines, 'test -s _site/nfl/index.html') is not None, (
        "nothing checks that the NFL's board is non-empty")
    assert line_of(lines, "find _site -name index.html") is not None, (
        "the placeholder check reads one page, not every page the site publishes")


@pytest.mark.parametrize('published, source', [('.nojekyll', '.nojekyll'),
                                                ('og-card.png', 'assets/og/og-card.png')])
def test_the_artifact_contains_what_the_site_needs(published, source):
    """Since Stage 53 src/site/build.py assembles the site: every sport's
    page, the NFL's printable picks under nfl/dist/, and the shared files.
    .nojekyll is the one people forget: without it Pages runs the output
    through Jekyll, which drops files and directories whose names begin with
    an underscore."""
    from src.site import build as site
    assert site.SHARED_FILES.get(published) == source, (
        f"{published} is never copied into the site, so the published site will not have it")


def test_the_nfl_board_and_its_printable_picks_are_collected():
    from src.site import build as site
    source = Path(site.__file__).read_text(encoding='utf-8')
    assert "shutil.copyfile(ROOT / 'index.html', dest / 'index.html')" in source
    assert "shutil.copytree(ROOT / 'dist', dest / 'dist', dirs_exist_ok=True)" in source


def test_the_deploy_cannot_write_to_the_repository(lines):
    """`contents: read` is what makes this structurally incapable of the thing
    the workflow it replaces does: committing a generated file back to main.
    A deploy that can push is a deploy that can start the conflict cycle again."""
    perms = re.search(r'^permissions:\n((?:\s+\w[\w-]*:.*\n)+)', '\n'.join(lines) + '\n', re.M)
    assert perms, "the workflow declares no permissions block"
    block = perms.group(1)
    assert re.search(r'contents:\s*read', block), (
        f"contents is not read-only in the permissions block:\n{block}"
        "A Pages deploy never needs to write to the repo.")
    for needed in ('pages: write', 'id-token: write'):
        assert needed in block, f"missing `{needed}`, which actions/deploy-pages requires"


def test_deploys_queue_rather_than_cancel(lines):
    """A cancelled deploy can leave the site on a half-published artifact.
    cancel-in-progress defaults to false, so this asserts it is stated -- the
    point is that the next person to copy this file sees the decision."""
    group = line_of(lines, 'group: pages')
    assert group is not None, (
        "no concurrency group, so two pushes can deploy over each other")
    assert line_of(lines, 'cancel-in-progress: false') is not None, (
        "cancel-in-progress is not explicitly false; a cancelled Pages deploy "
        "can leave the site serving a partially published artifact")


def test_it_does_not_commit_anything(lines):
    """The failure mode this whole change exists to remove."""
    body = '\n'.join(lines)
    for banned in ('git-auto-commit-action', 'file_pattern'):
        assert banned not in body, (
            f"the deploy workflow uses {banned} -- it is meant to publish a "
            f"built page, never to commit one back to the repository")


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))
