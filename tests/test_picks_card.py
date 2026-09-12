"""The My Picks card: when the game is, who you are picking, and nothing else.

Four changes, asked for together because they are one card rather than four
tweaks:

  * the kickoff, in words, on the card;
  * the "When picks looked this sure before" block off THIS card -- it still
    renders on the Week Board, twice;
  * a team logo above each abbreviation, so the thing you tap is recognisable
    rather than three capital letters;
  * Model B's pick stays.

The part that needs executing rather than reading is the kickoff. It converts
a 24-hour Eastern time into words, and every way it can be wrong produces a
plausible string: 20:20 as "8:20 AM", noon as "0:00 PM", midnight rolling to
"12:15 AM" on the wrong day, or the whole value silently carrying the reader's
timezone because somebody reached for a Date. A card showing the wrong kickoff
looks exactly like a card showing the right one.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / 'src' / 'dashboard_template.html'
HARNESS = Path(__file__).parent / 'picks_card_harness.js'
NODE = shutil.which('node')


@pytest.fixture(scope='module')
def source():
    return TEMPLATE.read_text(encoding='utf-8')


@pytest.fixture(scope='module')
def built():
    if not NODE:
        pytest.skip('node not available')
    r = subprocess.run([NODE, str(HARNESS)], capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    assert r.returncode == 0, f'harness failed:\n{r.stderr}'
    out = json.loads(r.stdout)
    assert 'fatal' not in out, out['fatal']
    return out


def test_the_kickoff_reads_as_a_time_a_person_would_say(built):
    assert built['evening'] == 'Wednesday, Sep 9 · 8:20 PM ET'
    assert built['earlyAfternoon'] == 'Sunday, Sep 13 · 1:00 PM ET'


def test_noon_and_midnight_are_the_two_that_go_wrong(built):
    """`hour % 12` is 0 for both, so the naive version prints "0:00".

    Noon as "0:00 PM" and a 12:15 AM kickoff as "0:15 AM" are the classic
    twelve-hour-clock defects, and both read as typos rather than as bugs --
    which means they get seen, shrugged at, and left.
    """
    assert built['noon'] == 'Sunday, Sep 13 · 12:00 PM ET'
    assert built['midnight'] == 'Sunday, Sep 13 · 12:15 AM ET'


def test_the_morning_kickoff_is_not_labelled_pm(built):
    """The London games start at 09:30 Eastern. An AM/PM comparison written
    as `>` rather than `>=`, or applied to the 12-hour value instead of the
    24-hour one, turns that into an evening game and nothing complains."""
    assert built['london'] == 'Sunday, Sep 13 · 9:30 AM ET'


def test_the_zone_is_always_stated(built):
    """The stored value is Eastern and the reader cannot know that.

    A kickoff printed without its zone is the same defect as a measured
    number printed without its method: unfalsifiable by anyone but the author,
    and wrong for most of the country in a way that still looks right.
    """
    for key in ('evening', 'earlyAfternoon', 'london', 'noon', 'midnight'):
        assert built[key].endswith(' ET'), (key, built[key])


def test_a_missing_kickoff_renders_nothing_rather_than_a_placeholder(built):
    """Absent stays absent. A week saved before these fields existed has no
    date, and '' renders no element at all -- where "TBD" would be a claim
    nobody made about when the game is."""
    assert built['undated'] == ''
    assert built['dayOnly'] == 'Sunday, Sep 13'
    assert built['noWeekday'] == 'Sep 13 · 1:00 PM ET'


def test_the_kickoff_label_does_not_build_a_date(source):
    """Same trap as the sort key, in the half that renders.

    A Date built from an Eastern date and time is interpreted in the runtime's
    zone, so the card would print a different kickoff depending on where the
    reader is -- and every one of those would look like a correct kickoff.
    """
    block = re.search(r'function kickoffLabel\(.*?\n\}', source, re.S)
    assert block, 'kickoffLabel is no longer findable'
    code = re.sub(r'//.*', '', block.group(0))
    assert 'new Date' not in code and 'toLocale' not in code, (
        'kickoffLabel now goes through a Date or a locale formatter, either of '
        'which attaches the reader timezone to a value that is Eastern')


def test_the_pick_button_is_a_logo_above_the_abbreviation(built):
    assert built['buttonUnpicked'] == (
        '<button class="pick-btn " data-team="NE">'
        '<img class="pick-logo" src="LOGO:NE" alt="" loading="lazy" '
        'onerror="this.style.display=\'none\'">'
        '<span class="pick-abbr">NE</span>'
        '</button>')


def test_the_logo_is_decorative_and_the_abbreviation_is_the_text(built):
    """Both would be read aloud otherwise, and the button's accessible name
    has to stay the abbreviation -- that is what the pick is recorded as."""
    assert 'alt=""' in built['buttonUnpicked']
    assert '<span class="pick-abbr">NE</span>' in built['buttonUnpicked']


def test_a_logo_that_fails_to_load_leaves_a_usable_button(source, built):
    """The images come from a third party. If that host is unreachable the
    tile has to remain pickable rather than showing a broken-image glyph,
    which is why the abbreviation is real text and not part of the picture."""
    assert "onerror=\"this.style.display='none'\"" in built['buttonUnpicked']


def test_only_the_chosen_team_carries_the_selected_class(built):
    assert 'pick-btn selected' in built['buttonPicked']
    assert 'selected' not in built['buttonOther']


def test_the_track_record_block_is_off_this_card_but_not_the_board(source):
    """Removed from My Picks only, and the distinction is the whole point.

    trackRecordHtml still renders twice on the Week Board -- once on the card
    and once inside the why-panel -- so deleting the function or dropping it
    everywhere would be a different and much larger change than the one asked
    for. Its entry in tests/test_plain_language.py moved from 'picks' to
    'board' for the same reason.
    """
    picks = re.search(r'grid\.innerHTML = gamesList\.map\(g=>\{.*?\}\)\.join',
                      source, re.S)
    assert picks, 'the My Picks card template is no longer findable'
    assert 'trackRecordHtml' not in picks.group(0), (
        'the "when picks looked this sure before" block is back on the My '
        'Picks card')
    assert source.count('trackRecordHtml(g.mktB_home') == 2, (
        'the Week Board should still render it twice -- on the card and in '
        'the why-panel. Removing it from My Picks must not remove it there.')


def test_the_card_still_says_what_model_b_picked(source):
    """Explicitly kept, so a later tidy-up does not read it as clutter."""
    picks = re.search(r'grid\.innerHTML = gamesList\.map\(g=>\{.*?\}\)\.join',
                      source, re.S)
    assert 'Model B picks:' in picks.group(0)
