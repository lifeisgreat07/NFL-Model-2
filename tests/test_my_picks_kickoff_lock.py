"""My Picks locks at kickoff, and only picks made before kickoff are counted.

Stage 11's first item (CLAUDE.md, "Stage 11 - Integrity and access"). Before
it, writing every graded winner into `nfl_pickem_my_picks` put "My picks
100.0%, 32 of 32" on Season Accuracy (measured 2026-09-26, recorded in
docs/design/UX-REVIEW-2026-09-26.md). That was the one number on the page a
visitor could make false by clicking.

The pure half of the lock is EXECUTED here, under node, twice: once with
TZ=America/Los_Angeles and once with TZ=UTC. The defect worth guarding is a
kickoff read in the visitor's own zone, and that defect is invisible to anyone
sitting in New York -- so the two runs must agree, and each must equal the
instants written below by hand from the US daylight-saving rule.

The DOM half (the tap handler, Undo, the paint) cannot run without a browser
here, so it is held by source guards that name the one call each path must
make before it writes.

Run with: pytest tests/test_my_picks_kickoff_lock.py -v
"""
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from src.pipeline.template_parts import JOINED_TEMPLATE

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = JOINED_TEMPLATE
HARNESS = Path(__file__).parent / 'my_picks_lock_harness.js'
NODE = shutil.which('node')


@pytest.fixture(scope='module')
def source():
    return TEMPLATE.read_text(encoding='utf-8')


def _run(tz):
    env = dict(os.environ, TZ=tz)
    r = subprocess.run([NODE, str(HARNESS)], capture_output=True, text=True,
                       encoding='utf-8', errors='replace', env=env)
    assert r.returncode == 0, f'harness failed under TZ={tz}:\n{r.stderr}'
    out = json.loads(r.stdout)
    assert 'fatal' not in out, out['fatal']
    return out


@pytest.fixture(scope='module')
def runs():
    if not NODE:
        pytest.skip('node not available')
    return {'la': _run('America/Los_Angeles'), 'utc': _run('UTC')}


@pytest.fixture(scope='module')
def lock(runs):
    return runs['la']


def function_body(src, name):
    m = re.search(r'function ' + name + r'\(.*?\n\}\n', src, re.S)
    assert m, f'{name} is not findable -- re-anchor this guard'
    code = re.sub(r'/\*.*?\*/', '', m.group(0), flags=re.S)
    return re.sub(r'//.*', '', code)


def test_the_lock_does_not_depend_on_where_the_visitor_is(runs):
    """Same answers in Los Angeles and in UTC, for every case.

    A kickoff built as `new Date("2026-09-13T13:00")` is read in the
    visitor's zone: correct in New York, three hours late in Los Angeles.
    """
    assert runs['la'] == runs['utc']


def test_a_kickoff_is_its_eastern_time_as_an_instant(lock):
    """Real 2026 slots. Eastern daylight time is UTC-4 in September."""
    i = lock['instants']
    assert i['sundayEarly'] == '2026-09-13T17:00:00.000Z'
    assert i['london'] == '2026-09-13T13:30:00.000Z'
    # 20:15 Monday Eastern is already Tuesday in UTC.
    assert i['mondayNight'] == '2026-09-15T00:15:00.000Z'


def test_both_daylight_saving_edges_move_the_offset(lock):
    """UTC-4 through the last Sunday of October, UTC-5 from the first of
    November (2026-11-01 is itself that Sunday), and back to UTC-4 on the
    second Sunday of March. A fixed offset would be an hour wrong for half
    the season, and a lock an hour late is the whole defect again."""
    i = lock['instants']
    assert i['lastDaylightSunday'] == '2026-10-25T17:00:00.000Z'
    assert i['fallBackSunday'] == '2026-11-01T18:00:00.000Z'
    assert i['standardSunday'] == '2026-11-08T18:00:00.000Z'
    assert i['january'] == '2027-01-10T21:30:00.000Z'
    assert i['dayBeforeSpringForward'] == '2027-03-13T18:00:00.000Z'
    assert i['springForwardSunday'] == '2027-03-14T17:00:00.000Z'


def test_an_unknown_time_locks_early_and_an_unknown_day_not_at_all(lock):
    """A day with no time locks from the start of that day, Eastern -- early
    rather than late. No day at all is "unknown", which locks only once the
    game is graded."""
    assert lock['instants']['dayOnly'] == '2026-09-13T04:00:00.000Z'
    assert lock['instants']['undated'] is None
    assert lock['locks']['undatedUngraded'] is False
    assert lock['locks']['gradedUndatedEarly'] is True


def test_a_game_locks_at_kickoff_and_not_a_minute_before(lock):
    l = lock['locks']
    assert l['minuteBefore'] is False
    assert l['atKickoff'] is True
    assert l['after'] is True


def test_a_graded_game_is_locked_whatever_the_clock_says(lock):
    """Belt and braces: a wrong clock or a wrong kickoff must not reopen a
    game whose result is already on the page."""
    assert lock['locks']['gradedBeforeKickoff'] is True


def test_only_a_pick_made_before_kickoff_counts(lock):
    v = lock['verdicts']
    assert v['before'] == 'counted'
    assert v['atKickoff'] == 'late'
    assert v['after'] == 'late'
    assert v['none'] == 'untimed'
    assert v['garbage'] == 'untimed'
    assert v['unknownKickoff'] == 'untimed'


def test_winners_written_in_after_the_results_count_for_nothing(lock):
    """The measured exploit: every graded winner, picked after the fact."""
    t = lock['tallies']['allWinnersAfterResults']
    assert (t['wins'], t['losses']) == (0, 0)
    assert t['late'] == 4


def test_a_pick_saved_before_this_change_is_kept_but_not_counted(lock):
    t = lock['tallies']['legacy']
    assert (t['wins'], t['losses'], t['untimed']) == (0, 0, 4)


def test_the_race_counts_exactly_the_picks_made_before_kickoff(lock):
    """Two in time (one right, one wrong), one late, one with no time."""
    t = lock['tallies']['mixed']
    assert t == {'wins': 1, 'losses': 1, 'late': 1, 'untimed': 1}
    assert lock['tallies']['ungraded'] == {'wins': 0, 'losses': 0, 'late': 0, 'untimed': 0}


def test_the_page_says_how_many_it_left_out_and_why(lock):
    s = lock['sentences']
    assert s['none'] == ''
    assert s['oneLate'] == '1 of your graded picks is not counted: 1 made after kickoff.'
    assert s['oneUntimed'] == ('1 of your graded picks is not counted: '
                               '1 with no record of when it was made.')
    assert s['mixed'] == ('5 of your graded picks are not counted: 2 made after '
                          'kickoff, 3 with no record of when they were made.')


def test_the_badge_says_none_counted_rather_than_none_graded(lock):
    """Graded picks that were all made late or have no time are graded: the
    badge says none of them counted, and why (Stage 37 item 1, Mark's
    observation in the 2026-10-04 audit)."""
    s = lock['sentences']
    assert s['badgeCounted'] == '3-1 on graded picks (2 not counted)'
    assert s['badgeNoneCounted'] == '0 counted: 3 graded picks made after kickoff or with no time'
    assert s['badgeOneNotCounted'] == '0 counted: 1 graded pick made after kickoff or with no time'
    assert s['badgeNothing'] == 'No graded picks yet'


def test_only_a_game_still_to_come_has_an_untimed_pick_stamped(lock):
    """Now is an honest "made no later than" only before kickoff."""
    st = lock['stamp']
    assert st['stamped'] == 1
    assert st['times']['w|OH|OA'] == st['nowIso']
    assert 'w|LH|LA' not in st['times']
    assert st['times']['w|TH|TA'] == '2026-09-01T00:00:00.000Z'


def _strip(code):
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.S)
    return re.sub(r'//.*', '', code)


@pytest.fixture(scope='module')
def tap_handler(source):
    """The pick button's click handler, from its listener to its Undo offer.

    Anchored on the one line only this handler has, then walked back to the
    listener that owns it, and size-checked before anything is read off it
    (CLAUDE.md: anchor on something that occurs once).
    """
    clicked = source.find('const clicked = btn.dataset.team;')
    assert clicked != -1, 'the pick handler is no longer findable'
    start = source.rfind("btn.addEventListener('click', ()=>{", 0, clicked)
    end = source.find('showUndoToast();', clicked)
    assert start != -1 and end != -1, 'the pick handler lost its listener or its Undo'
    block = source[start:end]
    assert len(block) < 3500, f'handler capture is {len(block)} chars -- re-anchor it'
    return _strip(block)


def test_a_tap_after_kickoff_is_refused_before_anything_is_written(tap_handler):
    """`disabled` alone is not enough: a page left open across a kickoff
    keeps live buttons until something repaints the card."""
    check = tap_handler.find('isPickLocked(')
    save = tap_handler.find('saveMyPicks(')
    assert check != -1, 'the pick handler no longer asks whether the game is locked'
    assert save != -1, 'the pick handler no longer saves'
    assert check < save, 'the lock is checked only after the pick is saved'
    assert 'return;' in tap_handler[check:save], (
        'the handler checks the lock but carries on to save anyway')


def test_every_pick_is_stored_with_the_time_it_was_made(tap_handler):
    assert re.search(r'times\[pid\]\s*=\s*new Date\(\)\.toISOString\(\)', tap_handler), (
        'a new pick is saved without the time it was made')
    assert re.search(r'delete times\[pid\]', tap_handler), (
        'clearing a pick leaves its time behind for the next pick to inherit')
    assert 'savePickTimes(' in tap_handler, 'pick times are computed and never saved'


def test_undo_after_kickoff_is_refused(source):
    """Undo writes a pick too; after kickoff it is a late change."""
    m = re.search(r"document\.getElementById\(.undo-action.\)\.onclick.*?\n  \};", source, re.S)
    assert m, 'the Undo handler is no longer findable'
    undo = _strip(m.group(0))
    check, save = undo.find('isPickLocked('), undo.find('saveMyPicks(')
    assert check != -1 and save != -1 and check < save, (
        'Undo restores a pick without asking whether the game has kicked off')
    assert 'previousAt' in undo, 'Undo restores the pick but not the time it was made'


def test_every_record_on_the_page_goes_through_the_one_tally(source):
    """Four records, one rule. The loops these replaced each re-derived the
    winner by hand, which is four places to forget the lock."""
    for name in ('refreshPickTotals', 'renderPicksStreak',
                 'buildCumulativeTrendChart', 'renderAccuracy'):
        body = function_body(source, name)
        assert 'tallyMyPicks(' in body, f'{name} no longer counts through tallyMyPicks'
        assert not re.search(r'actual_home_win\s*\?\s*g\.home\s*:\s*g\.away', body), (
            f'{name} decides a pick right or wrong by itself again, outside the lock')


def test_the_scoreboard_says_what_it_left_out(source):
    body = function_body(source, 'renderAccuracy')
    assert 'leftOutSentence(' in body, 'Season Accuracy no longer says what it left out'
    # That the scoreboard prints it is executed in tests/test_scoreboard.py
    # (test_the_left_out_sentence_is_printed), which replaced a text check
    # here (Stage 31 item 12).


def test_a_locked_card_is_disabled_and_says_so(source):
    paint = function_body(source, 'paintPickCard')
    assert re.search(r'btn\.disabled\s*=\s*locked', paint), (
        'paintPickCard no longer disables a locked card')
    assert 'locked at kickoff' in paint, (
        "a locked button's accessible name no longer says it is locked")
    assert 'pickLockHtml(' in paint, 'the lock line is no longer painted'


def test_a_changed_pick_never_keeps_the_old_pick_time(source):
    """A link carries no times, so wherever an import replaced a pick the
    old time must go with the old pick."""
    body = function_body(source, 'importSharedPicks')
    assert re.search(r'existing\[k\]\s*!==\s*merged\[k\]\)\s*delete times\[k\]', body), (
        'a shared import can leave a pick paired with the time of the pick it replaced')
    assert 'savePickTimes(' in body
