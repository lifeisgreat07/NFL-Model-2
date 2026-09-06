"""
Runs the dashboard's real share-link code and checks what it actually does.

The picks share link puts one week of picks inside a URL fragment. It is
positional -- one character per game, in the week's own order -- which is what
keeps the link short enough to survive being pasted into a chat window, and is
also its one real hazard: decoded against a schedule that differs from the
sender's, every pick lands on the wrong fixture and the result looks entirely
normal. Nothing about a wrong-but-plausible pick set announces itself.

So the link carries a fingerprint of the schedule it was made from, and the
tests that matter here are the refusals, not the happy path.

These do not reimplement the encoding. tests/share_link_harness.js lifts the
functions out of dashboard_template.html and executes them, so this fails when
the shipped code changes. A Python reimplementation would only ever prove that
two implementations agree, and the template's could rot untouched underneath
it. The existing string-matching guards elsewhere in this suite prove certain
text is present; this proves the behaviour.

Requires node. Skipped, loudly, if it is absent.

Run with: pytest tests/test_share_link.py -v
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
HARNESS = Path(__file__).parent / 'share_link_harness.js'
TEMPLATE = REPO_ROOT / 'src' / 'dashboard_template.html'

NODE = shutil.which('node')
pytestmark = pytest.mark.skipif(
    NODE is None,
    reason="node not on PATH -- the share-link behaviour cannot be executed")


@pytest.fixture(scope='module')
def results():
    proc = subprocess.run([NODE, str(HARNESS)], cwd=REPO_ROOT,
                          capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, f"harness failed:\n{proc.stderr}"
    data = json.loads(proc.stdout)
    # The harness reports its own failure to find the code rather than
    # silently testing an empty string.
    assert 'fatal' not in data, data.get('fatal')
    return data


def test_a_link_round_trips_to_exactly_the_picks_that_made_it(results):
    r = results['round_trip']
    assert r['error'] is None, r['error']
    assert r['picked'] == 3
    assert r['matches'], (
        f"decoding a link did not return the picks that were encoded:\n"
        f"{r['decoded']}")


def test_a_week_with_no_picks_produces_no_link(results):
    assert results['no_picks_yields_no_link']['token'] is None, (
        "a week with nothing picked still produced a share link, which would "
        "send someone a link to an empty board")


def test_the_link_stays_short_enough_to_paste(results):
    """The reason this is one week rather than the whole log. A four-game
    fixture encodes in well under 100 characters; a real 16-game week is only
    twelve characters longer, since it is one character per game."""
    assert results['token_stays_short']['length'] < 100, (
        f"the token is {results['token_stays_short']['length']} chars for a "
        f"four-game week -- the encoding has stopped being positional and a "
        f"real week will not survive being pasted into a chat client")


@pytest.mark.parametrize('case', [
    'tampered_fingerprint_refused',
    'truncated_bits_refused',
    'wrong_version_refused',
    'unknown_week_refused',
    'malformed_token_refused',
])
def test_a_broken_link_is_refused_with_a_reason(results, case):
    r = results[case]
    assert r.get('error'), f"{case}: the link was ACCEPTED -- {r}"
    assert not r.get('picks'), f"{case}: picks were decoded despite the error"
    assert len(r['error']) > 30, (
        f"{case}: refused, but with a message too terse to tell anyone what "
        f"happened: {r['error']!r}")


def test_a_reordered_schedule_is_refused_rather_than_silently_misaligned(results):
    """The failure the fingerprint exists to prevent.

    Same week, same number of games, different order. Every length check
    passes. Decoding positionally would hand each pick to the wrong fixture
    and produce a complete, confident, entirely wrong pick set -- the worst
    available outcome, because nothing about it looks wrong.
    """
    r = results['reordered_schedule_refused']
    assert r['same_length'], "the fixture no longer tests a same-length reorder"
    assert r['error'], (
        "a reordered schedule was accepted; the picks would have been "
        f"attached to the wrong games: {r['would_have_been']}")
    assert r['would_have_been'] is None


def test_a_flipped_home_and_away_is_refused(results):
    """The subtlest version: the fixture still exists, but the sides swapped,
    so a decoded pick would flip to the other team."""
    assert results['flipped_home_away_refused'].get('error'), (
        "a schedule with home and away swapped on one game was accepted -- "
        "that pick would silently become a pick for the opponent")


def test_the_link_travels_in_the_fragment_not_the_query_string():
    """A deliberate privacy choice, and one that is easy to undo by accident.
    Fragments are never sent to the server, so sharing picks does not put them
    into GitHub Pages' request logs."""
    page = TEMPLATE.read_text(encoding='utf-8')
    assert "'#picks=' + encoded.token" in page, (
        "the share link no longer uses the URL fragment; if it moved to a "
        "query string, every shared pick set reaches the server's logs")


def test_opening_a_share_link_cannot_write_to_this_device():
    """The shared view renders someone else's picks. If it read or wrote the
    local store, looking at a friend's week would quietly become editing your
    own log -- and the Season Accuracy page is scored from that log."""
    page = TEMPLATE.read_text(encoding='utf-8')
    assert 'const myPicks = sharedPicksView ? sharedPicksView.picks : loadMyPicks();' in page, (
        "the picks grid no longer prefers the shared picks over local storage")
    assert 'if(sharedPicksView) return;' in page, (
        "the pick-button click handlers are no longer suppressed in shared "
        "view, so tapping someone else's pick can write to this device")


def test_a_share_link_pasted_into_an_open_tab_still_works():
    """Only the fragment changes, so the browser does not reload and none of
    the page's init code runs again. Without this listener the link appears to
    do nothing at all -- which is exactly how it behaved when the receive path
    was first tested as a second visit rather than a fresh load."""
    page = TEMPLATE.read_text(encoding='utf-8')
    assert "addEventListener('hashchange'" in page, (
        "nothing listens for hashchange, so a share link pasted into a tab "
        "that already has the dashboard open silently does nothing")


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))
