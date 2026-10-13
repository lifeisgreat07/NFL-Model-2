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
    opens_on = max(weeks, key=builder.parse_week)
    ties = [g for g in weeks[opens_on]['games'] if g.get('result') == 'tie']
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
    page = (out / 'states_tie.html').read_text(encoding='utf-8')
    opens_on = max(builder.weeks_json(page), key=builder.parse_week)
    assert builder.rendered_tie_tags(page, opens_on) == 1


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
    assert builder.rendered_tie_tags(page, f'{graded_latest[0]}_week{graded_latest[1]}') == 1


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


def test_a_week_with_a_real_tie_keeps_it_as_the_tie():
    """Week 5 of 2026 had a real tie (NYG 27, WAS 27). Tying another game
    beside it gave the page two "Tie" tags; the real one is the tie."""
    builder = load_builder()
    graded = [{'home': 'DAL', 'away': 'TB', 'result': None, 'actual_home_win': 0,
               'market_correct': 1, 'model_a_correct': 0, 'model_b_correct': 0},
              {'home': 'WAS', 'away': 'NYG', 'result': 'tie', 'actual_home_win': None,
               'market_correct': None, 'model_a_correct': None, 'model_b_correct': None}]
    out, status, tied = builder.with_a_tie(graded, None, 2026, 5)
    assert tied == ('WAS', 'NYG')
    assert [g['home'] for g in out if g.get('result') == 'tie'] == ['WAS']
    assert out[0]['model_a_correct'] == 0


def test_a_real_tie_in_an_earlier_week_does_not_fail_the_page():
    """Only the week the board opens on is counted: a real tie in an earlier
    week is a real result, not a second synthetic one."""
    builder = load_builder()
    fn = ("function gradedTagHtml(g){\n  if(!g.graded) return '';\n"
          "  const verdict = g.model_b_correct ?? g.model_a_correct;\n"
          "  if(g.result === 'tie' || verdict === null || verdict === undefined)\n"
          "    return `<span class=\"graded-tag tie\">Tie</span>`;\n  return '';\n}\n")
    tie = {'graded': True, 'result': 'tie'}
    weeks = {'2026_week4': {'season': 2026, 'week': 4, 'games': [dict(tie, home='NYG', away='WAS')]},
             '2026_week5': {'season': 2026, 'week': 5, 'games': [dict(tie, home='GB', away='ATL')]}}
    page = fn + 'const weeks = ' + json.dumps(weeks) + ';'
    builder.check('tie', page, ('GB', 'ATL'))


def test_a_week_without_a_tie_gets_one():
    """The builder's own job, held without the saved weeks: once a real week
    held a real tie, the built page stopped showing whether the builder
    could still make one (states-tie-never-tied survived on 2026-10-13)."""
    builder = load_builder()
    graded = [{'home': 'DAL', 'away': 'TB', 'result': None, 'actual_home_win': 0, 'spread_line': 9.5,
               'market_correct': 1, 'model_a_correct': 0, 'model_b_correct': 0},
              {'home': 'GB', 'away': 'CHI', 'result': None, 'actual_home_win': 1, 'spread_line': -1.5,
               'market_correct': 1, 'model_a_correct': 1, 'model_b_correct': 1}]
    out, status, tied = builder.with_a_tie(graded, None, 2026, 4)
    assert tied == ('DAL', 'TB')
    assert out[0]['result'] == 'tie' and out[0]['model_a_correct'] is None
    assert out[1]['result'] is None and out[1]['model_a_correct'] == 1
    [game] = status['games']
    assert (game['home'], game['status'], game['home_score'], game['away_score']) == ('DAL', 'final', 20, 20)
