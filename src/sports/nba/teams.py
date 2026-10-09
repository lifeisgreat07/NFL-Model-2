"""The NBA's 30 clubs by ESPN's abbreviation (Stage 65's board).

ESPN's codes are the schedule's, the injury report's and the history's
(`experiments/nba/stage61/registry.json`, team_identity): stable from
2015-16 on, and six differ from the league's three-letter codes (GS, NO,
NY, SA, UTAH, WSH).
"""
from __future__ import annotations

NAMES: dict[str, str] = {
    'ATL': 'Atlanta Hawks', 'BOS': 'Boston Celtics', 'BKN': 'Brooklyn Nets', 'CHA': 'Charlotte Hornets',
    'CHI': 'Chicago Bulls', 'CLE': 'Cleveland Cavaliers', 'DAL': 'Dallas Mavericks', 'DEN': 'Denver Nuggets',
    'DET': 'Detroit Pistons', 'GS': 'Golden State Warriors', 'HOU': 'Houston Rockets', 'IND': 'Indiana Pacers',
    'LAC': 'LA Clippers', 'LAL': 'Los Angeles Lakers', 'MEM': 'Memphis Grizzlies', 'MIA': 'Miami Heat',
    'MIL': 'Milwaukee Bucks', 'MIN': 'Minnesota Timberwolves', 'NO': 'New Orleans Pelicans',
    'NY': 'New York Knicks', 'OKC': 'Oklahoma City Thunder', 'ORL': 'Orlando Magic',
    'PHI': 'Philadelphia 76ers', 'PHX': 'Phoenix Suns', 'POR': 'Portland Trail Blazers',
    'SAC': 'Sacramento Kings', 'SA': 'San Antonio Spurs', 'TOR': 'Toronto Raptors', 'UTAH': 'Utah Jazz',
    'WSH': 'Washington Wizards',
}
