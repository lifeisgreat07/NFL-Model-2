"""
The browser checks also run on pages built in the states no real week is in
yet: a tied game, a skipped week, a preview past its kickoff (Stage 34 item
30). tests/browser/build_states.py builds them from the saved weeks; this
file holds that it still does, and that CI checks what it builds.

Run with: pytest tests/test_states_pages.py -v
"""
import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github' / 'workflows' / 'browser-checks.yml'


def load_builder():
    spec = importlib.util.spec_from_file_location('build_states', ROOT / 'tests' / 'browser' / 'build_states.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope='module')
def built(tmp_path_factory):
    builder = load_builder()
    out = tmp_path_factory.mktemp('states')
    builder.main(['--out', str(out)])
    return builder, out


def test_both_pages_are_built(built):
    builder, out = built
    assert sorted(p.name for p in out.glob('*.html')) == sorted(builder.PAGES)


def test_the_tie_page_carries_a_tied_final(built):
    builder, out = built
    weeks = builder.weeks_json((out / 'states_tie.html').read_text(encoding='utf-8'))
    ties = [g for w in weeks.values() for g in w['games'] if g.get('result') == 'tie']
    assert len(ties) == 1, ties
    tie = ties[0]
    assert (tie['status'], tie['home_score'], tie['away_score']) == ('final', 20, 20), tie
    assert tie['model_a_correct'] is None and tie['model_b_correct'] is None


def test_the_preview_page_shows_the_stale_preview_and_hides_the_skipped_week(built):
    builder, out = built
    weeks = builder.weeks_json((out / 'states_preview.html').read_text(encoding='utf-8'))
    previews = {k: w for k, w in weeks.items() if w.get('preview')}
    assert len(previews) == 1, sorted(previews)
    [(label, week)] = previews.items()
    # Every kickoff of the shown preview is in the past, so the page says
    # the lock run did not happen rather than promising a lock.
    assert all(g['gameday'] < '2026-09-29' for g in week['games']), week['games']
    locked = [k for k, w in weeks.items() if not w.get('preview')]
    season, n = builder.parse_week(label)
    assert f'{season}_week{n - 1}' not in weeks, 'the skipped week is on the page'
    assert max(builder.parse_week(k) for k in locked) == (season, n - 2)


def test_a_page_without_its_state_fails_the_build():
    """Synthetic, so the builder's own check stays able to fail."""
    builder = load_builder()
    page = 'const weeks = {"2026_week3": {"season": 2026, "week": 3, "games": [{"home": "GB", "away": "ATL", "result": null}]}};'
    with pytest.raises(SystemExit, match='no tied game'):
        builder.check('tie', page, ('GB', 'ATL'))
    with pytest.raises(SystemExit, match='must show only the stale preview'):
        builder.check('preview', page, ((2026, 4), (2026, 5)))


def test_ci_builds_the_states_pages_and_checks_each_one():
    text = WORKFLOW.read_text(encoding='utf-8')
    assert re.search(r'run: python tests/browser/build_states\.py --out "\$RUNNER_TEMP/states"', text)
    loop = re.search(r'for page in ([\w. ]+); do\s+python tests/browser/check_page\.py '
                     r'"\$RUNNER_TEMP/states/\$page" --axe node_modules/axe-core/axe\.min\.js', text)
    assert loop, 'the workflow no longer runs check_page on the states pages'
    builder = load_builder()
    assert sorted(loop.group(1).split()) == sorted(builder.PAGES)
