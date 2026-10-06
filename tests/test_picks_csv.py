"""picks.csv: every locked pick and its grade, beside the board (Stage 46
item 7, src/pipeline/picks_csv.py).

Held here: locked weeks only, never a preview; each game joined to its own
grade; a game not yet played and a tie each say so and grade no one; a pick
is the side given 50% or more, as the grading has it; the file agrees with
the committed grades; and the site build writes it and publishes it beside
the board, which links to it.

Run with: pytest tests/test_picks_csv.py -v
"""
import csv
import json
from pathlib import Path

from src.pipeline import picks_csv
from src.pipeline.paths import PRED_DIR, RESULTS_DIR
from src.site import build

ROOT = Path(__file__).resolve().parents[1]


def game(away, home, a, b, mkt, day='2026-10-11', t='13:00'):
    return {'away': away, 'home': home, 'gameday': day, 'gametime_et': t, 'model_version': '2.5',
            'model_a_home_win_prob': a, 'model_b_home_win_prob': b, 'market_prob_home': mkt}


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj), encoding='utf-8')


def setup(tmp_path):
    pred, res = tmp_path / 'predictions', tmp_path / 'results'
    week = [game('NYG', 'WAS', 0.40, 0.54, 0.63, t='16:25'),
            game('SF', 'SEA', 0.5, 0.49, None),
            game('BUF', 'LA', 0.55, 0.58, 0.61, day='2026-10-12', t='20:15')]
    write(pred / '2026_week5.json', week)
    write(pred / 'preview' / '2026_week6.json', [game('A', 'B', 0.5, 0.5, 0.5)])
    graded = [dict(week[0], actual_home_win=1, model_a_correct=0, model_b_correct=1, market_correct=1),
              dict(week[1], result='tie', actual_home_win=None, model_a_correct=None,
                   model_b_correct=None, market_correct=None)]
    write(res / '2026_week5_graded.json', graded)
    return pred, res


def test_one_row_per_locked_game_in_kickoff_order_and_never_a_preview(tmp_path):
    rows = picks_csv.rows(*setup(tmp_path))
    assert [(r['away'], r['home']) for r in rows] == [('SF', 'SEA'), ('NYG', 'WAS'), ('BUF', 'LA')]


def test_each_game_carries_its_own_grade(tmp_path):
    rows = {r['home']: r for r in picks_csv.rows(*setup(tmp_path))}
    assert (rows['WAS']['result'], rows['WAS']['winner']) == ('final', 'WAS')
    assert (rows['WAS']['model_a_correct'], rows['WAS']['model_b_correct'], rows['WAS']['market_correct']) == ('0', '1', '1')


def test_a_tie_and_an_unplayed_game_grade_no_one(tmp_path):
    rows = {r['home']: r for r in picks_csv.rows(*setup(tmp_path))}
    assert (rows['SEA']['result'], rows['SEA']['winner'], rows['SEA']['model_b_correct']) == ('tie', '', '')
    assert (rows['LA']['result'], rows['LA']['winner'], rows['LA']['model_a_correct']) == ('', '', '')


def test_a_pick_is_the_side_given_fifty_percent_or_more(tmp_path):
    rows = {r['home']: r for r in picks_csv.rows(*setup(tmp_path))}
    assert rows['SEA']['model_a_pick'] == 'SEA', '50% exactly is a home pick, as grade_predictions has it'
    assert rows['SEA']['model_b_pick'] == 'SF'
    assert rows['SEA']['market_pick'] == '' and rows['SEA']['market_home_win_prob'] == ''
    assert rows['WAS']['model_a_home_win_prob'] == '0.4000'


def test_the_file_has_the_columns_in_order(tmp_path):
    out = tmp_path / 'picks.csv'
    n = picks_csv.write(out, *setup(tmp_path))
    with open(out, encoding='utf-8', newline='') as f:
        read = list(csv.DictReader(f))
    assert n == len(read) == 3
    assert list(read[0]) == picks_csv.COLUMNS


def test_the_file_agrees_with_the_committed_grades():
    """Every graded game in results/ appears once, with the same verdicts."""
    rows = picks_csv.rows(PRED_DIR, RESULTS_DIR)
    assert rows, 'no locked weeks found -- vacuity: nothing was checked'
    by = {(r['season'], r['week'], r['away'], r['home']): r for r in rows}
    checked = 0
    for path in sorted(RESULTS_DIR.glob('*_week*_graded.json')):
        season, week = path.stem.split('_week')[0], path.stem.split('_week')[1].split('_')[0]
        for g in json.loads(path.read_text(encoding='utf-8')):
            r = by[(season, week, g['away'], g['home'])]
            for k in ('model_a_correct', 'model_b_correct', 'market_correct'):
                assert r[k] == ('' if g.get(k) is None else str(int(g[k]))), (path.name, g['home'], k)
            checked += 1
    assert checked >= 16


def test_the_site_build_writes_it_and_publishes_it_beside_the_board():
    cmds = [' '.join(c[3:]) for c in build.build_commands('nfl', Path('_site'))]
    assert 'src.pipeline.picks_csv --out picks.csv' in cmds
    src = Path(build.__file__).read_text(encoding='utf-8')
    assert "shutil.copyfile(ROOT / 'picks.csv', dest / 'picks.csv')" in src


def test_the_board_links_to_it_and_git_ignores_it():
    body = (ROOT / 'src' / 'dashboard' / 'body.html').read_text(encoding='utf-8')
    assert 'id="picks-csv-link"' in body and 'href="picks.csv" download' in body
    assert '/picks.csv' in (ROOT / '.gitignore').read_text(encoding='utf-8').splitlines()
