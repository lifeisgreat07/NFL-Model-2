"""The NHL's 32 clubs as the sources name them.

The league's feed names a club by its abbreviation; Daily Faceoff names it
in full. `abbr_for` turns either spelling into the abbreviation, ignoring
case, accents and punctuation ("Montréal" and "Montreal", "St. Louis" and
"St Louis"), and answers None for anything else, so a club it does not know
is reported rather than guessed.

Older names (`FORMER`) are the same franchise in the league's own records
(decision record 0006's team identity; `docs/nhl-data.md` section 5).
Whether Arizona's strength carries to Utah is a modelling question for the
Stage 56 registration, so it is not here.
"""
from __future__ import annotations

import re
import unicodedata

NAMES: dict[str, str] = {
    'ANA': 'Anaheim Ducks', 'BOS': 'Boston Bruins', 'BUF': 'Buffalo Sabres',
    'CAR': 'Carolina Hurricanes', 'CBJ': 'Columbus Blue Jackets', 'CGY': 'Calgary Flames',
    'CHI': 'Chicago Blackhawks', 'COL': 'Colorado Avalanche', 'DAL': 'Dallas Stars',
    'DET': 'Detroit Red Wings', 'EDM': 'Edmonton Oilers', 'FLA': 'Florida Panthers',
    'LAK': 'Los Angeles Kings', 'MIN': 'Minnesota Wild', 'MTL': 'Montréal Canadiens',
    'NJD': 'New Jersey Devils', 'NSH': 'Nashville Predators', 'NYI': 'New York Islanders',
    'NYR': 'New York Rangers', 'OTT': 'Ottawa Senators', 'PHI': 'Philadelphia Flyers',
    'PIT': 'Pittsburgh Penguins', 'SEA': 'Seattle Kraken', 'SJS': 'San Jose Sharks',
    'STL': 'St. Louis Blues', 'TBL': 'Tampa Bay Lightning', 'TOR': 'Toronto Maple Leafs',
    'UTA': 'Utah Mammoth', 'VAN': 'Vancouver Canucks', 'VGK': 'Vegas Golden Knights',
    'WPG': 'Winnipeg Jets', 'WSH': 'Washington Capitals',
}

#: Former abbreviation -> the club it became, same franchise.
FORMER: dict[str, str] = {'ATL': 'WPG', 'PHX': 'ARI'}


def _key(name: str) -> str:
    plain = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z]', '', plain.lower())


_BY_KEY = {_key(full): abbr for abbr, full in NAMES.items()}


def abbr_for(name: str) -> str | None:
    """The club's abbreviation from its abbreviation or full name, or None."""
    if name in NAMES:
        return name
    return _BY_KEY.get(_key(name))
