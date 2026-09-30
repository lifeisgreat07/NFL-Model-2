"""
The browser checks also run on pages built in the states no real week is in
yet: a tied game, a skipped week, a preview past its kickoff (Stage 34 item
30). tests/browser/build_states.py builds them from the saved weeks; this
file holds that it still does, and that CI checks what it builds.

Run with: pytest tests/test_states_pages.py -v
"""
import importlib.util
import json
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
    """(builder, folder, None) -- or the reason, if a page came out without
    its state. Not raised here: an error in a fixture would take every test
    down as an error, and none of them would say which state was missing."""
    builder = load_builder()
    out = tmp_path_factory.mktemp('states')
    try:
        builder.main(['--out', str(out)])
        missing = None
    except builder.StateMissing as e:
        missing = str(e)
    return builder, out, missing


def test_both_pages_are_built(built):
    builder, out, missing = built
    assert missing is None, missing
    assert sorted(p.name for p in out.glob('*.html')) == sorted(builder.PAGES)


def test_the_tie_page_carries_a_tied_final(built):
    builder, out, missing = built
    assert missing is None, missing
    weeks = builder.weeks_json((out / 'states_tie.html').read_text(encoding='utf-8'))
    ties = [g for w in weeks.values() for g in w['games'] if g.get('result') == 'tie']
    assert len(ties) == 1, ties
    tie = ties[0]
    assert (tie['status'], tie['home_score'], tie['away_score']) == ('final', 20, 20), tie
    assert tie['model_a_correct'] is None and tie['model_b_correct'] is None


def test_the_tie_page_renders_exactly_one_tie_tag(built):
    """What a reader sees, not what the JSON holds: the page's own
    gradedTagHtml, run over every card. The JSON check above counted one tie
    while the board showed sixteen (Stage 35, the third audit)."""
    builder, out, missing = built
    assert missing is None, missing
    assert builder.rendered_tie_tags((out / 'states_tie.html').read_text(encoding='utf-8')) == 1


def test_a_locked_week_not_graded_yet_does_not_take_the_tie(tmp_path):
    """From each Thursday lock to Tuesday's grading, the latest locked week
    has no graded file. Replayed here with the saved weeks plus one newer
    week that is locked and ungraded: the tie must go in the latest GRADED
    week, the newer week must be left off the page, and one card must read
    "Tie". Before Stage 35 the builder graded the newer week's raw picks
    and all sixteen of its cards read "Tie"."""
    builder = load_builder()
    weeks = builder.saved_weeks()
    graded_latest = max(k for k, (_, g, _) in weeks.items() if g)
    newest = max(weeks)
    locked = (newest[0], newest[1] + 1)
    weeks[locked] = (weeks[newest][0], None, None)
    page = builder.build(tmp_path, 'tie', weeks).read_text(encoding='utf-8')
    shown = {builder.parse_week(k) for k in builder.weeks_json(page)}
    assert locked not in shown and max(shown) == graded_latest, sorted(shown)
    assert builder.rendered_tie_tags(page) == 1


def test_the_preview_page_shows_the_stale_preview_and_hides_the_skipped_week(built):
    builder, out, missing = built
    assert missing is None, missing
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
    with pytest.raises(builder.StateMissing, match='no tied game'):
        builder.check('tie', page, ('GB', 'ATL'))
    with pytest.raises(builder.StateMissing, match='must show only the stale preview'):
        builder.check('preview', page, ((2026, 4), (2026, 5)))


def test_a_tie_page_with_more_than_one_tie_tag_fails_the_build():
    """The rendered check can fail: two graded cards with no verdict, the
    shape the old builder produced sixteen of."""
    builder = load_builder()
    fn = ("function gradedTagHtml(g){\n  if(!g.graded) return '';\n"
          "  const verdict = g.model_b_correct ?? g.model_a_correct;\n"
          "  if(g.result === 'tie' || verdict === null || verdict === undefined)\n"
          "    return `<span class=\"graded-tag tie\">Tie</span>`;\n  return '';\n}\n")
    games = [{'home': 'GB', 'away': 'ATL', 'graded': True, 'result': 'tie'},
             {'home': 'KC', 'away': 'BUF', 'graded': True, 'result': None,
              'model_a_correct': None, 'model_b_correct': None}]
    page = (fn + 'const weeks = ' + json.dumps({'2026_week3': {'season': 2026, 'week': 3, 'games': games}}) + ';')
    with pytest.raises(builder.StateMissing, match='renders 2 "Tie" tags'):
        builder.check('tie', page, ('GB', 'ATL'))


def test_ci_builds_the_states_pages_and_checks_each_one():
    text = WORKFLOW.read_text(encoding='utf-8')
    assert re.search(r'run: python tests/browser/build_states\.py --out "\$RUNNER_TEMP/states"', text)
    loop = re.search(r'for page in ([\w. ]+); do\s+python tests/browser/check_page\.py '
                     r'"\$RUNNER_TEMP/states/\$page" --axe node_modules/axe-core/axe\.min\.js', text)
    assert loop, 'the workflow no longer runs check_page on the states pages'
    builder = load_builder()
    assert sorted(loop.group(1).split()) == sorted(builder.PAGES)
