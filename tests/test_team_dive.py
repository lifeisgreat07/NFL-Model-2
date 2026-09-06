"""
Guards the Team Deep-Dive page: its data actually loads, and its drill-down
shows the selected team's side of each game rather than the home team's.

Two separate failures live here, and the first one is the reason the second
was worth guarding at all.

THE PAGE WAS SILENTLY EMPTY. load_team_history() reads data/team_history.json;
the file had been sitting in src/ since it was uploaded. The missing-file
branch returned {} and said nothing, so every build produced a Team Deep-Dive
page reading "No team history data available yet" for all 32 teams -- while
the roadmap listed the page as Done and the page description promised
"2020-2025 season-end snapshots". A branch that returns empty and stays quiet
produces a page that looks deliberate.

THE FLIP IS INVISIBLE WHEN WRONG. Everything in `weeks` is stored from the
HOME side. A drill-down built around one selected team has to invert
probabilities, the line, the result and the contribution signs whenever that
team is away -- and 55.7% is exactly as plausible as 44.3%. Nothing about the
wrong number looks wrong.

tests/team_dive_harness.js executes the shipped teamGamesFor() rather than
matching strings, for the same reason as the share-link tests: string matching
proves the text is present, not that it works. Requires node; skipped loudly
if absent.

Run with: pytest tests/test_team_dive.py -v
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
HARNESS = Path(__file__).parent / 'team_dive_harness.js'
HISTORY = REPO_ROOT / 'data' / 'team_history.json'
GENERATED = REPO_ROOT / 'index.html'
GENERATOR = REPO_ROOT / 'src' / 'generate_dashboard.py'

NODE = shutil.which('node')


# --------------------------------------------------------------------------
# The regression: is the data where the loader looks?
# --------------------------------------------------------------------------

def test_the_history_file_is_where_the_loader_reads_it():
    """The whole bug in one assertion. generate_dashboard.load_team_history()
    reads data/team_history.json; the file lived in src/ and the page was
    empty for months without anything saying so."""
    assert HISTORY.exists(), (
        "data/team_history.json is missing -- the Team Deep-Dive page will "
        "render 'No team history data available yet' for every team, and "
        "nothing else will complain")
    payload = json.loads(HISTORY.read_text())
    assert payload.get('names'), "team_history.json has no team names"
    assert payload.get('history'), "team_history.json has no rating history"
    assert len(payload['names']) == 32, (
        f"expected 32 teams, found {len(payload['names'])}")


def test_the_generator_looks_where_the_file_actually_is():
    """Guards the other direction: someone 'fixes' a future problem by
    pointing the loader at src/ again, and the committed data file is
    orphaned without any test noticing."""
    src = GENERATOR.read_text(encoding='utf-8')
    assert "DATA_DIR / 'team_history.json'" in src, (
        "load_team_history no longer reads data/team_history.json")


def test_a_missing_history_file_is_reported_loudly():
    """This project's stated rule is that the pipeline fails loudly rather
    than quietly degrading. The silent `return {}` is precisely why nobody
    noticed, so the branch has to say something."""
    src = GENERATOR.read_text(encoding='utf-8')
    marker = src.index("static_path = DATA_DIR / 'team_history.json'")
    branch = src[marker:marker + 900]
    assert 'WARNING' in branch, (
        "the missing-history branch still returns empty without a warning -- "
        "the exact silence that hid this for months")


def test_the_generated_page_actually_carries_the_history():
    """The end-to-end check. Everything above can pass while the page still
    ships an empty object, which is what it was doing."""
    if not GENERATED.exists():
        pytest.skip("index.html absent -- run src/generate_dashboard.py")
    page = GENERATED.read_text(encoding='utf-8')
    assert 'const teamHistory = {}' not in page.replace(' ', ''), (
        "the generated page carries an empty teamHistory, so the Team "
        "Deep-Dive page renders its empty state for every team")
    payload = json.loads(HISTORY.read_text())
    a_team = sorted(payload['names'])[0]
    assert f'"{a_team}"' in page, (
        f"{a_team} does not appear in the generated page's team history")


# --------------------------------------------------------------------------
# The flip: does the drill-down show the selected team's side?
# --------------------------------------------------------------------------

@pytest.fixture(scope='module')
def flip():
    if NODE is None:
        pytest.skip("node not on PATH -- the flip logic cannot be executed")
    proc = subprocess.run([NODE, str(HARNESS)], cwd=REPO_ROOT,
                          capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, f"harness failed:\n{proc.stderr}"
    data = json.loads(proc.stdout)
    assert 'fatal' not in data, data.get('fatal')
    return data


def test_a_team_sees_both_its_home_and_away_games(flip):
    s = flip['selection']
    assert s['den_game_count'] == 2, (
        "the selected team's list is not picking up games from both sides")
    assert s['den_sees_both_home_and_away'], (
        "the drill-down only found games on one side of the fixture")
    assert s['lv_game_count'] == 1


def test_win_probabilities_flip_to_the_selected_team(flip):
    """The core of it. The stored value is a HOME win probability; an away
    team's chance is the complement, and showing the raw number under their
    name would report the opponent's chance as theirs."""
    p = flip['probability_flip']
    assert p['home_unchanged'], (
        f"the home side's probability was altered ({p['home_probA']})")
    assert p['sums_to_100'], (
        f"home {p['home_probA']} and away {p['away_probA']} do not sum to 100 "
        f"-- one of the two sides is being shown the wrong number")
    assert p['away_probB_sums'], "Model B's probability does not flip"


def test_the_betting_line_inverts_for_the_away_side(flip):
    """spread_line is the home team's line, positive when home is favoured.
    Left unflipped, a 9.5-point underdog is displayed as a 9.5-point
    favourite."""
    l = flip['line_flip']
    assert l['home_matches_raw'], "the home line was altered"
    assert l['inverts'], (
        f"home line {l['home_line']} and away line {l['away_line']} are not "
        f"inverses -- one side is shown the wrong favourite")


def test_the_result_flips_so_both_sides_cannot_win(flip):
    r = flip['result_flip']
    assert r['home_won_is_true'], "the home team's win was not recorded as a win"
    assert r['opposite'], (
        "both sides of the same game report the same result -- actual_home_win "
        "is not being inverted for the away team")


def test_contribution_signs_negate_for_the_away_side(flip):
    """why{} points toward the home team. Unflipped, the away view shows the
    reasons the OPPONENT was favoured, labelled as its own."""
    w = flip['why_negation']
    assert w['all_negate'], (
        f"contributions do not negate between sides:\nhome {w['home']}\n"
        f"away {w['away']}")


def test_correctness_survives_being_stored_as_one_and_zero(flip):
    """The graded files store 1/0, not true/false. A downstream `=== true`
    against a 1 is quietly false -- which showed up as 'Model A called 0 of 1'
    printed beside a game the model had plainly got right, and as the
    correct/wrong marks silently not rendering."""
    c = flip['correctness_normalised']
    assert c['a_raw'] == 1 and c['b_raw'] == 0, "fixture no longer tests 1/0 input"
    assert c['a_is_strict_true'], (
        "a graded-correct value of 1 does not become boolean true, so strict "
        "comparisons downstream silently fail")
    assert c['b_is_strict_false'], "a graded-wrong value of 0 does not become false"
    assert c['asBool_one'] is True and c['asBool_zero'] is False
    assert c['asBool_null'] is None and c['asBool_undefined'] is None, (
        "asBool collapses 'not graded' into a boolean, which would report "
        "unplayed games as wrong predictions")


def test_an_ungraded_game_reports_no_result_rather_than_a_loss(flip):
    """The tri-state that matters. Folding 'not played yet' into false would
    show every upcoming fixture as a loss and a failed prediction."""
    u = flip['ungraded']
    assert u['won'] is None, "an unplayed game reports a win/loss"
    assert u['probs_still_flipped'], (
        "probabilities stop flipping for ungraded games")
    assert flip['correctness_normalised']['ungraded_stays_null']


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))
