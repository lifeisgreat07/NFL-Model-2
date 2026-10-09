"""Team news names the starters who will not play, and the pick's own QB (Stage 16).

src/sports/nfl/team_news.py keeps only what a reader needs to judge a pick: starters Out
or Doubtful by name, starters Questionable as a count, and the quarterback
the pick was made with. An unpublished report is never an empty one. The
injury report and depth chart are synthetic frames here, so the suite makes
no network call.

Run with: pytest tests/test_team_news.py -v
"""
import json
import re
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

from src.sports.nfl import team_news as tn

WEEKLY = ROOT / '.github' / 'workflows' / 'nfl-weekly-update.yml'
WEEKEND = ROOT / '.github' / 'workflows' / 'nfl-weekend-refresh.yml'

NOW = datetime(2026, 10, 2, 12, tzinfo=UTC)


def depth(*rows, dt='2026-10-01T12:00:00Z'):
    return pd.DataFrame([dict(dt=dt, team=t, gsis_id=g, pos_rank=r, pos_grp=grp, pos_abb=abb)
                         for t, g, r, grp, abb in rows])


def injuries(*rows):
    cols = ['week', 'team', 'gsis_id', 'full_name', 'position', 'report_status', 'report_primary_injury']
    return pd.DataFrame(rows, columns=cols) if rows else pd.DataFrame(columns=cols)


DEPTH = depth(
    ('CLE', 'qb1', '1', '3WR 1TE', 'QB'), ('CLE', 'wr1', '1', '3WR 1TE', 'WR'),
    ('CLE', 'wr3', '3', '3WR 1TE', 'WR'), ('CLE', 'lb1', '1', 'Base 4-3 D', 'MLB'),
    ('CLE', 'k1', '1', 'Special Teams', 'PK'), ('CLE', 'kr1', '1', 'Special Teams', 'KR'),
    ('PIT', 'pqb', '1', '3WR 1TE', 'QB'),
)
PICK = {'home': 'CLE', 'away': 'PIT', 'home_qb': 'Deshaun Watson', 'home_qb_id': '00-1',
        'home_qb_basis': 'announced', 'last_game_home_qb': 'Joe Flacco', 'last_game_home_qb_id': '00-2',
        'away_qb': 'Aaron Rodgers', 'away_qb_id': '00-3', 'away_qb_basis': 'announced',
        'last_game_away_qb': 'Aaron Rodgers', 'last_game_away_qb_id': '00-3'}


def test_starters_are_rank_one_on_offense_and_defense_plus_kickers():
    s = tn.starters(DEPTH)
    assert s['CLE'] == {'qb1', 'wr1', 'lb1', 'k1'}, 'a backup and a returner are not starters'


def test_only_the_latest_depth_chart_counts():
    old = depth(('CLE', 'old1', '1', '3WR 1TE', 'WR'), dt='2026-09-01T12:00:00Z')
    s = tn.starters(pd.concat([old, DEPTH]))
    assert 'old1' not in s['CLE']


def test_out_and_doubtful_starters_are_named_questionable_ones_counted():
    inj = injuries((4, 'CLE', 'wr1', 'Jerry Jeudy', 'WR', 'Out', 'Hamstring'),
                   (4, 'CLE', 'lb1', 'Mo Linebacker', 'LB', 'Doubtful', None),
                   (4, 'CLE', 'k1', 'Kicker Guy', 'K', 'Questionable', 'Back'),
                   (4, 'CLE', 'wr3', 'Backup Receiver', 'WR', 'Out', 'Knee'),
                   (4, 'CLE', 'qb1', 'Deshaun Watson', 'QB', None, None))
    teams = tn.build_week([PICK], inj, DEPTH, 4)
    cle = teams['CLE']
    assert cle['injury_report'] == 'published'
    assert cle['out'] == [{'name': 'Jerry Jeudy', 'position': 'WR', 'injury': 'Hamstring'}]
    assert cle['doubtful'] == [{'name': 'Mo Linebacker', 'position': 'LB', 'injury': None}]
    assert cle['questionable_starters'] == 1, 'the backup receiver is not news'


def test_a_missing_injury_is_null_not_nan():
    inj = injuries((4, 'CLE', 'wr1', 'Jerry Jeudy', 'WR', 'Out', float('nan')))
    out = tn.build_week([PICK], inj, DEPTH, 4)['CLE']['out'][0]
    assert out['injury'] is None
    json.dumps(out, allow_nan=False)


def test_an_unpublished_report_is_never_an_empty_one():
    inj = injuries((3, 'CLE', 'wr1', 'Jerry Jeudy', 'WR', 'Out', 'Hamstring'))
    cle = tn.build_week([PICK], inj, DEPTH, 4)['CLE']
    assert cle['injury_report'] == 'not yet published'
    assert 'out' not in cle and 'doubtful' not in cle, 'an empty list would read as "nobody hurt"'


def test_a_team_with_no_depth_chart_says_so():
    teams = tn.build_week([dict(PICK, away='NYJ')], injuries((4, 'NYJ', 'x', 'X', 'WR', 'Out', None)), DEPTH, 4)
    assert teams['NYJ']['injury_report'] == 'no depth chart for this team' and 'out' not in teams['NYJ']


def test_the_quarterback_is_the_picks_own_and_a_change_is_flagged():
    teams = tn.build_week([PICK], injuries(), DEPTH, 4)
    assert teams['CLE']['qb'] == {'name': 'Deshaun Watson', 'basis': 'announced', 'changed_from': 'Joe Flacco'}
    assert teams['PIT']['qb'] == {'name': 'Aaron Rodgers', 'basis': 'announced', 'changed_from': None}


def test_a_pick_saved_before_the_qb_fields_has_no_qb_line():
    old = {'home': 'CLE', 'away': 'PIT'}
    assert tn.build_week([old], injuries(), DEPTH, 4)['CLE']['qb'] is None


def test_an_unchanged_week_is_not_rewritten(tmp_path):
    teams = tn.build_week([PICK], injuries(), DEPTH, 4)
    assert tn.write_week(2026, 4, teams, 'dt1', NOW, tmp_path) is True
    assert tn.write_week(2026, 4, teams, 'dt2', NOW, tmp_path) is False
    saved = json.loads((tmp_path / '2026_week4.json').read_text(encoding='utf-8'))
    assert saved['sources']['depth_chart_snapshot'] == 'dt1' and saved['teams'] == teams


def test_pending_reports_on_the_locked_weeks(tmp_path, capsys):
    preds, results = tmp_path / 'predictions', tmp_path / 'results'
    preds.mkdir(); results.mkdir()
    (preds / '2026_week4.json').write_text(json.dumps([PICK]), encoding='utf-8')
    inj = injuries((4, 'CLE', 'wr1', 'Jerry Jeudy', 'WR', 'Out', 'Hamstring'))
    assert tn.main(['--pending'], now=NOW, load=lambda s: (inj, DEPTH), pred_dir=preds,
                   results_dir=results, news_dir=tmp_path / 'news') == 0
    saved = json.loads((tmp_path / 'news' / '2026_week4.json').read_text(encoding='utf-8'))
    assert saved['teams']['CLE']['out'][0]['name'] == 'Jerry Jeudy'
    assert '1 starter(s) out or doubtful' in capsys.readouterr().out


def test_nothing_pending_loads_nothing(tmp_path, capsys):
    def load(season):
        raise AssertionError('nothing is pending, so nothing may be loaded')
    assert tn.main(['--pending'], now=NOW, load=load, pred_dir=tmp_path, results_dir=tmp_path,
                   news_dir=tmp_path / 'news') == 0
    assert 'no team news to read' in capsys.readouterr().out


def _steps(path):
    """({step name: its text}, [step names in order]), each step bounded by the next `- name:`."""
    text = path.read_text(encoding='utf-8')
    out = {}
    for part in re.split(r'\n(?=      - name: )', text):
        m = re.match(r'\s*- name: (.+)', part)
        if m:
            out[m.group(1).strip()] = part
    return out, [m.group(1).strip() for m in re.finditer(r'\n      - name: (.+)', text)]


def test_both_workflows_read_team_news_and_cannot_fail_on_it():
    for path in (WEEKLY, WEEKEND):
        steps, _ = _steps(path)
        step = steps.get('Read team news')
        assert step, f'{path.name} has no "Read team news" step'
        assert 'python -m src.sports.nfl.team_news --pending' in step
        assert re.search(r'^\s+continue-on-error: true\s*$', step, re.M), (
            f'{path.name}: without continue-on-error a failed injury read fails the run -- '
            f'and in Weekly update that run is the one that locks the picks')
        assert 'shell: bash' in step, 'without bash there is no pipefail under | tee'


def test_the_weekly_run_reads_team_news_after_it_locks_and_before_it_commits():
    steps, order = _steps(WEEKLY)
    i = order.index('Read team news')
    assert order.index("Generate/lock in this week's predictions") < i < order.index('Commit and push changes'), (
        'before the lock, the week just locked is not yet pending and goes into Thursday night with no news')
    assert i > order.index('Summarise the run'), 'the summary reads git status for predictions and results'
    assert '${{ !cancelled() }}' in steps['Read team news']


def test_the_refresh_reads_team_news_before_it_commits_it():
    steps, order = _steps(WEEKEND)
    assert order.index('Read team news') < order.index('Commit and push changes')
    assert 'data/nfl/team_news/**' in steps['Commit and push changes'], (
        'the refresh reads team news and then does not commit it, so Friday\'s ruling never reaches the page')
