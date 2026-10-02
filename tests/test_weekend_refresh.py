"""The weekend refresh reports status, scores and lines, and never touches a pick.

Stage 15 (CLAUDE.md). src/pipeline/weekend_refresh.py writes data/game_status/ between
the Thursday lock and Tuesday's grading. These tests hold what it decides for
a game, which weeks it refreshes, that an unchanged snapshot is not rewritten,
that it writes nothing outside data/game_status/, and the workflow that runs
it: its schedule, its commit scope, its alert, and its bridge to the page
build. The schedule is replaced here, so the suite makes no network call.

Run with: pytest tests/test_weekend_refresh.py -v
"""
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]

from src.pipeline import weekend_refresh as wr  # noqa: E402

WORKFLOW = ROOT / '.github' / 'workflows' / 'weekend-refresh.yml'
WEEKLY = ROOT / '.github' / 'workflows' / 'weekly-update.yml'
BUILDER = ROOT / '.github' / 'workflows' / 'deploy-pages.yml'

# Sunday 2026-10-04, 18:00 UTC: the early games (1:00 PM ET, 17:00 UTC) have
# kicked off, the late ones (4:25 PM ET) have not.
SUNDAY = datetime(2026, 10, 4, 18, 0, tzinfo=timezone.utc)


def row(away, home, gameday='2026-10-04', gametime='13:00', away_score=None,
        home_score=None, spread=3.0, week=4):
    return {'away_team': away, 'home_team': home, 'gameday': gameday,
            'gametime': gametime, 'away_score': away_score,
            'home_score': home_score, 'spread_line': spread, 'week': week}


def sched(*rows):
    return pd.DataFrame(list(rows))


def pick(away, home):
    return {'away': away, 'home': home, 'model_a_home_win_prob': 0.6}


def test_a_game_with_both_scores_is_final():
    r = row('PIT', 'CLE', gameday='2026-10-01', gametime='20:15', away_score=20, home_score=17)
    assert wr.game_status(pd.Series(r), SUNDAY) == 'final'


def test_a_kicked_off_game_without_a_final_score_has_started():
    assert wr.game_status(pd.Series(row('NE', 'BUF')), SUNDAY) == 'started'


def test_a_game_not_yet_kicked_off_is_upcoming():
    assert wr.game_status(pd.Series(row('KC', 'LV', gametime='16:25')), SUNDAY) == 'upcoming'


def test_one_score_is_not_a_final():
    r = row('NE', 'BUF', away_score=21, home_score=float('nan'))
    assert wr.game_status(pd.Series(r), SUNDAY) == 'started'


def test_a_week_carries_scores_only_when_final_and_follows_the_picks():
    rows = sched(row('KC', 'LV', gametime='16:25', spread=float('nan')),
                 row('PIT', 'CLE', gameday='2026-10-01', gametime='20:15',
                     away_score=20, home_score=17, spread=-3.0),
                 row('NE', 'BUF', away_score=7, home_score=float('nan')))
    games, missing = wr.build_week([pick('PIT', 'CLE'), pick('NE', 'BUF'),
                                    pick('KC', 'LV'), pick('DAL', 'HOU')], rows, SUNDAY)
    assert games == [
        {'away': 'PIT', 'home': 'CLE', 'status': 'final', 'away_score': 20,
         'home_score': 17, 'spread_line': -3.0},
        {'away': 'NE', 'home': 'BUF', 'status': 'started', 'away_score': None,
         'home_score': None, 'spread_line': 3.0},
        {'away': 'KC', 'home': 'LV', 'status': 'upcoming', 'away_score': None,
         'home_score': None, 'spread_line': None},
    ]
    assert missing == [('DAL', 'HOU')], 'a pick the schedule lost is reported, never filled in'


def _write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj), encoding='utf-8')


def test_only_weeks_with_fewer_grades_than_picks_are_refreshed(tmp_path):
    preds, results = tmp_path / 'predictions', tmp_path / 'results'
    two = [pick('PIT', 'CLE'), pick('NE', 'BUF')]
    _write(preds / '2026_week2.json', two)
    _write(results / '2026_week2_graded.json', two)       # fully graded
    _write(preds / '2026_week3.json', two)
    _write(results / '2026_week3_graded.json', [])        # graded before it was played
    _write(preds / '2026_week4.json', two)                # not graded at all
    _write(preds / '2025_week18.json', two)               # another season
    assert wr.weeks_to_refresh(2026, preds, results) == [3, 4]


def test_an_unchanged_snapshot_is_not_rewritten(tmp_path):
    games = [{'away': 'PIT', 'home': 'CLE', 'status': 'upcoming', 'away_score': None,
              'home_score': None, 'spread_line': -3.0}]
    assert wr.write_week(2026, 4, games, SUNDAY, tmp_path) is True
    first = (tmp_path / '2026_week4.json').read_text(encoding='utf-8')
    later = datetime(2026, 10, 5, 5, 37, tzinfo=timezone.utc)
    assert wr.write_week(2026, 4, games, later, tmp_path) is False
    assert (tmp_path / '2026_week4.json').read_text(encoding='utf-8') == first
    changed = [dict(games[0], status='final', away_score=20, home_score=17)]
    assert wr.write_week(2026, 4, changed, later, tmp_path) is True
    saved = json.loads((tmp_path / '2026_week4.json').read_text(encoding='utf-8'))
    assert saved['read_at'] == '2026-10-05T05:37:00Z' and saved['source'] == wr.SOURCE
    assert saved['games'] == changed


def _digest(folder):
    return {p.relative_to(folder).as_posix(): hashlib.md5(p.read_bytes()).hexdigest()
            for p in sorted(folder.rglob('*')) if p.is_file()}


def test_a_run_writes_game_status_and_nothing_else(tmp_path, capsys):
    """Two writers of picks is two ways to break a lock (2026-09-24)."""
    preds, results, status = tmp_path / 'predictions', tmp_path / 'results', tmp_path / 'status'
    _write(preds / '2026_week4.json', [pick('PIT', 'CLE'), pick('NE', 'BUF')])
    _write(results / '2026_week3_graded.json', [])
    before = _digest(tmp_path)
    load = lambda season: sched(row('PIT', 'CLE', gameday='2026-10-01', gametime='20:15',
                                    away_score=20, home_score=17), row('NE', 'BUF'),
                                row('X', 'Y', week=5))
    assert wr.main(['--season', '2026'], now=SUNDAY, load=load, pred_dir=preds,
                   results_dir=results, status_dir=status) == 0
    after = _digest(tmp_path)
    assert {k: v for k, v in after.items() if not k.startswith('status/')} == before
    assert sorted(k for k in after if k.startswith('status/')) == ['status/2026_week4.json']
    assert '1 final, 1 started, 0 upcoming -- written' in capsys.readouterr().out


def test_nothing_to_refresh_loads_nothing(tmp_path, capsys):
    def load(season):
        raise AssertionError('no week needs refreshing, so the schedule must not be fetched')
    assert wr.main(['--season', '2026'], now=SUNDAY, load=load, pred_dir=tmp_path,
                   results_dir=tmp_path, status_dir=tmp_path / 'status') == 0
    assert 'nothing to refresh' in capsys.readouterr().out


@pytest.mark.parametrize('today, season', [
    (datetime(2026, 9, 27), 2026), (datetime(2027, 1, 10), 2026),
    (datetime(2027, 2, 28), 2026), (datetime(2027, 3, 1), 2027)])
def test_the_season_rolls_over_after_february(today, season):
    assert wr.current_season(today) == season


def test_the_source_writes_only_under_game_status():
    src = (ROOT / 'src' / 'pipeline' / 'weekend_refresh.py').read_text(encoding='utf-8')
    code = re.sub(r'(?s)""".*?"""', '', src)
    assert code.count("open(path, 'w')") == 1 and 'write_text' not in code
    assert "path = status_dir /" in code


def _text(path):
    return path.read_text(encoding='utf-8')


def test_the_workflow_commits_game_status_and_nothing_else():
    patterns = re.findall(r"^\s*file_pattern:\s*'([^']*)'", _text(WORKFLOW), re.M)
    assert patterns == ['data/game_status/** data/tv/** data/team_news/**'], (
        f'the weekend refresh commits {patterns}; it may commit data/game_status/**, '
        f'data/tv/** and data/team_news/** only -- a second writer of predictions/ or '
        f'results/ is a second way to break a lock')
    assert 'git add' not in _text(WORKFLOW)


def _cron_times(text):
    out = []
    for m, h, _, _, dow in re.findall(r"cron:\s*'(\S+) (\S+) (\S+) (\S+) (\S+)'", text):
        out.append((int(dow), int(h) * 60 + int(m)))
    return out


def test_its_runs_cannot_meet_the_weekly_runs_even_five_hours_late():
    mine, weekly = _cron_times(_text(WORKFLOW)), _cron_times(_text(WEEKLY))
    assert len(mine) == 3 and len(weekly) == 2
    week = 7 * 24 * 60
    def at(dow, minute):
        return (dow * 24 * 60 + minute) % week
    for d, t in mine:
        start = at(d, t)
        for wd, wt in weekly:
            other = at(wd, wt)
            for s in (start, start + 5 * 60):
                gap = min((s - other) % week, (other - s) % week)
                assert gap >= 60, f'a refresh at cron day {d} minute {t} can run within an hour of the weekly run'


def test_a_failed_refresh_raises_an_alert():
    text = _text(WORKFLOW)
    assert re.search(r"if: failure\(\)[\s\S]*?alerts\.py --title \"Weekend refresh failed\"", text)
    assert re.search(r'permissions:[\s\S]*?issues: write', text)
    assert 'shell: bash' in text, 'without bash there is no pipefail, and | tee hides a failed refresh'


def test_the_page_build_runs_after_it():
    name = re.search(r'^name:\s*(.+?)\s*$', _text(WORKFLOW), re.M).group(1)
    listed = re.search(r'workflow_run:\s*\n\s*workflows:\s*\[(.*?)\]', _text(BUILDER), re.S).group(1)
    assert name in [n.strip().strip('"\'') for n in listed.split(',')]


WEEKLY = ROOT / '.github' / 'workflows' / 'weekly-update.yml'


def _step_blocks(path):
    """[(name, text)] for each step, in order."""
    text = _text(path)
    parts = re.split(r'\n(?=      - name: )', text)
    out = []
    for part in parts:
        m = re.match(r'\s*- name: (.+)', part)
        if m:
            out.append((m.group(1).strip(), part))
    return out


AUTO_COMMIT = 'stefanzweifel/git-auto-commit-action@'
WORKFLOWS_DIR = ROOT / '.github' / 'workflows'


def _pushers():
    """Every workflow with a git-auto-commit step, found rather than listed.
    Until Stage 35 this test named two workflows by hand, and the third one
    that pushes main unattended, collect-agent-log.yml, had no catch-up; the
    third audit found it. booth-regression.yml also pushes, with a plain
    `git push` it runs itself, and is deliberately outside this rule: it is
    started by hand, pushes the ref it was dispatched on, and commits before
    pushing, so a refused push is a red run in front of the person who
    started it, not a silent loss."""
    return sorted(p for p in WORKFLOWS_DIR.glob('*.yml')
                  if AUTO_COMMIT in p.read_text(encoding='utf-8'))


def test_every_unattended_pusher_is_found():
    """The discovery must find at least the three known pushers, or the rule
    below could pass by checking nothing."""
    names = {p.name for p in _pushers()}
    assert {'weekend-refresh.yml', 'weekly-update.yml', 'collect-agent-log.yml'} <= names, names


@pytest.mark.parametrize('path', _pushers(), ids=lambda p: p.stem)
def test_the_commit_catches_up_with_main_first(path):
    """Run 36360495917 read everything and saved nothing: a merge landed between
    its checkout and its push, and the push was refused. Every commit step must
    be preceded, immediately, by a rebase onto main that carries the run's
    uncommitted files across."""
    steps = _step_blocks(path)
    commits = [i for i, (_, body) in enumerate(steps) if AUTO_COMMIT in body]
    assert commits, f'{path.name}: no commit step found'
    for i in commits:
        name, body = steps[i - 1]
        assert name == 'Catch up with main', f'{path.name}: nothing catches up with main before {steps[i][0]!r}'
        assert 'pull --rebase --autostash origin main' in body, 'without --autostash the rebase refuses a dirty tree'
        assert "user.email=" in body and "user.name=" in body, 'autostash makes a commit, and the runner has no identity'


def test_the_lock_run_catches_up_even_after_a_failed_step():
    """The weekly commit step runs unless cancelled, so a failed summary still
    saves the picks; its catch-up must run under the same condition."""
    steps = dict(_step_blocks(WEEKLY))
    assert '${{ !cancelled() }}' in steps['Catch up with main']
