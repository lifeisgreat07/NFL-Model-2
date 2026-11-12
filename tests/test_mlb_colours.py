"""MLB's club colours: one per club, visible on the dark theme, and the separation figures their docstring
quotes, recomputed (Stage 98 item 4). The colour arithmetic is `src.core.colour`, which tests/test_nhl_colours.py
pins to the NFL's own script.

Run with: pytest tests/test_mlb_colours.py -v
"""
import re

from src.sports.mlb import colours
from src.sports.mlb.teams import NAMES, abbr


def test_thirty_clubs_keyed_on_the_stats_api_id():
    assert len(NAMES) == 30 and all(k.isdigit() for k in NAMES)
    assert abbr('133') == 'ATH' and abbr('114') == 'CLE'
    assert len({a for a, _ in NAMES.values()}) == 30


def test_every_club_has_exactly_one_colour_in_hex():
    assert set(colours.TEAM_COLOUR) == set(NAMES)
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
    assert len(scores) == 435
    assert sum(s < 15 for s in scores.values()) == colours.PAIRS_UNDER_15
    assert sum(s < 5 for s in scores.values()) == colours.PAIRS_UNDER_5
    assert f'{colours.PAIRS_UNDER_15} under 15 and {colours.PAIRS_UNDER_5} under 5' in colours.__doc__


def test_logos_come_from_the_leagues_own_files_for_both_themes():
    assert colours.LOGO['light'].format(club='147') == 'https://www.mlbstatic.com/team-logos/147.svg'
    assert colours.LOGO['dark'].format(club='147') == 'https://www.mlbstatic.com/team-logos/team-cap-on-dark/147.svg'
