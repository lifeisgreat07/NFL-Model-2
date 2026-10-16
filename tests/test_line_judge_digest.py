"""
Stage 44 item 5: Line Judge's weekly digest (src/core/line_judge_digest.py,
.github/workflows/line-judge-digest.yml).

What is held here:
  - the week counted is the last whole Monday-to-Sunday (UTC) before the run;
  - a run's verdict comes from its line-judge job alone: passed is right,
    failed is a finding, skipped or cancelled or absent is not judged, and a
    job still running is left out;
  - the digest's first line is the count, a line per judged workflow follows,
    and every run with findings is linked; a week with nothing judged says so
    first, in bold;
  - the digest is posted to the one standing issue, and --dry-run posts
    nothing;
  - the workflow runs it on Monday after the Weekend refresh's last slot,
    with the token reads and issue writes it needs and nothing more.

Run with: pytest tests/test_line_judge_digest.py -v
"""
import re
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from src.core import line_judge_digest as dg
from src.core.missed_dispatch import NOT_DISPATCHED
from src.core.start_delay import Cron, crons

WORKFLOW = Path(__file__).resolve().parents[1] / '.github' / 'workflows' / 'line-judge-digest.yml'
MON, SUN = date(2026, 10, 5), date(2026, 10, 11)


def job(conclusion, status='completed', name='line-judge'):
    return {'name': name, 'status': status, 'conclusion': conclusion}


@pytest.mark.parametrize('now', ['2026-10-12T08:23:00', '2026-10-12T00:00:00', '2026-10-18T23:59:00'])
def test_the_week_counted_is_the_last_whole_one(now):
    assert dg.last_week(datetime.fromisoformat(now).replace(tzinfo=UTC)) == (MON, SUN)


@pytest.mark.parametrize('jobs, want', [
    ([job('success', name='daily'), job('success')], 'right'),
    ([job('success', name='daily'), job('failure')], 'found'),
    ([job('failure', name='daily'), job('skipped')], 'not judged'),
    ([job('cancelled')], 'not judged'),
    ([job('success', name='daily')], 'not judged'),
    ([job(None, status='in_progress')], 'running'),
])
def test_a_runs_verdict_is_its_line_judge_job(jobs, want):
    assert dg.verdict(jobs) == want


def fake_api(runs_by_workflow, jobs_by_run):
    asked = []

    def api(path):
        asked.append(path)
        m = re.search(r'/actions/workflows/([^/]+)/runs\?', path)
        if m:
            return [{'id': r, 'html_url': f'https://example.test/runs/{r}'} for r in runs_by_workflow.get(m.group(1), [])]
        m = re.search(r'/actions/runs/(\d+)/jobs', path)
        return jobs_by_run[int(m.group(1))]
    return api, asked


def test_runs_are_counted_by_verdict_and_findings_linked():
    api, asked = fake_api({'nhl-daily.yml': [1, 2, 3, 4]},
                          {1: [job('success')], 2: [job('failure')], 3: [job('skipped')],
                           4: [job(None, status='in_progress')]})
    t = dg.tally('nhl-daily.yml', MON, SUN, api)
    assert (t.right, t.found, t.not_judged, t.judged) == (1, ['https://example.test/runs/2'], 1, 2)
    assert 'created=2026-10-05..2026-10-11' in asked[0]
    assert asked[0].startswith('repos/{owner}/{repo}/actions/workflows/nhl-daily.yml/runs')


def test_the_digest_leads_with_the_count_and_links_every_finding():
    tallies = {'nhl-daily.yml': dg.Tally(13, ['https://example.test/runs/2'], 1),
               'nba-daily.yml': dg.Tally(14, [], 0),
               'nfl-weekly-update.yml': dg.Tally(2, [], 0),
               'nfl-weekend-refresh.yml': dg.Tally(5, [], 1)}
    text = dg.digest(tallies, MON, SUN)
    lines = text.splitlines()
    assert lines[0] == ('Line Judge, Mon 2026-10-05 to Sun 2026-10-11: 35 runs judged, '
                        '34 right, 1 with findings; 2 not judged.')
    assert '- NHL daily run: 14 runs judged, 13 right, 1 with findings, 1 not judged.' in lines
    assert '- NFL Weekly update: 2 runs judged, 2 right, 0 with findings, 0 not judged.' in lines
    assert lines[-1] == '- https://example.test/runs/2'
    assert 'No run was judged' not in text


def test_a_week_with_nothing_judged_says_so_first():
    text = dg.digest({}, MON, SUN)
    assert text.startswith('**No run was judged this week.**')
    assert '0 runs judged, 0 right, 0 with findings; 0 not judged.' in text
    assert 'Runs with findings' not in text


def test_one_run_is_not_called_runs():
    assert '1 run judged' in dg.digest({'nhl-daily.yml': dg.Tally(1, [], 0)}, MON, SUN)


def test_the_digest_is_posted_to_the_standing_issue(capsys):
    api, _ = fake_api({}, {})
    posted = []
    now = datetime(2026, 10, 12, 8, 23, tzinfo=UTC)
    assert dg.main([], now=now, api=api, post=lambda title, body: posted.append((title, body))) == 0
    assert [t for t, _ in posted] == ['Line Judge weekly digest']
    assert posted[0][1].startswith('**No run was judged this week.**')
    posted.clear()
    assert dg.main(['--dry-run'], now=now, api=api, post=lambda *a: posted.append(a)) == 0
    assert posted == [] and 'Line Judge, Mon 2026-10-05' in capsys.readouterr().out


def test_every_judged_workflow_has_a_line_judge_job():
    for wf in dg.JUDGED:
        text = (WORKFLOW.parent / wf).read_text(encoding='utf-8')
        assert re.search(rf'^  {dg.JOB}:$', text, re.M), wf


def test_the_workflow_runs_monday_after_the_last_refresh_slot():
    text = WORKFLOW.read_text(encoding='utf-8')
    assert crons(text) == ['23 8 * * 1']
    assert Cron('23 8 * * 1').matches(datetime(2026, 10, 12, 8, 23, tzinfo=UTC))
    refresh = crons((WORKFLOW.parent / 'nfl-weekend-refresh.yml').read_text(encoding='utf-8'))
    monday = [c for c in refresh if c.endswith(' * * 1')]
    assert monday and all((int(c.split()[1]), int(c.split()[0])) < (8, 23) for c in monday)
    assert 'line-judge-digest.yml' in NOT_DISPATCHED


def test_the_workflow_posts_through_the_module_with_only_what_it_needs():
    text = WORKFLOW.read_text(encoding='utf-8')
    assert 'run: python -m src.core.line_judge_digest\n' in text
    block = re.search(r'\npermissions:\n((?:  .*\n)+)', text).group(1)
    assert sorted(block.split()) == sorted(['contents:', 'read', 'issues:', 'write', 'actions:', 'read'])
    assert 'contents: write' not in text and 'claude-code-action' not in text
