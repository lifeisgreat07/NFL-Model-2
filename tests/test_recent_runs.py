"""The scheduled jobs' last runs on Checking the AI's work (Stage 41 item 4).

src/pipeline/recent_runs.py reads them from GitHub's Actions API in the
deploy job; the generator puts them in the page as `recentRuns`; app.js's
renderRecentRuns draws the table. Each half is checked here with no network:
the reader over a fake API, the renderer in node over the shipped template.

Run with: pytest tests/test_recent_runs.py -v
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from src.pipeline import generate_dashboard as gd
from src.pipeline import recent_runs as rr
from src.pipeline.template_parts import JOINED_TEMPLATE

REPO = Path(__file__).parent.parent
WORKFLOWS = REPO / '.github' / 'workflows'
NODE = shutil.which('node')


def run(n, name='x', event='schedule', conclusion='success', status='completed', minute=0):
    started = f'2026-10-0{n}T21:{minute:02d}:00Z'
    return {'id': n, 'name': name, 'event': event, 'status': status, 'conclusion': conclusion,
            'run_started_at': started, 'created_at': started,
            'updated_at': f'2026-10-0{n}T21:{minute + 3:02d}:30Z',
            'html_url': f'https://github.com/o/r/actions/runs/{n}'}


def fake_api(per_file):
    calls = []

    def get(url, token=None):
        calls.append((url, token))
        file = re.search(r'/workflows/([^/]+)/runs', url).group(1)
        return {'workflow_runs': per_file.get(file, [])}
    return get, calls


# --- the reader ---------------------------------------------------------------

def test_every_scheduled_workflow_is_watched_and_every_watched_one_is_scheduled():
    """A new job on a timer is on the page without anyone remembering to add it.

    A sport whose pages are not built yet has its jobs in
    `src/agents/session_start.py`'s SPORT_WATCHED instead: this page is the
    NFL's until Stage 57, and a session still sees those runs. Every
    scheduled job is in exactly one of the two."""
    from src.agents import session_start as ss
    scheduled = {p.name for p in WORKFLOWS.glob('*.yml')
                 if re.search(r'^\s+schedule:\s*$', p.read_text(encoding='utf-8'), re.M)}
    assert len(scheduled) >= 4, scheduled
    assert not set(rr.WATCHED) & set(ss.SPORT_WATCHED)
    assert set(rr.WATCHED) | set(ss.SPORT_WATCHED) == scheduled


def test_runs_are_merged_across_the_jobs_newest_first_and_cut_to_thirty():
    per_file = {f: [run(1 + (k % 9), name=f, minute=i) for k in range(12)] for i, f in enumerate(rr.WATCHED)}
    get, calls = fake_api(per_file)
    rows = rr.fetch('o/r', 'tok', get)
    assert len(calls) == len(rr.WATCHED) and all(t == 'tok' for _, t in calls)
    assert len(rows) == rr.SHOWN == 30
    starts = [r['started_utc'] for r in rows]
    assert starts == sorted(starts, reverse=True)
    assert {r['workflow'] for r in rows} <= set(rr.WATCHED.values())


def test_a_finished_run_has_its_minutes_and_a_running_one_has_neither_result_nor_minutes():
    done = rr.row(run(4, minute=47), 'Weekend refresh')
    assert done == {'workflow': 'Weekend refresh', 'event': 'schedule', 'conclusion': 'success',
                    'started_utc': '2026-10-04T21:47:00Z', 'minutes': 3.5,
                    'url': 'https://github.com/o/r/actions/runs/4'}
    going = rr.row(run(4, status='in_progress', conclusion=None), 'Weekend refresh')
    assert going['conclusion'] is None and going['minutes'] is None


def test_a_read_writes_the_file_the_build_reads(tmp_path, capsys):
    get, _ = fake_api({'weekly-update.yml': [run(6)]})
    out = tmp_path / 'data' / 'recent_runs.json'
    assert rr.main(['--repo', 'o/r', '--out', str(out)], get=get) == 0
    data = json.loads(out.read_text(encoding='utf-8'))
    assert re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ', data['read_utc'])
    assert [r['workflow'] for r in data['runs']] == ['Weekly update']


def test_a_failed_read_writes_nothing_and_does_not_fail_the_build(tmp_path, capsys):
    def get(url, token=None):
        raise OSError('rate limited')
    out = tmp_path / 'recent_runs.json'
    assert rr.main(['--repo', 'o/r', '--out', str(out)], get=get) == 0
    assert not out.exists()
    assert 'not read' in capsys.readouterr().out


def test_the_file_is_never_committed():
    assert 'data/recent_runs.json' in (REPO / '.gitignore').read_text(encoding='utf-8').splitlines()


def test_the_deploy_reads_the_runs_before_it_builds_and_may_read_actions():
    text = (WORKFLOWS / 'deploy-pages.yml').read_text(encoding='utf-8')
    read = text.index('python -m src.pipeline.recent_runs')
    build = text.index('python -m src.pipeline.generate_dashboard')
    assert read < build
    assert '--out data/recent_runs.json' in text
    assert re.search(r'^permissions:\n(?:  .*\n)*  actions: read\n', text, re.M)


# --- the generator --------------------------------------------------------------

def test_no_file_is_null_not_an_empty_list(tmp_path):
    assert gd.load_recent_runs(tmp_path / 'recent_runs.json') is None


def test_a_file_is_read_as_written(tmp_path):
    p = tmp_path / 'recent_runs.json'
    p.write_text(json.dumps({'read_utc': 't', 'runs': []}), encoding='utf-8')
    assert gd.load_recent_runs(p) == {'read_utc': 't', 'runs': []}


# --- the page -------------------------------------------------------------------

def function_source(src, name):
    m = re.search(r'function ' + name + r'\(.*?\n\}\n', src, re.S)
    assert m, f'{name} is not findable -- re-anchor this guard'
    return m.group(0)


def const_block(src, name):
    m = re.search(r'^const ' + name + r' = .*?;\n', src, re.M | re.S)
    assert m, f'{name} is not findable -- re-anchor this guard'
    return m.group(0)


def render(payload):
    """renderRecentRuns() in node over the shipped template, with `payload`
    as recentRuns; returns the HTML it wrote."""
    if not NODE:
        pytest.skip('node not available')
    src = JOINED_TEMPLATE.read_text(encoding='utf-8')
    js = (const_block(src, 'STATE_KINDS') + function_source(src, 'stateHtml') +
          function_source(src, 'escapeHtml') + const_block(src, 'RUN_RESULTS') +
          function_source(src, 'runResultText') + function_source(src, 'runTriggerText') +
          function_source(src, 'runStartedText') + function_source(src, 'renderRecentRuns') +
          f'const recentRuns = {json.dumps(payload)};'
          'const el = {innerHTML: ""}; const document = {getElementById: () => el};'
          'renderRecentRuns(); process.stdout.write(el.innerHTML);')
    r = subprocess.run([NODE, '-e', js], capture_output=True, text=True, encoding='utf-8')
    assert r.returncode == 0, r.stderr[-800:]
    return r.stdout


ROWS = [rr.row(run(4, minute=47, event='workflow_dispatch'), 'Weekend refresh'),
        rr.row(run(3, conclusion='failure'), 'Nightly data check'),
        rr.row(run(2, status='in_progress', conclusion=None), 'Weekly <update>')]


def test_null_says_the_history_was_not_read_rather_than_showing_an_empty_table():
    out = render(None)
    assert 'was not read for this build' in out and '<table' not in out


def test_each_run_is_a_row_with_its_result_linked_to_the_run():
    out = render({'read_utc': '2026-10-04T23:09:39Z', 'runs': ROWS})
    assert out.count('<tr>') == 1 + len(ROWS)
    assert 'href="https://github.com/o/r/actions/runs/4"' in out and '>Finished</a>' in out
    assert '>Failed</a>' in out and '>Running</a>' in out
    assert '1 failed' in out


def test_a_start_reads_in_eastern_time_and_says_who_started_it():
    out = render({'read_utc': 't', 'runs': ROWS})
    assert 'Oct 4, 5:47 PM' in out and 'Times are Eastern' in out
    assert 'Requested' in out and 'GitHub&#39;s timer' in out


def test_a_job_name_is_escaped():
    out = render({'read_utc': 't', 'runs': ROWS})
    assert 'Weekly &lt;update&gt;' in out and 'Weekly <update>' not in out


def test_no_failures_says_so():
    out = render({'read_utc': 't', 'runs': ROWS[:1]})
    assert 'none failed' in out
