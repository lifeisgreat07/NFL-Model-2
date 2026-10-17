"""Spotter's render job, held without a browser (Stage 43 item 2).

The pictures themselves are taken in CI (tests/browser/spotter_render.py
needs Playwright, which only the browser workflows install), so this file
reads the renderer and the workflow as text and holds what a render depends
on: the two viewports and both themes, one name for each picture, the clock
fixed, the workflow built to decision record 0007, and every file a rule
names able to start it.

Run with: pytest tests/test_spotter_render.py -v
"""
import ast
import re
from fnmatch import fnmatch
from pathlib import Path

import pytest

from src.agents import spotter_pages as sp

ROOT = Path(__file__).resolve().parents[1]
RENDERER = ROOT / 'tests' / 'browser' / 'spotter_render.py'
WORKFLOW = ROOT / '.github' / 'workflows' / 'spotter.yml'
BROWSER_CHECKS = ROOT / '.github' / 'workflows' / 'browser-checks.yml'


def text(path):
    return path.read_text(encoding='utf-8').replace('\r\n', '\n')


def constants():
    """The renderer's module-level constants, read without importing it
    (importing it needs Playwright)."""
    out = {}
    for node in ast.parse(text(RENDERER)).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try:
                out[node.targets[0].id] = ast.literal_eval(node.value)
            except ValueError:
                pass
    return out


def picture_name(page, width, height, scheme, label):
    """The renderer's name for a picture, read from its source so the two cannot drift."""
    assert "f'{page}-{width}x{height}-{scheme}-{label}.png'" in text(RENDERER), 'the picture name format changed'
    return f'{page}-{width}x{height}-{scheme}-{label}.png'


# --- the renderer -------------------------------------------------------------------------

def test_the_two_viewports_are_a_phone_and_a_desktop_in_both_themes():
    c = constants()
    assert c['VIEWPORTS'] == ((390, 844), (1440, 900))
    assert c['SCHEMES'] == ('light', 'dark')


def test_the_renderer_serves_the_pages_where_the_site_builds_them():
    assert constants()['SITE_PATH'] == sp.SITE_PATH


def test_a_picture_is_named_for_everything_a_reader_cites():
    assert picture_name('nfl', 390, 844, 'dark', 'head') == 'nfl-390x844-dark-head.png'
    assert picture_name('home', 1440, 900, 'light', 'base') == 'home-1440x900-light-base.png'


def test_every_picture_of_a_run_has_its_own_name():
    c = constants()
    names = {picture_name(p, w, h, s, label) for p in sp.PAGES for w, h in c['VIEWPORTS'] for s in c['SCHEMES']
             for label in ('head', 'base')}
    assert len(names) == len(sp.PAGES) * 2 * 2 * 2


@pytest.mark.parametrize('needle', [
    "timezone_id='UTC'", "locale='en-US'", "reduced_motion='reduce'", 'set_fixed_time(clock)',
    "lambda r: r.abort()", 'full_page=True', 'MIN_BYTES', "'pageerror'", 'PARK_JS',
], ids=['utc', 'locale', 'reduced-motion', 'fixed-clock', 'network-blocked', 'full-page', 'blank-guard', 'page-errors',
        'parked-panels'])
def test_what_makes_two_renders_of_a_page_the_same_picture_is_in_the_renderer(needle):
    assert needle in text(RENDERER), needle


def test_the_renderer_compares_no_pixels():
    src = text(RENDERER)
    assert not re.search(r'pixelmatch|to_have_screenshot|expect\(.*screenshot|ImageChops|\bdiff\b', src.split('"""', 2)[2])


# --- the workflow -----------------------------------------------------------------------------

def job(name):
    body = text(WORKFLOW).split('\njobs:\n', 1)[1]
    parts = re.split(r'\n(?=  [A-Za-z][\w-]*:[ ]*\n)', '\n' + body)
    found = {re.match(r'\n?  ([\w-]+):', p).group(1): p for p in parts if re.match(r'\n?  ([\w-]+):', p)}
    return found[name]


def test_the_render_job_holds_no_model_and_reads_only():
    # The workflow's other jobs (item 3) publish and read; this job runs the pull request's code.
    t = job('render')
    assert 'anthropics/claude-code-action' not in t
    assert 'permissions:' not in t, 'the render job takes the workflow\'s read-only grant and nothing more'
    assert not re.search(r':\s*write\b', t.replace('# ', '#'))
    assert re.search(r'^permissions:\n  contents: read\n', text(WORKFLOW), re.M)


@pytest.mark.parametrize('name', ['render', 'publish', 'read'])
def test_every_job_is_bounded_and_on_the_pinned_runner(name):
    t = job(name)
    assert '    runs-on: ubuntu-24.04\n' in t and re.search(r'    timeout-minutes: \d+\n', t)


def test_the_workflow_does_not_run_for_a_fork():
    # The render job is the only one that starts: the others need it, and it publishes nothing for a fork.
    assert 'if: github.event.pull_request.head.repo.full_name == github.repository' in job('render')
    assert "needs: [render" in job('publish') and "needs.render.outputs.pictures == 'true'" in job('publish')


def test_the_head_and_the_base_are_checked_out_by_sha_into_their_own_folders():
    t = text(WORKFLOW)
    assert 'ref: ${{ github.event.pull_request.head.sha }}' in t and '          path: head\n' in t
    assert 'ref: ${{ github.event.pull_request.base.sha }}' in t and '          path: base\n' in t
    assert 'refs/pull' not in t, 'the merge ref is neither of the two pages being compared'
    # The NFL page reads the git log, so a shallow base shows lines the head does not.
    assert t.count('          fetch-depth: 0\n') == 2, 'both checkouts need the same full history'


def test_both_sites_are_built_and_both_are_photographed_with_one_clock():
    t = text(WORKFLOW)
    assert 'python -m src.site.build --out "$RUNNER_TEMP/site-head"' in t
    assert 'python -m src.site.build --out "$RUNNER_TEMP/site-base"' in t
    assert 'for label in head base; do' in t
    assert t.count('--clock "$clock"') == 1 and 'clock=$(date -u -d' in t


def test_playwright_is_pinned_to_the_version_the_browser_checks_use():
    mine = re.search(r'pip install playwright==(\S+)', text(WORKFLOW))
    theirs = re.search(r'pip install playwright==(\S+)', text(BROWSER_CHECKS))
    assert mine and theirs and mine.group(1) == theirs.group(1)


def test_the_pictures_are_uploaded_as_one_named_artifact_that_must_exist():
    t = text(WORKFLOW)
    assert 'name: spotter-renders-pr${{ github.event.pull_request.number }}' in t
    assert 'if-no-files-found: error' in t


def test_the_pages_are_picked_by_the_map_from_the_two_commits():
    t = text(WORKFLOW)
    assert 'python -m src.agents.spotter_pages --base "$BASE_SHA" --head "$HEAD_SHA"' in t
    # every step that needs a browser is skipped when no page is touched
    for step in ('Install dependencies', 'Build the head', 'Build the base', 'Take the pictures', 'Upload the pictures'):
        block = t[t.index(f'- name: {step}'):]
        assert "steps.pages.outputs.pages != ''" in block.split('\n      - ')[0], step


def glob_matches(pattern, path):
    return fnmatch(path, pattern.replace('**', '*'))


@pytest.mark.parametrize('prefix', [p for p, _ in sp.RULES], ids=[p for p, _ in sp.RULES])
def test_every_file_a_rule_names_can_start_the_workflow(prefix):
    paths = re.findall(r"^      - '([^']+)'$", text(WORKFLOW).split('permissions:')[0], re.M)
    sample = prefix + 'x' if prefix.endswith('/') else prefix
    assert any(glob_matches(p, sample) for p in paths), f'{prefix} changes no trigger path of spotter.yml'
