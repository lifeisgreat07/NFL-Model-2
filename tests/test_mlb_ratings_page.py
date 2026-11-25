"""MLB's Power Ratings page (Stage 100 item 2, layout C, Mark 2026-11-23): Clubs and Starters behind chips, the
starters with a club filter, a sort and the first forty until "Show all".

The page reads `results/mlb/ratings_<season>.json`, written by src/sports/mlb/page_inputs.py's ratings_json, which
MLB's daily run will call (Stage 101); the build turns each club's Stats API id into its code.

Run with: pytest tests/test_mlb_ratings_page.py -v
"""
import json
import subprocess
from pathlib import Path

from src.sports.mlb import page_inputs, site
from src.sports.mlb.ratings import DayRatings
from tests.js_source import function_source
from tests.optional import require_tool

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / 'src' / 'sports' / 'mlb' / 'pages' / 'mlb.js').read_text(encoding='utf-8').replace('\r\n', '\n')
BODY = (ROOT / 'src' / 'sports' / 'mlb' / 'pages' / 'body.html').read_text(encoding='utf-8')
NYY, BOS, TOR = '147', '111', '141'
RATED = DayRatings(runs={NYY: 0.61, BOS: 0.04, TOR: -0.3}, league_rate=4.55,
                   pitchers={'1': 3.3, '2': 4.9, '3': 3.9, '4': 2.0})
# Pitcher 1 starts three times, the last for Toronto; 2 three times; 3 three times; 4 only twice.
STARTS = [('1', NYY, '2024-04-01'), ('1', NYY, '2024-05-01'), ('1', TOR, '2024-08-01'),
          ('2', BOS, '2024-04-02'), ('2', BOS, '2024-05-02'), ('2', BOS, '2024-06-02'),
          ('3', NYY, '2024-04-03'), ('3', NYY, '2024-05-03'), ('3', NYY, '2024-06-03'),
          ('4', BOS, '2024-04-04'), ('4', BOS, '2024-05-04')]


def doc():
    return page_inputs.ratings_json(RATED, 150.0, STARTS, {'1': 400.0, '2': 300.0, '3': 250.0},
                                    {'1': 'Ace One', '2': 'Two'}, '2024-08-15')


def test_clubs_go_best_first_and_starters_by_rate_with_enough_starts():
    d = doc()
    assert [c['team'] for c in d['clubs']] == [NYY, BOS, TOR]
    assert [s['player_id'] for s in d['starters']] == ['1', '3', '2'], 'pitcher 4 has two starts and is not listed'
    assert (d['league_rate'], d['K_outs'], d['min_starts']) == (4.55, 150.0, page_inputs.MIN_STARTS)


def test_a_starters_club_is_his_latest_starts_and_a_name_may_be_missing():
    s = {x['player_id']: x for x in doc()['starters']}
    assert s['1']['club'] == TOR and s['1']['starts'] == 3 and s['1']['outs'] == 400.0
    assert s['3']['name'] is None


def board_with(tmp_path, monkeypatch, d):
    res = tmp_path / 'results'
    res.mkdir()
    if d is not None:
        (res / 'ratings_2026.json').write_text(json.dumps(d), encoding='utf-8')
    monkeypatch.setattr(site, 'PATHS', type('P', (), {'results': res, 'predictions': res.parent.parent / 'predictions' / 'mlb'})())
    return site.board(2026)


def test_the_build_names_each_club_by_its_code(tmp_path, monkeypatch):
    r = board_with(tmp_path, monkeypatch, doc())['ratings']
    assert [c['team'] for c in r['clubs']] == ['NYY', 'BOS', 'TOR']
    assert [s['club'] for s in r['starters']] == ['TOR', 'NYY', 'BOS']


def test_before_the_first_run_the_page_says_so(tmp_path, monkeypatch):
    assert board_with(tmp_path, monkeypatch, None)['ratings'] is None
    assert "'No ratings yet'" in JS


def test_the_page_has_the_ratings_page_and_both_buttons():
    assert BODY.count('data-page="ratings"') == 2 and 'id="page-ratings"' in BODY and 'id="ratings-body"' in BODY


def run_node(names, body):
    node = require_tool('node')
    head = 'const STARTERS_SHOWN = 40;\n'
    src = head + ''.join(function_source(JS, n, at_line_start=True) for n in names) + body
    r = subprocess.run([node, '-e', src], capture_output=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


STARTERS = """
const s = [...Array(50).keys()].map(i => ({player_id: String(i), club: i % 2 ? 'NYY' : 'BOS', rate: 3 + i / 10,
  starts: 30 - (i % 7)}));
const pick = x => [x.rows.map(r => r.player_id), x.of];
"""


def test_the_first_forty_then_all():
    out = run_node(['startersShown'], STARTERS + """
console.log(JSON.stringify([pick(startersShown(s, '', 'best', false)), pick(startersShown(s, '', 'best', true))]));""")
    assert out[0] == [[str(i) for i in range(40)], 50] and out[1] == [[str(i) for i in range(50)], 50]


def test_a_club_shows_only_its_starters_and_most_starts_sorts_by_starts_then_rate():
    out = run_node(['startersShown'], STARTERS + """
console.log(JSON.stringify([pick(startersShown(s, 'NYY', 'best', false)),
  startersShown(s, '', 'starts', true).rows.slice(0, 3).map(r => [r.starts, r.player_id])]));""")
    assert out[0] == [[str(i) for i in range(1, 50, 2)], 25]
    assert out[1] == [[30, '0'], [30, '7'], [30, '14']]


def test_a_rating_is_signed_with_a_plain_minus():
    out = run_node(['plusMinus'], "console.log(JSON.stringify([0.614, -0.3, 0].map(x => plusMinus(x, 2))));")
    assert out == ['+0.61', '-0.30', '0.00']
