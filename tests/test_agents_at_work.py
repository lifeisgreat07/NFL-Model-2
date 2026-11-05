"""Stage 90 item 3: the agents at work.

"Checking the AI's work" counted Booth's audits and nothing else, though four
agents check this project: Booth audits each change, Scout reads its
description first, Spotter photographs the pages it can alter, and Line Judge
reads the unattended runs. src/agents/collect_agent_log.py now also records
the four agents' latest outputs (`recent`), each with the link to where it was
posted, and the page lists them.

Run with: pytest tests/test_agents_at_work.py -v
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from src.agents import collect_agent_log as cal
from src.core.template_parts import JOINED_TEMPLATE
from tests.js_source import function_source

ROOT = Path(__file__).resolve().parents[1]
BOT = {'login': 'github-actions[bot]'}
URL = 'https://github.com/lifeisgreat07/NFL-Model-2'


def audit(pr, when, overall='SAFE TO MERGE'):
    block = json.dumps({'pr': pr, 'head': 'abcdef1', 'claims': [{'id': 1, 'verdict': 'CONFIRMED', 'implicates': []}],
                        'overall': overall})
    body = (f'## Booth Audit: PR #{pr}\n\nHead commit audited: abcdef1\n\nClaims checked: 1\nConfirmed: 1\n'
            f'Discrepancies: 0\nUnverifiable: 0\n\n### Overall verdict\n{overall}\n\n```booth-verdict\n{block}\n```\n')
    return {'body': body, 'html_url': f'{URL}/pull/{pr}#issuecomment-{pr}{when[-2:]}', 'created_at': when, 'user': BOT}


SPOTTER = {'body': '<!-- spotter-comment -->\n## Spotter: the pages this change can alter\n\nHead `abc`.\n\n'
                   '### Reading\n\nThe NBA rows lose their price label at 390 px. The rest match.\n',
           'html_url': f'{URL}/pull/620#issuecomment-9', 'created_at': '2026-11-05T08:04:25Z', 'user': BOT}
DIGEST = {'body': 'Line Judge, Mon 2026-10-26 to Sun 2026-11-01: 14 runs judged, 13 right, 1 with findings; '
                  '0 not judged.\n\n- NFL weekly update: 2 runs judged\n',
          'html_url': f'{URL}/issues/400#issuecomment-1', 'created_at': '2026-11-02T09:00:00Z', 'user': BOT}
DIAGNOSIS = {'body': "**Line Judge's diagnosis** -- an agent's reading of the finding above, not a check.\n\n"
                     'The odds feed answered with an empty list. Nothing else failed.\n\nRun: x\n',
             'html_url': f'{URL}/issues/401#issuecomment-2', 'created_at': '2026-11-03T09:00:00Z', 'user': BOT}
SCOUT = [{'conclusion': 'success', 'html_url': f'{URL}/actions/runs/1', 'created_at': '2026-11-05T08:00:00Z',
          'pull_requests': [{'number': 620}]},
         {'conclusion': 'failure', 'html_url': f'{URL}/actions/runs/2', 'created_at': '2026-11-01T08:00:00Z',
          'pull_requests': [{'number': 600}]},
         {'conclusion': None, 'html_url': f'{URL}/actions/runs/3', 'created_at': '2026-11-05T09:00:00Z',
          'pull_requests': []}]


def test_all_four_agents_are_recorded_newest_first_each_with_its_link():
    comments = [audit(619, '2026-11-05T07:38:18Z', 'NEEDS HUMAN REVIEW'), audit(619, '2026-11-05T07:57:40Z'),
                SPOTTER, DIGEST, DIAGNOSIS]
    got = cal.build(comments, SCOUT)['recent']
    assert [(e['agent'], e['pr']) for e in got] == [
        ('Spotter', 620), ('Scout', 620), ('Booth', 619), ('Line Judge', None), ('Line Judge', None), ('Scout', 600)]
    booth = got[2]
    assert booth['says'] == 'SAFE TO MERGE: 1 of 1 claims confirmed, 0 wrong, 0 unverifiable', \
        'the superseded audit is not listed; the counted one is'
    assert got[0]['says'] == 'The NBA rows lose their price label at 390 px.'
    assert got[3]['says'] == 'Diagnosis: The odds feed answered with an empty list.'
    assert got[4]['says'].startswith('Line Judge, Mon 2026-10-26 to Sun 2026-11-01: 14 runs judged')
    assert got[1]['says'] == 'found nothing to fix in the description'
    assert got[5]['says'] == 'found the description needs fixing before an audit'
    assert all(e['url'].startswith(URL) for e in got)


def test_only_this_repositorys_bot_accounts_count():
    """As for Booth (is_audit): a person pasting an agent's heading puts nothing on the page."""
    fake = dict(SPOTTER, user={'login': 'someone'})
    assert cal.agent_entry(fake) is None and cal.agent_entry(dict(DIGEST, user={})) is None


def test_the_list_is_capped_and_a_run_in_progress_is_not_listed():
    many = [audit(500 + i, f'2026-10-{10 + i:02d}T00:00:00Z') for i in range(cal.RECENT + 5)]
    got = cal.build(many, SCOUT)['recent']
    assert len(got) == cal.RECENT
    assert f'{URL}/actions/runs/3' not in {e['url'] for e in got}


def test_without_scout_runs_the_others_are_still_listed():
    assert {e['agent'] for e in cal.build([SPOTTER, DIGEST])['recent']} == {'Spotter', 'Line Judge'}


def test_the_workflow_reads_scouts_runs_and_passes_them_on():
    wf = (ROOT / '.github' / 'workflows' / 'collect-agent-log.yml').read_text(encoding='utf-8')
    assert 'actions/workflows/scout-preflight.yml/runs' in wf
    assert 'python -m src.agents.collect_agent_log --comments comments.json --scout scout.json' in wf


@pytest.mark.skipif(shutil.which('node') is None, reason='node is not installed')
def test_the_page_lists_them_escaped_and_links_only_to_github():
    page = JOINED_TEMPLATE.read_text(encoding='utf-8')
    js = (function_source(page, 'escapeHtml') + 'const AGENT_ROLES = {Booth: "a", Scout: "b", '
          'Spotter: "c", "Line Judge": "d"};\n' + function_source(page, 'agentsAtWork')
          + 'process.stdout.write(JSON.stringify([agentsAtWork(' + json.dumps([
              {'agent': 'Booth', 'pr': 619, 'when': '2026-11-05T07:57:40Z', 'url': f'{URL}/pull/619#c',
               'says': 'SAFE <b>'},
              {'agent': 'Spotter', 'pr': 620, 'when': '2026-11-05T08:04:25Z', 'url': 'javascript:alert(1)',
               'says': 'a reading'}]) + '), agentsAtWork([]), agentsAtWork(undefined)]));')
    out = json.loads(subprocess.run(['node', '-e', js], capture_output=True, text=True, check=True).stdout)
    html = out[0]
    assert '<h3>The agents at work</h3>' in html
    assert f'<b>Booth</b> on #619, 2026-11-05: <a href="{URL}/pull/619#c" rel="noopener">SAFE &lt;b&gt;</a>' in html
    assert '<b>Spotter</b> on #620, 2026-11-05: a reading</li>' in html and 'javascript:' not in html
    assert out[1] == '' and out[2] == '', 'no list at all when nothing was collected'
