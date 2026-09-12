"""The Week Board opens in kickoff order, and the order is executed to check it.

The board used to open sorted by confidence. A week is a sequence of games
before it is a ranking of them -- the first question a reader has is what is on
next -- so the default is now first game to last, with confidence one click
away and still the tiebreak inside a single slot. Thirteen of week 1's sixteen
games start at the same minute, so without that tiebreak the sort would leave
most of the board in file order and look like it had done nothing.

Two things make this worth real tests rather than a glance:

  * A misordered card still looks like a card. Nobody reports it, and a
    screenshot does not disprove it.
  * The sort key is a STRING comparison on purpose. Constructing a Date from
    "2026-09-13" and "13:00" attaches the runtime's timezone to a value that is
    Eastern, so the board would reorder itself depending on where the reader is
    sitting. That is safe only while both halves stay zero-padded, which is
    asserted here against values transcribed from the real feed.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / 'src' / 'dashboard_template.html'
HARNESS = Path(__file__).parent / 'kickoff_order_harness.js'
NODE = shutil.which('node')


@pytest.fixture(scope='module')
def source():
    return TEMPLATE.read_text(encoding='utf-8')


@pytest.fixture(scope='module')
def ordered():
    if not NODE:
        pytest.skip('node not available')
    r = subprocess.run([NODE, str(HARNESS)], capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    assert r.returncode == 0, f'harness failed:\n{r.stderr}'
    out = json.loads(r.stdout)
    assert 'fatal' not in out, out['fatal']
    return out


def test_a_real_week_comes_out_in_kickoff_order(ordered):
    """Seven real week-1 slots, shuffled in and sorted by the shipped code."""
    assert ordered['fullWeek'] == [
        'NE@SEA',    # Wed 20:20, the opener
        'SF@LA',     # Thu 20:35
        'JAX@MIA',   # Sun 09:30, London
        'TB@CIN',    # Sun 13:00
        'CHI@CAR',   # Sun 13:00
        'ARI@LAC',   # Sun 16:25
        'DEN@KC',    # Mon 20:15
    ]


def test_the_london_kickoff_sorts_before_the_early_window(ordered):
    """The case a string compare gets wrong if an hour ever loses its zero.

    09:30 beats 13:00 lexically only because it is zero-padded. '9:30' would
    sort AFTER '13:00' and put the London game in the middle of the afternoon,
    which is exactly the sort of wrong that looks fine.
    """
    week = ordered['fullWeek']
    assert week.index('JAX@MIA') < week.index('TB@CIN')


def test_a_shared_kickoff_is_broken_by_confidence(ordered):
    """Otherwise thirteen of sixteen cards keep whatever order the file had."""
    assert ordered['tieBreak'] == ['TB@CIN', 'CHI@CAR']


def test_a_game_with_no_kickoff_sinks_rather_than_leading(ordered):
    """An unknown kickoff is unknown, not midnight.

    Not hypothetical: every saved week looked like this before the fields
    existed, and a week looks like it again if the schedule stops supplying
    them. Sorting an unknown first would put it above the opener.
    """
    assert ordered['undatedSinks'] == ['NE@SEA', 'TB@CIN', 'XX@YY']
    assert ordered['allUndated'] == ['C@D', 'A@B'], (
        'with nothing to order them by, undated games should still fall back '
        'to confidence rather than to file order')


def test_a_date_without_a_time_is_placed_at_the_start_of_its_day(ordered):
    assert ordered['keys']['dayOnly'] == '2026-09-13T00:00'
    assert ordered['keys']['undated'] is None
    assert ordered['dayOnlyPlacement'][0] == 'ZZ@WW'


def test_the_board_opens_in_kickoff_order(source):
    assert re.search(r"let currentSort = 'chronological';", source), (
        'the Week Board no longer opens in kickoff order. If that was '
        'deliberate it is a visible product change and belongs in a '
        'description, not in a diff nobody reads.')


def test_the_dropdown_and_the_initial_sort_cannot_disagree(source):
    """A coupling with no compiler behind it.

    `currentSort` is set in JavaScript; which option the browser shows is
    whichever `<option>` comes first in the markup. Nothing connects them. Move
    one without the other and the control reads "Most Confident First" over a
    board sorted by kickoff -- a page lying about itself, with every test
    green, which is this repository's most expensive failure shape.
    """
    initial = re.search(r"let currentSort = '([a-z_]+)';", source)
    assert initial, 'currentSort is no longer a simple literal to check'
    first_option = re.search(
        r'<select id="sort-select".*?<option value="([a-z_]+)"', source, re.S)
    assert first_option, 'the sort select no longer starts with an option'
    assert initial.group(1) == first_option.group(1), (
        f'the board sorts by {initial.group(1)!r} but the dropdown shows '
        f'{first_option.group(1)!r} as selected. One of them moved.')


def test_the_comparator_does_not_build_a_date(source):
    """The timezone trap, guarded at the only place it can be introduced.

    A Date built from an Eastern date and time is interpreted in the reader's
    zone, so the same board would order itself differently in Los Angeles than
    in New York -- and every card would still look correct. The string compare
    has no such failure mode, and the only way to lose it is to "improve" this
    into a Date.
    """
    block = re.search(r'function kickoffKey\(.*?function renderGames\(',
                      source, re.S)
    assert block, 'the kickoff comparator block is no longer findable'
    code = re.sub(r'/\*.*?\*/', '', block.group(0), flags=re.S)
    code = re.sub(r'//.*', '', code)
    assert 'new Date' not in code and 'Date.parse' not in code, (
        'the kickoff comparator now constructs a Date. The stored time is '
        'Eastern and a Date attaches the runtime timezone to it, so the board '
        'reorders itself by where the reader is sitting.')
