"""TV channels are read on a schedule, and can never cost a pick (Stage 15).

src/pipeline/tv_channels.py --pending reads every locked week not yet fully graded.
"Weekly update" runs it after the Tuesday grading and the Thursday lock, and
"Weekend refresh" runs it before the weekend's games; both with
continue-on-error, because a TV listing must never fail the run that makes
or refreshes picks. The page is fetched through a stub here, so the suite
makes no network call.

Run with: pytest tests/test_tv_schedule.py -v
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

from src.pipeline import tv_channels as tv  # noqa: E402

WEEKLY = ROOT / '.github' / 'workflows' / 'weekly-update.yml'
WEEKEND = ROOT / '.github' / 'workflows' / 'weekend-refresh.yml'
NOW = datetime(2026, 9, 27, 20, tzinfo=timezone.utc)


def _write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj), encoding='utf-8')


def _dirs(tmp_path):
    preds, results, tvdir = tmp_path / 'predictions', tmp_path / 'results', tmp_path / 'tv'
    _write(tvdir / 'exceptions.json', {'exceptions': []})
    return preds, results, tvdir


def test_pending_reads_every_locked_week_not_yet_graded(tmp_path):
    preds, results, tvdir = _dirs(tmp_path)
    two = [{'home': 'CLE', 'away': 'PIT'}, {'home': 'BUF', 'away': 'NE'}]
    _write(preds / '2026_week2.json', two)
    _write(results / '2026_week2_graded.json', two)
    _write(preds / '2026_week3.json', two)
    _write(results / '2026_week3_graded.json', [])
    _write(preds / '2026_week4.json', two)
    asked = []
    def page(week, season):
        asked.append(week)
        return ''
    tv.main(['--pending'], now=NOW, load=lambda s: pd.DataFrame({'week': []}), fetch_page=page,
            tv_dir=tvdir, pred_dir=preds, results_dir=results)
    assert asked == [3, 4]


def test_pending_with_nothing_waiting_fetches_nothing(tmp_path, capsys):
    preds, results, tvdir = _dirs(tmp_path)
    def page(week, season):
        raise AssertionError('nothing is waiting on grading, so no page may be fetched')
    def load(season):
        raise AssertionError('nothing is waiting on grading, so the schedule may not be loaded')
    assert tv.main(['--pending'], now=NOW, load=load, fetch_page=page, tv_dir=tvdir,
                   pred_dir=preds, results_dir=results) == 0
    assert 'no channels to read' in capsys.readouterr().out


def _steps(path):
    """{step name: its text}, each bounded by the next `- name:`."""
    text = path.read_text(encoding='utf-8')
    parts = re.split(r'\n(?=      - name: )', text)
    out = {}
    for p in parts:
        m = re.match(r'\s*- name: (.+)', p)
        if m:
            out[m.group(1).strip()] = p
    return out, [m.group(1).strip() for m in re.finditer(r'\n      - name: (.+)', text)]


def test_both_workflows_read_channels_and_cannot_fail_on_them():
    for path in (WEEKLY, WEEKEND):
        steps, _ = _steps(path)
        step = steps.get('Read TV channels')
        assert step, f'{path.name} has no "Read TV channels" step'
        assert 'python -m src.pipeline.tv_channels --pending' in step
        assert re.search(r'^\s+continue-on-error: true\s*$', step, re.M), (
            f'{path.name}: without continue-on-error a failed TV read fails the run -- '
            f'and in Weekly update that run is the one that locks the picks')
        assert 'shell: bash' in step, 'without bash there is no pipefail under | tee'


def test_the_weekly_run_reads_channels_after_it_locks_and_before_it_commits():
    steps, order = _steps(WEEKLY)
    i = order.index('Read TV channels')
    assert order.index("Generate/lock in this week's predictions") < i < order.index('Commit and push changes')
    assert i > order.index('Summarise the run'), 'the summary reads git status for predictions and results'
    assert '${{ !cancelled() }}' in steps['Read TV channels']


def test_the_refresh_reads_channels_before_it_commits():
    _, order = _steps(WEEKEND)
    assert order.index('Read TV channels') < order.index('Commit and push changes')
