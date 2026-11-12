"""MLB's club colours and logos (Stage 98 item 4), measured like the other three sports'.

Each club's colour is one of its official colours, keyed on the Stats API's club id (`teams.NAMES`). Where it would
not reach 3:1 against the dark theme's card surface (`#121519`), its lightness is raised a step at a time, hue and
saturation kept, until it does: twelve clubs, the navies and blues among them (the Yankees' #003087 to #0054ED, the
Cubs' #0E3386 to #1856E2) and the deeper reds (the Angels, the Diamondbacks, the Nationals). Where a club's primary
is near-black or navy, its brightest official colour starts instead (Detroit's orange, Houston's, the Mets', the
Athletics' gold, the White Sox's silver, Tampa Bay's light blue). `tests/test_mlb_colours.py` holds the 3:1.

MLB is a league of reds and blues, so many pairs of clubs look alike. Measured with `src.core.colour` (CIEDE2000,
Machado 2009 at severity 1.0, the worse of protanopia and deuteranopia), as the NFL's and the NHL's palettes were:

- as drawn on a game's bar (after the board's push, worst over both orderings), 45 of the 435 pairs of clubs sit
  under dE00 15, and 3 under 5. The NHL's, measured the same way: 84 of 496 and 4;
- the colours as listed, before any push: 120 under 15 and 49 under 5.

The board's per-matchup push and the logos and abbreviations beside every bar carry identity, as on the other
boards. Logos are the league's own files: `LOGO['light' | 'dark'].format(club=...)`, the club's logo for the light
theme and its cap logo drawn for a dark ground.
"""
from __future__ import annotations

from itertools import combinations, permutations

from src.core import colour

TEAM_COLOUR: dict[str, str] = {
    '108': '#C90024', '109': '#C21D38', '110': '#DF4601', '111': '#BD3039', '112': '#1856E2', '113': '#CB0120',
    '114': '#E50022', '115': '#5C5CAD', '116': '#FA4616', '117': '#EB6E1F', '118': '#0063BF', '119': '#0066B0',
    '120': '#CA0004', '121': '#FF5910', '133': '#EFB21E', '134': '#FDB827', '135': '#FFC425', '136': '#007070',
    '137': '#FD5A1E', '138': '#C41E3A', '139': '#8FBCE6', '140': '#005AD9', '141': '#1961BB', '142': '#D31145',
    '143': '#E81828', '144': '#CE1141', '145': '#C4CED4', '146': '#00A3E0', '147': '#0054ED', '158': '#FFC52F',
}

LOGO = {'light': 'https://www.mlbstatic.com/team-logos/{club}.svg',
        'dark': 'https://www.mlbstatic.com/team-logos/team-cap-on-dark/{club}.svg'}

#: The dark theme's card surface, which every club colour must stand out on.
DARK_SURFACE = '#121519'
MIN_CONTRAST = 3.0

#: The measured figures quoted above; tests/test_mlb_colours.py recomputes them.
DRAWN_UNDER_15 = 45
DRAWN_UNDER_5 = 3
PAIRS_UNDER_15 = 120
PAIRS_UNDER_5 = 49


def pair_scores() -> dict[tuple[str, str], float]:
    """Worst colour-vision dE00 for every unordered pair of clubs."""
    return {(a, b): colour.worst_cvd_de00(colour.hex_to_rgb(TEAM_COLOUR[a]), colour.hex_to_rgb(TEAM_COLOUR[b]))
            for a, b in combinations(sorted(TEAM_COLOUR), 2)}


def drawn_scores() -> dict[tuple[str, str], float]:
    """Per pair of clubs, the worst colour-vision dE00 as a bar draws them, over both orderings."""
    best: dict[tuple[str, str], float] = {}
    for a, h in permutations(sorted(TEAM_COLOUR), 2):
        ra, rh = colour.matchup_push(TEAM_COLOUR[a], TEAM_COLOUR[h])
        key = (min(a, h), max(a, h))
        best[key] = min(best.get(key, float('inf')), colour.worst_cvd_de00(ra, rh))
    return best


def contrast_on_dark(club: str) -> float:
    return colour.contrast(colour.hex_to_rgb(TEAM_COLOUR[club]), colour.hex_to_rgb(DARK_SURFACE))
