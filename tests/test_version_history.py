"""
Holds config.VERSION_HISTORY and MODEL_VERSION to each other, and to the page.

config.py has always instructed the reader to "bump this whenever the feature
set or a tuned constant changes", and nothing enforced it. The history also
lived in a comment, which meant the only thing connecting the release notes to
the model was that someone remembered. This project has a standing rule about
exactly that -- published numbers must be tied to their data file by a test,
because prose drifts -- and a Changelog page generated from a comment would
have been the same failure in a new place.

So VERSION_HISTORY is a real list now, the page is generated from it, and
these are the ends being held together.

Run with: pytest tests/test_version_history.py -v
"""
import json
import re
import sys
from datetime import date
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / 'src'))

from config import MODEL_VERSION, VERSION_HISTORY

TEMPLATE = REPO_ROOT / 'src' / 'dashboard_template.html'
GENERATED = REPO_ROOT / 'index.html'
REQUIRED = ('version', 'date', 'headline', 'detail')


def _tuple(v):
    return tuple(int(part) for part in v.split('.'))


def test_the_running_version_has_an_entry_and_is_the_newest_one():
    """The guard the comment in config.py has been asking for all along.

    Bumping MODEL_VERSION without writing the entry leaves the site announcing
    an older release than the one actually generating predictions -- and it is
    the saved predictions, which carry MODEL_VERSION, that become impossible
    to trace back to what produced them.
    """
    versions = [e['version'] for e in VERSION_HISTORY]
    assert MODEL_VERSION in versions, (
        f"MODEL_VERSION is {MODEL_VERSION!r} but VERSION_HISTORY has no entry "
        f"for it (has {versions}) -- every release needs its note")
    assert VERSION_HISTORY[0]['version'] == MODEL_VERSION, (
        f"MODEL_VERSION is {MODEL_VERSION!r} but the newest entry is "
        f"{VERSION_HISTORY[0]['version']!r}; the list is newest-first, so "
        f"either the bump or the entry is in the wrong place")


def test_every_entry_is_complete():
    """A half-written entry renders as a heading with nothing under it."""
    for i, e in enumerate(VERSION_HISTORY):
        for field in REQUIRED:
            assert field in e, f"entry {i} ({e.get('version','?')}) has no {field!r}"
            assert str(e[field]).strip(), (
                f"entry {e.get('version','?')} has an empty {field!r}, which "
                f"renders as a blank row on the Changelog page")


def test_versions_are_unique():
    versions = [e['version'] for e in VERSION_HISTORY]
    dupes = {v for v in versions if versions.count(v) > 1}
    assert not dupes, (
        f"duplicate version(s) {sorted(dupes)} -- 'Running now' would be "
        f"stamped on more than one entry, and a saved prediction carrying that "
        f"version could not be traced to a single release")


def test_the_list_runs_newest_first():
    """Both orderings, because they can disagree. Two releases can share a
    date (v2.3 and v2.4 both landed 2026-08-31), so dates may repeat -- but
    version numbers must strictly descend or the page reads as a jumble."""
    versions = [_tuple(e['version']) for e in VERSION_HISTORY]
    assert versions == sorted(versions, reverse=True), (
        f"versions are not in descending order: "
        f"{[e['version'] for e in VERSION_HISTORY]}")
    assert len(set(versions)) == len(versions), "version ordering has a tie"

    dates = [e['date'] for e in VERSION_HISTORY]
    assert dates == sorted(dates, reverse=True), (
        f"dates are not newest-first: {dates}. A later version dated before "
        f"an earlier one means one of the two dates is wrong")


@pytest.mark.parametrize('entry', VERSION_HISTORY, ids=lambda e: e['version'])
def test_dates_are_real_and_not_in_the_future(entry):
    """A typo'd date is invisible on the page -- it just reads as a date."""
    assert re.fullmatch(r'\d{4}-\d{2}-\d{2}', entry['date']), (
        f"v{entry['version']} has date {entry['date']!r}, not YYYY-MM-DD")
    parsed = date.fromisoformat(entry['date'])
    assert parsed <= date.today(), (
        f"v{entry['version']} is dated {entry['date']}, which is in the "
        f"future -- most likely a typo in the year or month")


def test_the_page_carries_the_real_history_not_a_hand_written_copy():
    """The whole point of the exercise. If the Changelog page ever stops being
    generated from config.py, this fails -- which is the moment the release
    notes and the model become free to disagree."""
    if not GENERATED.exists():
        pytest.skip("index.html absent -- run src/generate_dashboard.py")
    page = GENERATED.read_text(encoding='utf-8')

    for e in VERSION_HISTORY:
        assert json.dumps(e['headline'])[1:-1] in page, (
            f"v{e['version']}'s headline is not in the generated page, so the "
            f"page is no longer rendering config.VERSION_HISTORY")
    assert f'const modelVersion = "{MODEL_VERSION}"' in page, (
        "the page does not carry the running MODEL_VERSION, so it cannot mark "
        "which release is live")


def test_the_current_release_badge_is_derived_not_stored():
    """'Running now' has to be computed by comparing against MODEL_VERSION.

    A stored flag would let config.py say one thing and the page say another,
    which is the exact class of drift this file exists to prevent -- and it
    would be invisible, because a stale flag still renders as a confident
    badge."""
    tpl = TEMPLATE.read_text(encoding='utf-8')
    assert 'v.version === modelVersion' in tpl, (
        "the Changelog no longer decides 'Running now' by comparing the entry "
        "against MODEL_VERSION")
    for e in VERSION_HISTORY:
        assert 'current' not in e and 'is_current' not in e, (
            f"v{e['version']} stores a current-release flag; that is the "
            f"model's job to answer, not the changelog's to remember")


def test_release_notes_are_escaped_before_they_reach_the_page():
    """This text comes out of a hand-edited Python file. An unescaped '<' in a
    release note would break the page that note is describing."""
    tpl = TEMPLATE.read_text(encoding='utf-8')
    assert 'function clEscape(' in tpl, "the changelog escape helper is gone"
    for field in ('version', 'date', 'headline', 'detail'):
        assert f'clEscape(v.{field})' in tpl, (
            f"the changelog interpolates v.{field} without escaping it")


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))
