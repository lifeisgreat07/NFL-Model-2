"""
Where things live, and the few facts every pipeline module needs the same
answer to.

Stage 32 item 15, from the 2026-09-29 re-audit. Until this file each module
worked these out for itself:
- the repository root and its data folders, five times;
- the week in a file name (`2026_week3`), four ways: a split in
  generate_dashboard and weekend_refresh, a regex in check_drift, and
  regexes over git paths in weekly_summary;
- the current season, twice in Python (canary, weekend_refresh) and once in
  the weekly workflow's bash;
- the 32 teams, as TEAM_NAMES in weekly_update and NFL_TEAMS in
  data_quality.

Each now has one definition here, with one deliberate exception:
weekly_summary's regexes stay. They match paths in `git status` output
(`predictions/preview/2026_week4.json`), a different input from a file
stem, and they also tell a lock from a preview from a grade by folder.
Two inline splits of a stem were missed in #241 and moved here in Stage 35
(weekend_refresh.weeks_to_refresh, weekly_update._week_numbers);
tests/test_paths.py's COPIES now finds an inline split as well as a def.
The modules keep their own names for them
(weekly_update.PRED_DIR, data_quality.NFL_TEAMS, ...), bound to these, so
nothing that reads or patches those names changes. tv_channels.TEAMS stays
where it is: it maps nfl.com's full names to abbreviations, a translation
table for one source rather than a list of teams.
"""
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).parents[2]
DATA_DIR = ROOT / 'data'
PRED_DIR = ROOT / 'predictions'
RESULTS_DIR = ROOT / 'results'
# One small file per week that kicked off with nothing locked; see
# weekly_update.record_skipped_week.
SKIPPED_DIR = PRED_DIR / 'skipped'
# What a holding run would pick; see weekly_update.save_preview.
PREVIEW_DIR = PRED_DIR / 'preview'
STATUS_DIR = DATA_DIR / 'game_status'
# Games the league cancelled, each with a source; see
# weekend_refresh.load_cancelled (Stage 39, Mark's call 2026-10-05).
CANCELLED_FILE = DATA_DIR / 'cancelled_games.json'


def parse_week(stem):
    """'2026_week3' -> (2026, 3). Returns None if it doesn't match.

    Exactly the rule generate_dashboard.parse_week_stem has always used, so
    no file is read differently: a stem with anything after the week number
    ('2026_week3_graded', '2026_week5_lines') is None. Strip a known suffix
    first."""
    try:
        season_str, week_str = stem.split('_week')
        return int(season_str), int(week_str)
    except ValueError:
        return None


def current_season(now=None):
    """The NFL season a date belongs to. January and February still belong
    to the season that kicked off the year before (the playoffs and the
    Super Bowl)."""
    now = now or datetime.now(UTC)
    return now.year - 1 if now.month <= 2 else now.year


#: The 32 franchises under the abbreviations nflverse uses for current
#: seasons, with the name the dashboard shows. Older seasons use OAK, SD and
#: STL; nothing here reads those.
TEAM_NAMES = {
    'ARI': 'Arizona Cardinals', 'ATL': 'Atlanta Falcons', 'BAL': 'Baltimore Ravens',
    'BUF': 'Buffalo Bills', 'CAR': 'Carolina Panthers', 'CHI': 'Chicago Bears',
    'CIN': 'Cincinnati Bengals', 'CLE': 'Cleveland Browns', 'DAL': 'Dallas Cowboys',
    'DEN': 'Denver Broncos', 'DET': 'Detroit Lions', 'GB': 'Green Bay Packers',
    'HOU': 'Houston Texans', 'IND': 'Indianapolis Colts', 'JAX': 'Jacksonville Jaguars',
    'KC': 'Kansas City Chiefs', 'LA': 'LA Rams', 'LAC': 'LA Chargers',
    'LV': 'Las Vegas Raiders', 'MIA': 'Miami Dolphins', 'MIN': 'Minnesota Vikings',
    'NE': 'New England Patriots', 'NO': 'New Orleans Saints', 'NYG': 'NY Giants',
    'NYJ': 'NY Jets', 'PHI': 'Philadelphia Eagles', 'PIT': 'Pittsburgh Steelers',
    'SEA': 'Seattle Seahawks', 'SF': 'San Francisco 49ers', 'TB': 'Tampa Bay Buccaneers',
    'TEN': 'Tennessee Titans', 'WAS': 'Washington Commanders',
}
NFL_TEAMS = frozenset(TEAM_NAMES)


if __name__ == '__main__':
    # The weekly workflow asks for the season here rather than repeating the
    # rule in bash: `python -m src.pipeline.paths --current-season`.
    if sys.argv[1:] == ['--current-season']:
        print(current_season())
    else:
        sys.exit('usage: python -m src.pipeline.paths --current-season')
