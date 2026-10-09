"""The NBA's team colours and logos (Stage 65's board), measured like the
NFL's and the NHL's.

Each club's colour is its primary, or its brightest official colour where
the primary is near-black or navy and would vanish on the dark theme
(Brooklyn's grey, Cleveland's, Denver's, Golden State's, Indiana's and the
Lakers' gold, Milwaukee's cream, Minnesota's green, New Orleans' gold,
New York's orange, Phoenix's orange, Washington's red). Dallas, Miami,
Sacramento and Utah are lightened toward white until they reach 3:1
against the dark theme's card surface (`#121519`).
`tests/test_nba_colours.py` holds that.

Measured with `src.core.colour` (CIEDE2000, Machado 2009 at severity 1.0,
the worse of protanopia and deuteranopia), as the NFL's palette was:

- as drawn on a game's bar (after the board's push, worst over both
  orderings), 57 of the 435 pairs of clubs sit under dE00 15, and 14 under 5.
  The NFL's palette, measured the same way on 2026-09-21: 60 of 496 and 9;
- the colours as listed, before any push: 121 under 15 and 43 under 5.

Identical colours (Chicago, Houston and Toronto's red; Cleveland and
Indiana's gold) are the clubs' own. As on the NFL and NHL boards, the logos
and abbreviations beside every bar carry identity, and Mark's decision of
2026-09-21 to keep team-colour bars knowingly is the precedent.

Logos are ESPN's files, the same host as the NFL board's
(`LOGO.format(abbr=..., theme='light'|'dark')`; the code is lowercase).
"""
from __future__ import annotations

from itertools import combinations, permutations

from src.core import colour

TEAM_COLOUR: dict[str, str] = {
    'ATL': '#E03A3E', 'BOS': '#007A33', 'BKN': '#A1A1A4', 'CHA': '#00788C', 'CHI': '#CE1141', 'CLE': '#FDBB30',
    'DAL': '#1F689A', 'DEN': '#FEC524', 'DET': '#C8102E', 'GS': '#FFC72C', 'HOU': '#CE1141', 'IND': '#FDBB30',
    'LAC': '#C8102E', 'LAL': '#FDB927', 'MEM': '#5D76A9', 'MIA': '#AE365A', 'MIL': '#EEE1C6', 'MIN': '#78BE20',
    'NO': '#85714D', 'NY': '#F58426', 'OKC': '#007AC1', 'ORL': '#0077C0', 'PHI': '#006BB6', 'PHX': '#E56020',
    'POR': '#E03A3E', 'SAC': '#785398', 'SA': '#C4CED4', 'TOR': '#CE1141', 'UTAH': '#7C45C0', 'WSH': '#E31837',
}

LOGOS = {'dark': 'https://a.espncdn.com/i/teamlogos/nba/500-dark/{code}.png',
         'light': 'https://a.espncdn.com/i/teamlogos/nba/500/{code}.png'}

#: The dark theme's card surface, which every team colour must stand out on.
DARK_SURFACE = '#121519'
MIN_CONTRAST = 3.0

#: The measured figures quoted above; tests/test_nba_colours.py recomputes them.
DRAWN_UNDER_15 = 57
DRAWN_UNDER_5 = 14
PAIRS_UNDER_15 = 121
PAIRS_UNDER_5 = 43


def logo(abbr: str, theme: str) -> str:
    return LOGOS[theme].format(code=abbr.lower())


def pair_scores() -> dict[tuple[str, str], float]:
    """Worst colour-vision dE00 for every unordered pair of clubs."""
    return {(a, b): colour.worst_cvd_de00(colour.hex_to_rgb(TEAM_COLOUR[a]), colour.hex_to_rgb(TEAM_COLOUR[b]))
            for a, b in combinations(sorted(TEAM_COLOUR), 2)}


def drawn_scores() -> dict[tuple[str, str], float]:
    """Per pair of clubs, the worst colour-vision dE00 as a bar draws them,
    over both orderings."""
    best: dict[tuple[str, str], float] = {}
    for a, h in permutations(sorted(TEAM_COLOUR), 2):
        ra, rh = colour.matchup_push(TEAM_COLOUR[a], TEAM_COLOUR[h])
        key = (min(a, h), max(a, h))
        best[key] = min(best.get(key, float('inf')), colour.worst_cvd_de00(ra, rh))
    return best


def contrast_on_dark(abbr: str) -> float:
    return colour.contrast(colour.hex_to_rgb(TEAM_COLOUR[abbr]), colour.hex_to_rgb(DARK_SURFACE))
