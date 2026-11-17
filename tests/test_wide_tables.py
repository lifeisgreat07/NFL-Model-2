"""Wide tables on a phone (audit 9 D11).

At a phone's width the NFL's Power Ratings (about 830 px) put Playoff Odds last of eight columns, off the
screen, and the NBA's standings (about 600 px, every club's full name) put the playoff chances off it too.
Playoff Odds now come straight after the team, and the standings name each club by its code under 640 px
(the full name stays its title). The pinned first column is tests/test_table_system.py's.

Run with: pytest tests/test_wide_tables.py -v
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BODY = (ROOT / 'src' / 'dashboard' / 'body.html').read_text(encoding='utf-8')
RATINGS = (ROOT / 'src' / 'dashboard' / 'app_ratings.js').read_text(encoding='utf-8')
NBA = (ROOT / 'src' / 'sports' / 'nba' / 'pages' / 'nba.js').read_text(encoding='utf-8')
NBA_CSS = (ROOT / 'src' / 'sports' / 'nba' / 'pages' / 'nba.css').read_text(encoding='utf-8')


def test_playoff_odds_come_straight_after_the_team_in_the_header_and_in_every_row():
    table = BODY[BODY.index('<table id="ratings-table">'):BODY.index('</thead>', BODY.index('<table id="ratings-table">'))]
    keys = re.findall(r'<th scope="col"(?: data-key="(\w+)")?', table)
    assert keys == ['rank', 'team', 'playoff', 'net', '', 'off', 'def', 'sos'], keys
    row = RATINGS[RATINGS.index("body.innerHTML = visible.map((t)=>{"):]
    row = row[:row.index('</tr>`;')]
    cells = [row.index(s) for s in ('<td class="rank">', '<div class="team-cell">', 't.playoff.toFixed(1)',
                                    '<div class="net-cell-inner">', 'trendSvg(seasonTrend', 'fmtRating(t.off)',
                                    'fmtRating(t.def)', 'fmtRating(t.sos)')]
    assert cells == sorted(cells), 'a row\'s cells are not in the header\'s order'


def test_the_nba_standings_name_a_club_by_its_code_on_a_phone():
    assert ('<tr><th scope="row"><span class="club-full">${escapeHtml(clubName(t.team))}</span>'
            '<abbr class="club-code" title="${escapeHtml(clubName(t.team))}">${escapeHtml(t.team)}</abbr></th>') in NBA
    assert '[data-sport="nba"] .club-code{display:none; text-decoration:none;}' in NBA_CSS
    assert '@media (max-width:639px){ [data-sport="nba"] .club-full{display:none;} [data-sport="nba"] .club-code{display:inline;} }' in NBA_CSS
