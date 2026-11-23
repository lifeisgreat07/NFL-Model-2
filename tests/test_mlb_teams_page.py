"""MLB's Teams and What's Changed pages (Stage 100 item 2).

Teams is the NHL's page, one club at a time, with what baseball adds: the club's starters from the ratings file. A
game's result is read from the club's side. What's Changed lists src/sports/mlb/pages/changes.json, which
tests/test_whats_changed_complete.py holds to the registration's amendments both ways.

Run with: pytest tests/test_mlb_teams_page.py -v
"""
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from src.sports.mlb import site
from tests.js_source import function_source
from tests.optional import require_tool

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / 'src' / 'sports' / 'mlb' / 'pages' / 'mlb.js').read_text(encoding='utf-8').replace('\r\n', '\n')
BODY = (ROOT / 'src' / 'sports' / 'mlb' / 'pages' / 'body.html').read_text(encoding='utf-8')
CHANGES = ROOT / 'src' / 'sports' / 'mlb' / 'pages' / 'changes.json'
ESCAPE = (ROOT / 'src' / 'core' / 'escape.js').read_text(encoding='utf-8').replace('\r\n', '\n') + '\n'


def test_the_page_data_carries_the_changes_newest_first(monkeypatch):
    monkeypatch.setattr(site, 'board', lambda season: {'season': season})
    monkeypatch.setattr(site, 'lab', lambda: None)
    changes = site.payload(datetime(2027, 2, 15, tzinfo=UTC))['changes']
    assert changes == json.loads(CHANGES.read_text(encoding='utf-8'))
    assert [c['date'] for c in changes] == sorted((c['date'] for c in changes), reverse=True)


def test_both_pages_have_their_buttons_and_teams_has_its_picker():
    for page in ('teams', 'changes'):
        assert BODY.count(f'data-page="{page}"') == 2 and f'id="page-{page}"' in BODY
    assert '<label class="mlb-team-label" for="team-select">Club</label>' in BODY


def run_node(names, body):
    node = require_tool('node')
    src = ''.join(function_source(JS, n, at_line_start=True) for n in names) + body
    r = subprocess.run([node, '-e', src], capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_a_result_is_read_from_the_clubs_side():
    out = run_node(['gameResult'], """
const g = {status: 'final', home: 'NYY', away: 'BOS', hs: 5, as: 3};
console.log(JSON.stringify([gameResult(g, 'NYY'), gameResult(g, 'BOS'),
  gameResult({...g, hs: 1, as: 1}, 'NYY'), gameResult({...g, status: 'scheduled', hs: null, as: null}, 'NYY')]));""")
    assert out == ['W 5-3', 'L 3-5', 'T 1-1', '']


def test_the_facts_give_the_rank_among_the_rated_clubs_and_say_when_nothing_is_there():
    out = run_node(['plusMinus', 'chance', 'teamFacts'], ESCAPE + """
const r = {clubs: [{team: 'LAD', runs: 0.78}, {team: 'NYY', runs: 0.61}]};
const s = {teams: [{team: 'NYY', wins_now: 72, losses_now: 50, projected_wins: 92.1, playoff_pct: 0.98,
  division: 'AL East', division_pct: 0.55}]};
console.log(JSON.stringify([teamFacts('NYY', r, s), teamFacts('NYY', null, null)]));""")
    assert out[0][0] == 'Run rating <b>+0.61</b> a game (2 of 2).'
    assert out[0][1] == '72-50; projected <b>92.1</b> wins, the postseason <b>98%</b>, the AL East title 55%.'
    assert out[1] == ['No ratings yet.', 'Standings odds not simulated yet.']
