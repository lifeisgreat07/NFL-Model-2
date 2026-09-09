"""The Week Board's plain-English reason, and the signs inside it.

Stage 7.5 asked for "a couple of plain sentences on why a team is favoured, in
football terms". The data already existed: the football-only model records each
feature's contribution, signed toward the home team, which is what it actually
added up rather than a story told afterwards. Turning that into a sentence is a
translation, and every translation here turns on a sign.

A wrong sign is invisible in this kind of copy. "The betting line agrees" reads
exactly as well as "the betting line disagrees" -- grammatical, plausible, and
on all sixteen cards. The first version of whyMarketSentence() had the spread
convention inverted and said "agrees" on a game where the football-only model
had the away side at 80.5% and the line had the home side by 10.5. The suite was
green, the diff looked fine, and it was caught only by loading the page and
reading it against the card's own "Vegas line" display.

Worth recording: the convention was already written down, in
tests/team_dive_harness.js -- "spread_line is the home line (positive when home
is favoured)". It was got wrong anyway, by assuming rather than reading. The
card negates it for display, football-style, which is what makes it easy.

These run the shipped functions via tests/why_words_harness.js rather than
matching strings in the template. Matching strings proves the sentence exists;
only executing it proves the sentence is true.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
HARNESS = Path(__file__).parent / 'why_words_harness.js'
NODE = shutil.which('node')


@pytest.fixture(scope='module')
def out():
    if not NODE:
        pytest.skip('node not available')
    r = subprocess.run([NODE, str(HARNESS)], capture_output=True, text=True,
                       cwd=str(REPO_ROOT))
    assert r.returncode == 0, f'harness failed:\n{r.stderr}'
    data = json.loads(r.stdout)
    assert 'fatal' not in data, data.get('fatal')
    return data


def test_the_favourite_is_named(out):
    assert out['home_dominant'].startswith('KC are ahead'), out['home_dominant']


def test_the_same_numbers_mirrored_name_the_other_team(out):
    """The flip. Identical magnitudes with every sign reversed must produce the
    away team's sentence, not the home team's. A missing flip passes every
    string check and names the wrong side of every game."""
    assert out['away_dominant'].startswith('DEN are ahead'), out['away_dominant']
    assert out['home_dominant'].split(' are ahead')[1] == \
        out['away_dominant'].split(' are ahead')[1], (
        'mirrored inputs produced different reasoning, so the flip is doing '
        'more than changing which team is named')


def test_one_dominant_factor_is_called_almost_entirely(out):
    assert 'almost entirely on the quarterback matchup' in out['home_dominant']


def test_two_comparable_factors_promote_neither(out):
    """A near-tie must not be reported as one cause. 'Almost entirely' is a
    claim about the model's own arithmetic and has to be earned."""
    assert 'almost entirely' not in out['shared'], out['shared']
    assert 'mainly on' in out['shared'] and 'adding to it' in out['shared']


def test_a_factor_favouring_the_underdog_is_stated(out):
    """The honest half. When something real points at the other team, saying so
    is the difference between an explanation and a sales pitch."""
    assert 'favours DEN' in out['counterweight'], out['counterweight']


def test_nothing_meaningful_says_so(out):
    assert out['flat'].startswith('Nothing much separates these two')
    assert 'almost entirely' not in out['flat']


def test_no_contributions_produces_no_sentence(out):
    """Silence, not an invented reason, when the data is absent -- the same
    rule the rest of this dashboard now follows."""
    assert out['no_why'] == ''


# --- the market sentence: one test per sign, because the sign was the bug ---

def test_positive_spread_means_the_home_team_is_favoured(out):
    assert out['market_agree_home'] == \
        'The betting line agrees, making SEA favourites by 3.5.', \
        out['market_agree_home']


def test_negative_spread_means_the_away_team_is_favoured(out):
    assert out['market_agree_away'] == \
        'The betting line agrees, making DEN favourites by 3.0.', \
        out['market_agree_away']


def test_the_real_card_that_was_reported_backwards(out):
    """ARI @ LAC, week 1 2026: model at 19.5% for the home side, line +10.5 for
    the home side. Disagreement, and the line's favourite is LAC. Shipped as
    'agrees, making ARI favourites by 10.5' until the page was looked at."""
    assert out['market_disagree_home_favoured'] == \
        'The betting line disagrees, making LAC favourites by 10.5.', \
        out['market_disagree_home_favoured']


def test_no_line_produces_no_claim_about_the_line(out):
    assert out['market_absent'] == ''


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))
