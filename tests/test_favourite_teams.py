"""Favourite teams (Stage 80 item 53, the 2026-10-13 UI/UX audit's F7).

Before, no page let a visitor follow a team: every day and week listed its
games in one order for everyone. A team can now be starred (the NHL's Teams
page, the NFL's Team Deep-Dive, and the game cards), its games come first on
each day board and on the NFL's week, under a "Your teams" head where the
NFL groups its cards by kickoff, and the list is kept in this browser under
one key every page reads (site:favs), so the home can name tonight's games.
src/core/favs.js holds the functions the NHL and NBA include; the NFL's
app.js carries the same text, held equal here.

Run with: pytest tests/test_favourite_teams.py -v
"""
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CORE = (ROOT / 'src' / 'core' / 'favs.js').read_text(encoding='utf-8')
APP = (ROOT / 'src' / 'dashboard' / 'app.js').read_text(encoding='utf-8')
NHL = (ROOT / 'src' / 'sports' / 'nhl' / 'pages' / 'nhl.js').read_text(encoding='utf-8')
NBA = (ROOT / 'src' / 'sports' / 'nba' / 'pages' / 'nba.js').read_text(encoding='utf-8')
HOME = (ROOT / 'src' / 'site' / 'home' / 'home.js').read_text(encoding='utf-8')
NODE = shutil.which('node')
STORE = ("function store(seed){ const m = Object.assign({}, seed); return {getItem: k => k in m ? m[k] : null,"
         " setItem: (k, v) => { m[k] = String(v); }}; }\n")


def fn(src, name):
    m = re.search(r'function %s\(.*?\n\}\n' % name, src, re.S)
    assert m, f'{name} is not findable -- re-anchor this guard'
    return m.group(0)


def node(code):
    if not NODE:
        pytest.skip('node not available')
    r = subprocess.run([NODE, '-e', code], capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def core_body():
    return CORE[CORE.index('const FAV_KEY'):]


def test_a_star_adds_and_removes_and_a_bad_store_is_empty():
    got = node(STORE + "let localStorage = store({});\n" + core_body()
               + "const a = toggleFav('nhl', 'BOS'), b = toggleFav('nhl', 'TOR'), c = toggleFav('nhl', 'BOS');\n"
               + "const kept = localStorage.getItem('site:favs');\n"
               + "localStorage = store({'site:favs': '{not json'});\n"
               + "console.log(JSON.stringify([a, b, c, kept, favs('nhl'), favLabel(true, 'Boston Bruins'), favLabel(false, 'Boston Bruins')]));")
    assert got == [True, True, False, '{"nhl":["TOR"]}', [], 'Remove Boston Bruins from your teams', 'Add Boston Bruins to your teams']


def test_a_favourite_teams_games_come_first_each_group_in_its_order():
    games = json.dumps([{'home': 'TBL', 'away': 'PHI'}, {'home': 'BOS', 'away': 'OTT'},
                        {'home': 'NYR', 'away': 'MTL'}, {'home': 'TOR', 'away': 'BOS'}])
    got = node(STORE + "const localStorage = store({'site:favs': JSON.stringify({nhl: ['BOS']})});\n" + core_body()
               + f"console.log(JSON.stringify([favFirst('nhl', {games}).map(g => g.home), favFirst('nba', {games}).map(g => g.home)]));")
    assert got == [['BOS', 'TOR', 'TBL', 'NYR'], ['TBL', 'BOS', 'NYR', 'TOR']]


def test_the_star_says_its_state():
    got = node(STORE + "const localStorage = store({'site:favs': JSON.stringify({nfl: ['LA']})});\n" + core_body()
               + "console.log(JSON.stringify([favStar('nfl', 'LA', 'LA Rams'), favStar('nfl', 'SEA', 'Seattle')]));")
    assert 'aria-pressed="true" aria-label="Remove LA Rams from your teams"' in got[0]
    assert 'aria-pressed="false" aria-label="Add Seattle to your teams"' in got[1]
    assert all(s.startswith('<button type="button" class="fav-star" ') for s in got)


def test_the_nfl_carries_the_same_functions():
    start = APP.index('const FAV_KEY')
    assert APP[start:start + len(core_body())] == core_body(), 'app.js and src/core/favs.js have drifted apart'


def test_every_sport_puts_its_favourites_first_and_listens_for_stars():
    assert "const dayGames = favFirst('nhl', byDay[currentDay] || []);" in NHL
    assert "const dayGames = favFirst('nba', byDay[currentDay] || []);" in NBA
    assert "const sorted = favFirst('nfl', [...filtered].sort((a,b)=>{" in APP
    assert 'installFavStars(() => { renderBoard(); renderTeams(); });' in NHL
    assert 'installFavStars(renderBoard);' in NBA
    assert 'installFavStars(() => { renderGames(); renderTeamDive(); });' in APP
    for sport in ('nhl', 'nba'):
        page = (ROOT / 'src' / 'sports' / sport / 'pages' / 'page.html').read_text(encoding='utf-8')
        assert '{% include "accuracy.js" %}\n{% include "favs.js" %}\n' in page
        site = (ROOT / 'src' / 'sports' / sport / 'site.py').read_text(encoding='utf-8')
        assert """.replace('{% include "favs.js" %}', FAVS_JS.read_text(encoding='utf-8'))""" in site


def test_the_teams_pages_carry_a_star():
    assert "${favStar('nhl', t, escapeHtml(teamName(t)))}</div>" in fn(NHL, 'renderTeams')
    assert "diveTeamHtml(team, teamHistory.names[team], favStar('nfl', team, teamHistory.names[team] || team))" in fn(APP, 'renderTeamDive')
    assert '<span class="dive-team-name">${name || team}</span>${star}</div>' in fn(APP, 'diveTeamHtml')


def test_the_nfl_week_heads_its_favourites_and_counts_the_slots_without_them():
    head = fn(APP, 'slotHeadBefore') + fn(APP, 'slotKey')
    games = json.dumps([{'home': 'LA', 'away': 'ARI', 'gameday': '2026-10-18', 'gametime_et': '16:05'},
                        {'home': 'DEN', 'away': 'SEA', 'gameday': '2026-10-15', 'gametime_et': '20:15'},
                        {'home': 'BUF', 'away': 'NE', 'gameday': '2026-10-18', 'gametime_et': '13:00'},
                        {'home': 'MIA', 'away': 'NYJ', 'gameday': '2026-10-18', 'gametime_et': '13:00'}])
    got = node("function escapeHtml(s){ return s; }\n"
               "function kickoffLabel(g){ return g.gameday + ' ' + g.gametime_et; }\nlet currentSort = 'chronological';\n" + head
               + f"const g = {games};\nconst a = g.map((_, i) => slotHeadBefore(g, i, 1));\n"
               + "currentSort = 'confidence';\nconst b = g.map((_, i) => slotHeadBefore(g, i, 1));\n"
               + "console.log(JSON.stringify([a, b]));")
    chrono, other = got
    assert chrono[0] == '<h3 class="slot-head">Your teams<span class="slot-count"> · 1 game</span></h3>'
    assert '2026-10-15 20:15<span class="slot-count"> · 1 game</span>' in chrono[1]
    assert '2026-10-18 13:00<span class="slot-count"> · 2 games</span>' in chrono[2] and chrono[3] == ''
    assert other == [chrono[0], '<h3 class="slot-head">Every other game</h3>', '', '']
    assert "const mine = favs('nfl'), pinned = sorted.filter(g => mine.includes(g.home) || mine.includes(g.away)).length;" in APP
    assert 'slotHeadBefore(sorted, i, pinned)' in APP


def test_each_card_has_a_star_at_the_outer_end_of_its_bar():
    """Mark chose the card's two ends (option B, 2026-10-14): a star beside
    each team at the ends of the bar, on the outside. A button cannot sit in
    an image, so the bar itself, not the row of ends, is the role="img"."""
    nhl, nba, nfl = fn(NHL, 'pickedCard'), fn(NBA, 'pickedCard'), fn(APP, 'cardProbHtml')
    assert "<span class=\"card-end\">${favStar('nhl', g.away, escapeHtml(teamName(g.away)))}${badge(p.pick === g.away" in nhl
    assert "${endTeam(g.home)}${favStar('nhl', g.home, escapeHtml(teamName(g.home)))}</span>" in nhl
    assert "<span class=\"card-end\">${favStar('nba', g.away, escapeHtml((BD.teams[g.away] || {}).name || g.away))}${badge(" in nba
    assert "${endTeam(g.home)}${favStar('nba', g.home, escapeHtml((BD.teams[g.home] || {}).name || g.home))}</span>" in nba
    assert "<span class=\"card-end\">${favStar('nfl', g.away, escapeHtml(teamFullName(g.away)))}${pickBadge(" in nfl
    assert "${barTeam(g.home)}${favStar('nfl', g.home, escapeHtml(teamFullName(g.home)))}</span>" in nfl
    for body in (nhl, nba, nfl):
        assert '<div class="card-viz">' in body and '<div class="card-scale" role="img" aria-label=' in body
        assert 'class="card-viz" role="img"' not in body


def yours(slate, favs, now):
    head = (STORE.split('\n')[0] + "\nconst HOUR = 3600 * 1000;\n"
            + "".join(re.search(r'^function %s\(.*$' % n, HOME, re.M).group(0) + '\n' for n in ('esc', 'dayKey', 'clock', 'weekday', 'when'))
            # The NBA's tip rule reads the starts ESPN marks not set (home.py `unset`, #489).
            + "const HOME = {nba: {unset: []}};\n"
            + re.search(r'^const UNSET_TIPS = .*$', HOME, re.M).group(0) + '\n'
            + re.search(r'^function tipSet\(t\)\{.*\}$', HOME, re.M).group(0) + '\n'
            + "function tipClock(t){ return tipSet(t) ? clock(t) : 'time TBD'; }\n")
    return node_ny(head + fn(HOME, 'yoursText') + fn(HOME, 'yoursHtml')
                   + f"console.log(JSON.stringify(yoursHtml({json.dumps(slate)}, {json.dumps(favs)}, Date.parse('{now}'))));")


def node_ny(code):
    if not NODE:
        pytest.skip('node not available')
    r = subprocess.run([NODE, '-e', code], capture_output=True, encoding='utf-8', env={**os.environ, 'TZ': 'America/New_York'})
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


SLATE = [
    {'s': 'nhl', 't': '2026-10-14T23:30:00Z', 'a': 'MTL', 'h': 'WSH', 'k': 'pick', 'p': 'WSH', 'c': 51, 'e': True},
    {'s': 'nhl', 't': '2026-10-15T00:30:00Z', 'a': 'DAL', 'h': 'COL', 'k': 'pick', 'p': 'COL', 'c': 57, 'e': False},
    {'s': 'nhl', 't': '2026-10-15T23:00:00Z', 'a': 'BUF', 'h': 'TOR', 'k': 'wait', 'l': None},
    {'s': 'nfl', 't': '2026-10-16T00:15:00Z', 'a': 'SEA', 'h': 'DEN', 'k': 'lean', 'p': 'SEA', 'c': 56, 'e': False},
]


def test_the_home_names_your_teams_games_tonight():
    got = yours(SLATE, {'nhl': ['DAL', 'TOR', 'WSH'], 'nfl': ['SEA']}, '2026-10-14T22:00:00Z')
    assert got == ('<b>Your teams tonight:</b> <a href="nhl/">MTL @ WSH 7:30 PM, WSH 51% · even</a>; '
                   '<a href="nhl/">DAL @ COL 8:30 PM, COL 57%</a>'), "tomorrow's games are not tonight's"


def test_nothing_is_named_before_a_team_is_starred_or_on_a_day_without_their_games():
    assert yours(SLATE, {}, '2026-10-14T22:00:00Z') == ''
    assert yours(SLATE, {'nhl': ['BOS']}, '2026-10-14T22:00:00Z') == ''
    assert yours(SLATE, {'nhl': 'COL'}, '2026-10-14T22:00:00Z') == '', 'a damaged list names nothing'
    assert yours(SLATE, {'nhl': ['COL']}, '2026-10-15T05:00:00Z') == '', 'a game long over is not tonight'


def test_the_home_has_a_place_for_it_and_reads_the_shared_list():
    page = (ROOT / 'src' / 'site' / 'home' / 'page.html').read_text(encoding='utf-8')
    assert '<p class="home-since" id="home-since" role="status"></p>\n  <p class="home-yours" id="home-yours" hidden></p>' in page
    assert "favs = JSON.parse(localStorage.getItem('site:favs') || '{}') || {};" in HOME
    assert "const html = yoursHtml(HOME.slate || [], favs, NOW);" in HOME
