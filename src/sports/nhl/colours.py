"""The NHL's team colours and logos (Stage 55 item 4), measured like the NFL's.

Each club's colour is its primary, or its brightest official colour where the
primary is near-black or navy and would vanish on the dark theme. A few blues
and Colorado's burgundy are lightened until they reach 3:1 against the dark
theme's card surface (`#121519`). `tests/test_nhl_colours.py` holds that.

The NHL is a league of reds, blues and golds, so many pairs of clubs look
alike. Measured with `src.core.colour` (CIEDE2000, Machado 2009 at severity
1.0, the worse of protanopia and deuteranopia), as the NFL's palette was:

- as drawn on a game's bar (after the board's push, worst over both
  orderings), 84 of the 496 pairs of clubs sit under dE00 15, and 4 under 5.
  The NFL's palette, measured the same way on 2026-09-21: 60 and 9;
- the colours as listed, before any push: 149 under 15 and 38 under 5.

Identical colours (Boston and Nashville's gold, Carolina and New Jersey's
red) are the clubs' own. The board's per-matchup push (`matchupColors` in
`src/dashboard/app.js`) and the logos and abbreviations beside every bar
carry identity, as on the NFL board. Whether the NHL keeps team-colour bars
is Mark's call at Stage 57, shown rendered.

Logos are the league's own files: `LOGO.format(abbr=..., theme='light'|'dark')`.
"""
from __future__ import annotations

from itertools import combinations, permutations

from src.core import colour

TEAM_COLOUR: dict[str, str] = {
    'ANA': '#F47A38', 'BOS': '#FFB81C', 'BUF': '#2E62C9', 'CAR': '#CE1126', 'CBJ': '#5B7FB8', 'CGY': '#F1BE48',
    'CHI': '#CF0A2C', 'COL': '#B83A66', 'DAL': '#00A06B', 'DET': '#E0283E', 'EDM': '#FF4C00', 'FLA': '#B9975B',
    'LAK': '#A2AAAD', 'MIN': '#2E7D4F', 'MTL': '#C8273A', 'NJD': '#CE1126', 'NSH': '#FFB81C', 'NYI': '#F47D30',
    'NYR': '#2F6BDB', 'OTT': '#C2912C', 'PHI': '#F74902', 'PIT': '#FCB514', 'SEA': '#99D9D9', 'SJS': '#00A3AD',
    'STL': '#3B6CD0', 'TBL': '#3A6CC4', 'TOR': '#4A7FD0', 'UTA': '#6CACE4', 'VAN': '#00843D', 'VGK': '#B4975A',
    'WPG': '#4A79C4', 'WSH': '#C8102E',
}

LOGO = 'https://assets.nhle.com/logos/nhl/svg/{abbr}_{theme}.svg'

#: The dark theme's card surface, which every team colour must stand out on.
DARK_SURFACE = '#121519'
MIN_CONTRAST = 3.0

#: The measured figures quoted above; tests/test_nhl_colours.py recomputes them.
DRAWN_UNDER_15 = 84
DRAWN_UNDER_5 = 4
PAIRS_UNDER_15 = 149
PAIRS_UNDER_5 = 38


def pair_scores() -> dict[tuple[str, str], float]:
    """Worst colour-vision dE00 for every unordered pair of clubs."""
    return {(a, b): colour.worst_cvd_de00(colour.hex_to_rgb(TEAM_COLOUR[a]), colour.hex_to_rgb(TEAM_COLOUR[b]))
            for a, b in combinations(sorted(TEAM_COLOUR), 2)}


def drawn_scores() -> dict[tuple[str, str], float]:
    """Per pair of clubs, the worst colour-vision dE00 as a bar draws them,
    over both orderings: the NFL's "unit C" (src/research/verify_matchup_cvd.py)."""
    best: dict[tuple[str, str], float] = {}
    for a, h in permutations(sorted(TEAM_COLOUR), 2):
        ra, rh = colour.matchup_push(TEAM_COLOUR[a], TEAM_COLOUR[h])
        key = (min(a, h), max(a, h))
        best[key] = min(best.get(key, float('inf')), colour.worst_cvd_de00(ra, rh))
    return best


def contrast_on_dark(abbr: str) -> float:
    return colour.contrast(colour.hex_to_rgb(TEAM_COLOUR[abbr]), colour.hex_to_rgb(DARK_SURFACE))
