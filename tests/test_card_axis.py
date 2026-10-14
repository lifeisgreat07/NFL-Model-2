"""
Stage 75 item 1 (the 2026-10-13 UI/UX audit): a card's markers sit on its
split bar's own axis, in all three sports' cards.

The bar draws the away team's segment first, `100 - lead` wide, so a home
share v belongs at `100 - v` from the left; the markers were placed at
`v`, and the Model B marker missed the split by 23.7 px on SEA at DEN.
tests/browser/check_card_axis.py measures that on the NFL's and NHL's
built pages. The NBA has no card to measure until opening night, so this
holds the same rule in the source of all three: the marker is placed at
`100 - vals[k]` and names its series, and the bar still draws away first.

Run with: pytest tests/test_card_axis.py -v
"""
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
CARDS = {
    'nfl': REPO / 'src' / 'dashboard' / 'app.js',
    'nhl': REPO / 'src' / 'sports' / 'nhl' / 'pages' / 'nhl.js',
    'nba': REPO / 'src' / 'sports' / 'nba' / 'pages' / 'nba.js',
}
MARKER = '<svg class="card-mk" data-series="${k}" style="left:${100 - vals[k]}%;'
AWAY_FIRST = {
    'nfl': '<div class="tele-bar-seg" style="width:${100-g.mktB_home}%; background:${awayC};"></div>',
    'nhl': '<div class="tele-bar-seg" style="width:${100 - lead}%; background:${awayC};"></div>',
    'nba': '<div class="tele-bar-seg" style="width:${100 - lead}%; background:${awayC};"></div>',
}


@pytest.mark.parametrize('sport', sorted(CARDS))
def test_every_card_marker_sits_on_the_bars_axis(sport):
    src = CARDS[sport].read_text(encoding='utf-8')
    assert src.count('class="card-mk"') == 1, sport
    assert src.count(MARKER) == 1, f"{sport}: the card marker is not placed at 100 - its value"


@pytest.mark.parametrize('sport', sorted(CARDS))
def test_the_bar_still_draws_the_away_team_first(sport):
    """The axis rule above assumes it; flip the bar and the markers must flip too."""
    src = CARDS[sport].read_text(encoding='utf-8')
    away = src.index(AWAY_FIRST[sport])
    assert src.index('background:${homeC};', away) > away, sport


def test_the_browser_check_runs_on_the_nfl_and_nhl_pages():
    wf = (REPO / '.github' / 'workflows' / 'browser-checks.yml').read_text(encoding='utf-8')
    assert 'python tests/browser/check_card_axis.py --self-test' in wf
    assert 'python tests/browser/check_card_axis.py index.html "$RUNNER_TEMP/states/nhl.html"' in wf
