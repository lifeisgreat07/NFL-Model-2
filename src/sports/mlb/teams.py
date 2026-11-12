"""MLB's clubs as the Stats API names them in 2026 (Stage 98 item 4).

Every table keys on the Stats API's club id, which is stable through renames and moves (docs/mlb-data.md section
5): 114 was the Cleveland Indians and is the Guardians, 133 was the Oakland Athletics and is the Athletics. The
schedule (`schedule.py`) writes the id as text in `home` and `away`; these names are only for showing.
"""
from __future__ import annotations

#: Stats API club id (as text, as the schedule writes it) -> (abbreviation, name), read from
#: `teams?sportId=1&season=2026` on 2026-11-12.
NAMES: dict[str, tuple[str, str]] = {
    '108': ('LAA', 'Los Angeles Angels'), '109': ('AZ', 'Arizona Diamondbacks'), '110': ('BAL', 'Baltimore Orioles'),
    '111': ('BOS', 'Boston Red Sox'), '112': ('CHC', 'Chicago Cubs'), '113': ('CIN', 'Cincinnati Reds'),
    '114': ('CLE', 'Cleveland Guardians'), '115': ('COL', 'Colorado Rockies'), '116': ('DET', 'Detroit Tigers'),
    '117': ('HOU', 'Houston Astros'), '118': ('KC', 'Kansas City Royals'), '119': ('LAD', 'Los Angeles Dodgers'),
    '120': ('WSH', 'Washington Nationals'), '121': ('NYM', 'New York Mets'), '133': ('ATH', 'Athletics'),
    '134': ('PIT', 'Pittsburgh Pirates'), '135': ('SD', 'San Diego Padres'), '136': ('SEA', 'Seattle Mariners'),
    '137': ('SF', 'San Francisco Giants'), '138': ('STL', 'St. Louis Cardinals'), '139': ('TB', 'Tampa Bay Rays'),
    '140': ('TEX', 'Texas Rangers'), '141': ('TOR', 'Toronto Blue Jays'), '142': ('MIN', 'Minnesota Twins'),
    '143': ('PHI', 'Philadelphia Phillies'), '144': ('ATL', 'Atlanta Braves'), '145': ('CWS', 'Chicago White Sox'),
    '146': ('MIA', 'Miami Marlins'), '147': ('NYY', 'New York Yankees'), '158': ('MIL', 'Milwaukee Brewers'),
}


def abbr(club: str) -> str:
    return NAMES[club][0]
