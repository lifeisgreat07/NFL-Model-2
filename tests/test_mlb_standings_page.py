"""MLB's Standings page (Stage 100 item 2, layout B, Mark 2026-11-23): the NHL's division tables plus each
league's wild card race, read from the file src/sports/mlb/standings.py's to_json writes.

The page reads `results/mlb/standings_<season>.json`, which MLB's daily run will write (Stage 101); the build
turns each club's Stats API id into its code. The race is the table as it stands: the clubs not leading a
division, by record, level clubs by projected wins, with games back of the third.

Run with: pytest tests/test_mlb_standings_page.py -v
"""
import json
import re
import subprocess
from pathlib import Path

import pandas as pd

from src.sports.mlb import site, standings
from tests.js_source import function_source
from tests.optional import require_tool

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / 'src' / 'sports' / 'mlb' / 'pages' / 'mlb.js').read_text(encoding='utf-8').replace('\r\n', '\n')
BODY = (ROOT / 'src' / 'sports' / 'mlb' / 'pages' / 'body.html').read_text(encoding='utf-8')
ESCAPE = (ROOT / 'src' / 'core' / 'escape.js').read_text(encoding='utf-8').replace('\r\n', '\n') + '\n'


def season_file():
    """A finished round robin through standings.to_json: every pair plays once at home and once away, the club whose
    id sorts first winning at home."""
    rows = [{'game_id': f'{h}-{a}', 'home': h, 'away': a, 'game_type': 'regular', 'status': 'final',
             'home_score': 5.0 if h < a else 3.0, 'away_score': 3.0 if h < a else 5.0}
            for clubs in standings.LEAGUE_CLUBS.values() for h in clubs for a in clubs if h != a]
    sched = pd.DataFrame(rows)
    return standings.to_json(standings.simulate(sched, {}, n_sim=5), '2026-08-15', 5, standings.games_listed(sched))


def board_with(tmp_path, monkeypatch, doc):
    res = tmp_path / 'results'
    res.mkdir()
    if doc is not None:
        (res / 'standings_2026.json').write_text(json.dumps(doc), encoding='utf-8')
    monkeypatch.setattr(site, 'PATHS', type('P', (), {'results': res})())
    return site.board(2026)


def test_before_the_first_simulation_the_page_says_so(tmp_path, monkeypatch):
    assert board_with(tmp_path, monkeypatch, None)['standings'] is None
    assert "'Not simulated yet'" in JS


def test_the_build_names_each_club_by_its_code(tmp_path, monkeypatch):
    s = board_with(tmp_path, monkeypatch, season_file())['standings']
    assert s['as_of'] == '2026-08-15' and len(s['teams']) == 30
    assert {t['team'] for t in s['teams']} == {code for code, _ in site.teams.NAMES.values()}
    assert {t['league'] for t in s['teams']} == {'AL', 'NL'} and len({t['division'] for t in s['teams']}) == 6


def test_the_page_says_fixed_chances_make_the_odds_too_sure():
    """As the NHL's and NBA's standings say: chances held fixed all season make 0% and 100% mean less than they look."""
    fn = function_source(JS, 'renderStandings', at_line_start=True)
    assert 'makes these odds surer than' in fn and 'no simulated season went' in fn


def test_the_page_has_the_standings_page_and_both_buttons():
    assert BODY.count('data-page="standings"') == 2 and 'id="page-standings"' in BODY
    assert 'id="standings-body"' in BODY


def run_node(names, body):
    node = require_tool('node')
    src = ESCAPE + ''.join(function_source(JS, n, at_line_start=True) for n in names) + body
    r = subprocess.run([node, '-e', src], capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


RACE = """
const t = (team, division, w, l, proj) => ({team, league: 'AL', division, wins_now: w, losses_now: l,
  projected_wins: proj, wildcard_pct: 0.5});
const teams = [
  t('NYY', 'AL East', 72, 50, 95), t('BAL', 'AL East', 71, 50, 93), t('BOS', 'AL East', 63, 57, 84),
  t('CLE', 'AL Central', 72, 49, 93), t('MIN', 'AL Central', 67, 53, 90), t('KC', 'AL Central', 66, 55, 86),
  t('HOU', 'AL West', 65, 55, 88), t('SEA', 'AL West', 63, 58, 85), t('TEX', 'AL West', 60, 61, 80),
  {...t('ATL', 'NL East', 80, 40, 99), league: 'NL'}];
console.log(JSON.stringify(wildCardRace(teams, 'AL').map(x => [x.team, x.place, x.back])));
"""


def test_the_race_is_the_clubs_not_leading_a_division_by_record_with_games_back_of_the_third():
    # Leaders NYY, CLE, HOU sit out; BAL, MIN, KC hold the three places; BOS is 2.5 back of KC (66-55).
    out = run_node(['winPct', 'byRecord', 'wildCardRace'], RACE)
    assert out == [['BAL', 1, 0], ['MIN', 2, 0], ['KC', 3, 0], ['BOS', 4, 2.5], ['SEA', 5, 3], ['TEX', 6, 6]]


def test_clubs_level_on_record_are_shown_by_projected_wins():
    out = run_node(['winPct', 'byRecord', 'wildCardRace'], """
const t = (team, w, proj) => ({team, league: 'NL', division: 'NL ' + team, wins_now: w, losses_now: 60,
  projected_wins: proj, wildcard_pct: 0});
const leaders = ['A', 'B', 'C'].map(x => ({...t(x, 90, 99), division: 'NL ' + 'xyz'['ABC'.indexOf(x)]}));
const rest = [t('P', 60, 80), t('Q', 60, 84)].map((x, i) => ({...x, division: 'NL ' + 'xy'[i]}));
console.log(JSON.stringify(wildCardRace([...leaders, ...rest], 'NL').map(x => x.team)));""")
    assert out == ['Q', 'P']


def test_a_chance_never_rounds_to_certain():
    out = run_node(['chance'], """
console.log(JSON.stringify([0, 0.001, 0.004, 0.5, 0.996, 0.9999, 1].map(chance)));""")
    assert out == ['0%', '&lt;1%', '&lt;1%', '50%', '&gt;99%', '&gt;99%', '100%']


def test_the_race_marks_the_line_under_the_third_and_shows_no_games_back_above_it():
    fn = function_source(JS, 'raceTable', at_line_start=True)
    assert "t.place === 3 ? ' class=\"mlb-wc-line\"'" in fn
    assert re.search(r'function gamesBack\(n\)\{ return n > 0 \? String\(n\) : .–.; \}', JS)


def test_each_league_shows_east_central_west_named_as_the_file_names_them():
    """The divisions are shown in a fixed order, not the file's (which sorts by projected wins): the first render
    put the NL West above the NL East. Each name must be one the file writes."""
    m = re.search(r"const divs = \[('East', 'Central', 'West')\]\.map\(d => `\$\{lg\} \$\{d\}`\);", JS)
    assert m, 'the page does not list the divisions in a fixed order'
    shown = {f'{lg} {d}' for lg in ('AL', 'NL') for d in ('East', 'Central', 'West')}
    assert shown == set(standings.DIVISIONS)


def specificity(selector):
    """(ids, classes and attributes, elements) of one simple CSS selector."""
    s = re.sub(r'\[[^\]]*\]', ' [a] ', selector)
    return (s.count('#'), s.count('.') + s.count('[a]'), len(re.findall(r'(?:^|[\s>+~])([a-z][a-z0-9-]*)', s)))


def test_the_line_under_the_third_outranks_the_tables_own_row_border():
    """The first render showed no line: `.mlb-wc-line > *` loses to the shared `.metrics-table td` border."""
    css = (ROOT / 'src' / 'sports' / 'mlb' / 'pages' / 'mlb.css').read_text(encoding='utf-8')
    shared = (ROOT / 'src' / 'dashboard' / 'styles.css').read_text(encoding='utf-8')
    line = re.search(r'([^{}]*mlb-wc-line[^{}]*)\{[^}]*border-bottom:2px', css).group(1).strip()
    rival = re.search(r'(\.metrics-table td)\{[^}]*border-bottom:1px', shared).group(1)
    assert specificity(line) > specificity(rival), line
