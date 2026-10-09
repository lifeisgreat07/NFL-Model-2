"""The NBA's team colours: one per club, visible on the dark theme, and the
separation figures their docstring quotes, recomputed.

Run with: pytest tests/test_nba_colours.py -v
"""
import re

from src.sports.nba import colours
from src.sports.nba.teams import NAMES


def test_every_club_has_exactly_one_colour_in_hex():
    assert set(colours.TEAM_COLOUR) == set(NAMES)
    assert len(NAMES) == 30
    assert all(re.fullmatch(r'#[0-9A-F]{6}', v) for v in colours.TEAM_COLOUR.values())


def test_every_colour_stands_out_on_the_dark_theme():
    low = {k: round(colours.contrast_on_dark(k), 2) for k in colours.TEAM_COLOUR
           if colours.contrast_on_dark(k) < colours.MIN_CONTRAST}
    assert not low, f'under 3:1 on the dark card surface: {low}'


def test_the_drawn_figures_match_the_docstring():
    drawn = colours.drawn_scores()
    assert len(drawn) == 435
    assert sum(s < 15 for s in drawn.values()) == colours.DRAWN_UNDER_15
    assert sum(s < 5 for s in drawn.values()) == colours.DRAWN_UNDER_5
    assert f'{colours.DRAWN_UNDER_15} of the 435 pairs' in colours.__doc__
    assert f'and {colours.DRAWN_UNDER_5} under 5' in colours.__doc__


def test_the_quoted_separation_figures_are_what_the_palette_measures():
    scores = colours.pair_scores()
    assert sum(s < 15 for s in scores.values()) == colours.PAIRS_UNDER_15
    assert sum(s < 5 for s in scores.values()) == colours.PAIRS_UNDER_5
    assert f'{colours.PAIRS_UNDER_15} under 15 and {colours.PAIRS_UNDER_5} under 5' in colours.__doc__


def test_the_teams_are_espns_codes_the_schedule_uses():
    """The six that differ from the league's own codes are ESPN's."""
    assert {'GS', 'NO', 'NY', 'SA', 'UTAH', 'WSH'} <= set(NAMES)
    assert not {'GSW', 'NOP', 'NYK', 'SAS', 'UTA', 'WAS'} & set(NAMES)


def test_logos_are_espns_files_for_both_themes():
    assert colours.logo('GS', 'light') == 'https://a.espncdn.com/i/teamlogos/nba/500/gs.png'
    assert colours.logo('UTAH', 'dark') == 'https://a.espncdn.com/i/teamlogos/nba/500-dark/utah.png'
