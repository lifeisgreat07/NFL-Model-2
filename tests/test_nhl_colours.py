"""The NHL's team colours: one per club, visible on the dark theme, and the
separation figures their docstring quotes, recomputed.

Stage 55 item 4. The colour arithmetic is `src.core.colour`, the NFL's
method moved into the core; the first test pins it to the NFL's own script
so the two can never drift apart.

Run with: pytest tests/test_nhl_colours.py -v
"""
import re
from itertools import permutations

import pytest

from src.core import colour
from src.research import verify_matchup_cvd as nfl_method
from src.sports.nhl import colours
from src.sports.nhl.teams import NAMES


def test_the_core_method_is_the_one_the_nfl_palette_was_measured_with():
    tc = nfl_method.team_colors()
    for a, b in permutations(sorted(tc), 2):
        ra, rb = nfl_method.matchup_colors(tc[a], tc[b])
        nfl = min(nfl_method.ciede2000(nfl_method.rgb_to_lab(nfl_method.simulate(ra, k)),
                                       nfl_method.rgb_to_lab(nfl_method.simulate(rb, k)))
                  for k in nfl_method.MACHADO)
        assert colour.worst_cvd_de00(ra, rb) == pytest.approx(nfl, abs=1e-9)


def test_wcag_contrast_has_its_known_end_points():
    assert colour.contrast((255, 255, 255), (0, 0, 0)) == pytest.approx(21.0)
    assert colour.contrast((119, 119, 119), (255, 255, 255)) == pytest.approx(4.48, abs=0.01)
    assert colour.contrast((255, 0, 0), (255, 255, 255)) == pytest.approx(4.0, abs=0.01)
    with pytest.raises(ValueError):
        colour.hex_to_rgb('#12345')


def test_every_club_has_exactly_one_colour_in_hex():
    assert set(colours.TEAM_COLOUR) == set(NAMES)
    assert all(re.fullmatch(r'#[0-9A-F]{6}', v) for v in colours.TEAM_COLOUR.values())


def test_every_colour_stands_out_on_the_dark_theme():
    low = {k: round(colours.contrast_on_dark(k), 2) for k in colours.TEAM_COLOUR
           if colours.contrast_on_dark(k) < colours.MIN_CONTRAST}
    assert not low, f'under 3:1 on the dark card surface: {low}'


def test_the_quoted_separation_figures_are_what_the_palette_measures():
    scores = colours.pair_scores()
    assert len(scores) == 496
    assert sum(s < 15 for s in scores.values()) == colours.PAIRS_UNDER_15
    assert sum(s < 5 for s in scores.values()) == colours.PAIRS_UNDER_5
    doc = colours.__doc__
    assert f'{colours.PAIRS_UNDER_15} of the 496 pairs' in doc and f'and {colours.PAIRS_UNDER_5} under 5' in doc


def test_logos_come_from_the_leagues_own_files_for_both_themes():
    assert colours.LOGO.format(abbr='TOR', theme='dark') == 'https://assets.nhle.com/logos/nhl/svg/TOR_dark.svg'
