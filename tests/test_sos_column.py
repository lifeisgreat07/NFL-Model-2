"""
Ties the Power Ratings SOS column to the data that produces it.

Worth recording why this file exists, because the premise it was written under
turned out to be wrong. A design audit on 2026-09-06 recorded SOS as "an
em-dash for all 32 teams" and queued the column to be removed or populated.
Neither was the right call. The computation in weekly_update.save_current_ratings
works; it returns None for all 32 teams because the 2026 season has not started,
and strength of schedule is defined over opponents ACTUALLY PLAYED. Confirmed
against data/playoff_odds.json, which independently reports games_played 0 and
games_remaining 272. Deleting the column would have removed a working feature
because it was audited in September.

What was genuinely missing is the ability to tell those two states apart. On
the dashboard a legitimate preseason blank and a broken pipeline render as the
same 32 em-dashes, and in the repo nothing tested the column at all.

So the failure this guards is the real one: SOS null when games HAVE been
played. That is silent today -- no test, no recompute, no visible difference.
The synthetic case below also does something the live artifact cannot do until
Week 1: it proves the column actually computes, months before the season can
demonstrate it.

Run with: pytest tests/test_sos_column.py -v
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / 'src'))

import weekly_update

TEMPLATE = REPO_ROOT / 'src' / 'dashboard_template.html'
LIVE_RATINGS = REPO_ROOT / 'data' / 'current_ratings.json'

# Three teams with deliberately distinct net ratings, so a wrong pairing shows
# up as a wrong number rather than coincidentally matching.
#   AAA net = 0.10 - 0.02  = +0.08
#   BBB net = 0.05 - 0.01  = +0.04
#   CCC net = 0.00 - 0.06  = -0.06
TEAM_RATINGS = {
    'AAA': (0.10, 0.02),
    'BBB': (0.05, 0.01),
    'CCC': (0.00, 0.06),
}


def _schedule(rows):
    return pd.DataFrame(
        rows, columns=['home_team', 'away_team', 'home_score', 'away_score'])


@pytest.fixture
def written(tmp_path, monkeypatch):
    """Runs save_current_ratings against a temp data dir and returns the rows.

    Monkeypatching DATA_DIR matters: the function writes straight to
    data/current_ratings.json, and a test that clobbered the live artifact
    would be corrupting the dashboard to check the dashboard.
    """
    def run(schedule):
        monkeypatch.setattr(weekly_update, 'DATA_DIR', tmp_path)
        weekly_update.save_current_ratings(TEAM_RATINGS, season_schedule=schedule)
        return {r['team']: r
                for r in json.loads((tmp_path / 'current_ratings.json').read_text())}
    return run


def test_sos_averages_the_opponents_a_team_actually_played(written):
    """The core computation, provable today without waiting for Week 1.

    Two games are scheduled; only one has been played. AAA and BBB met and
    have a result, so each carries the other's net rating. AAA also has an
    unplayed game against CCC, which must NOT count -- if it did, AAA's SOS
    would be the average of BBB and CCC (-0.01) instead of BBB alone (+0.04),
    and CCC would show a strength of schedule despite never taking the field.
    """
    rows = written(_schedule([
        ('AAA', 'BBB', 24, 17),          # played
        ('AAA', 'CCC', np.nan, np.nan),  # scheduled, not played
    ]))

    assert rows['AAA']['sos'] == pytest.approx(0.04), (
        "AAA's SOS should be BBB's net rating alone -- an unplayed game "
        "against CCC has leaked into the average")
    assert rows['BBB']['sos'] == pytest.approx(0.08)
    assert rows['AAA']['games_played'] == 1
    assert rows['BBB']['games_played'] == 1

    assert rows['CCC']['sos'] is None, (
        "CCC has played nobody, so it has no schedule to be strong or weak")
    assert rows['CCC']['games_played'] == 0


def test_sos_is_none_for_everyone_before_the_season_starts(written):
    """The state the dashboard is in right now, asserted rather than assumed."""
    rows = written(_schedule([
        ('AAA', 'BBB', np.nan, np.nan),
        ('BBB', 'CCC', np.nan, np.nan),
    ]))
    assert all(r['sos'] is None for r in rows.values())
    assert all(r['games_played'] == 0 for r in rows.values())


def test_sos_is_absent_only_when_no_games_have_been_played():
    """The invariant, checked against the live artifact the page reads.

    This is the one that will start doing real work in Week 1. A team with
    games behind it and no SOS means the schedule stopped reaching
    save_current_ratings, or opponent keys stopped matching the ratings dict --
    both of which currently look exactly like the preseason blank.
    """
    if not LIVE_RATINGS.exists():
        pytest.skip("data/current_ratings.json absent -- run weekly_update.py")
    rows = json.loads(LIVE_RATINGS.read_text())
    assert rows, "current_ratings.json is empty"

    for r in rows:
        played = r.get('games_played')
        assert played is not None, (
            f"{r['team']} has no games_played field, so the SOS column cannot "
            f"be told apart from a broken one")
        if played > 0:
            assert r.get('sos') is not None, (
                f"{r['team']} has played {played} game(s) but has no SOS -- "
                f"the column is broken, not merely early")
        else:
            assert r.get('sos') is None, (
                f"{r['team']} has played no games but reports an SOS of "
                f"{r.get('sos')}, which is a value averaged over nothing")


def test_the_page_says_why_the_column_is_empty_instead_of_showing_bare_dashes():
    """A column of 32 em-dashes with no explanation is indistinguishable from
    a broken feature, and that ambiguity is what got SOS queued for deletion
    in the first place. The page has to state which of the two it is."""
    page = TEMPLATE.read_text(encoding='utf-8')

    assert 'id="sos-empty-note"' in page, (
        "the empty-state note is gone -- an unexplained blank column is how "
        "this feature got misdiagnosed as broken")
    assert 'no games have been played yet' in page.lower(), (
        "the note no longer says why the column is blank")
    assert "getElementById('sos-empty-note')" in page, (
        "nothing toggles the note, so it is either always or never shown")


def test_the_note_hides_itself_once_sos_exists():
    """The note must be conditional. A permanently-visible 'no games played
    yet' would be its own wrong claim from Week 1 onward -- the page would be
    asserting an empty season while displaying real numbers beside it."""
    page = TEMPLATE.read_text(encoding='utf-8')
    assert 'anySos' in page and "sosNote.style.display = anySos ? 'none' : 'block'" in page, (
        "the note is no longer driven by whether any team actually has an "
        "SOS, so it will keep claiming the season has not started")


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))
