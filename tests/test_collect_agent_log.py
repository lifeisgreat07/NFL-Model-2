"""
Tests for src/agents/collect_agent_log.py.

A log of your own verifier is the easiest artifact in this repository to
quietly flatter yourself with, so most of these are about what the collector
must NOT do: drop a boring audit, count a superseded one, or report zero
findings for a report it could not parse.

Run with: pytest tests/test_collect_agent_log.py -v
"""
import json
from pathlib import Path

from src.agents import collect_agent_log as cal  # noqa: E402


def _block(claims, overall='SAFE TO MERGE', head='abc1234', pr=1):
    return json.dumps({'pr': pr, 'head': head, 'claims': claims,
                       'overall': overall}, indent=2)


def _audit(pr, when, claims=None, overall='SAFE TO MERGE', head='abc1234',
           block=True, body_extra='', login='claude[bot]'):
    body = f'## Booth Audit: PR #{pr}\n\n'
    if head:
        body += f'Head commit audited: `{head}`\n'
    body += f'\nClaims checked: {len(claims or [])}\n'
    body += f'\n### Overall verdict\n{overall}\n'
    body += body_extra
    if block:
        body += f'\n```booth-verdict\n{_block(claims or [], overall, head, pr)}\n```\n'
    return {
        'body': body,
        'html_url': f'https://github.com/o/r/pull/{pr}#issuecomment-{when}',
        'created_at': when,
        'user': {'login': login},
    }


CONFIRMED = [{'id': 1, 'verdict': 'CONFIRMED', 'implicates': []}]
FOUND = [
    {'id': 1, 'verdict': 'CONFIRMED', 'implicates': []},
    {'id': 2, 'verdict': 'DISCREPANCY', 'implicates': ['src/thing.py']},
]


# --- what counts as an audit ------------------------------------------------

def test_ordinary_comments_are_not_audits():
    assert not cal.is_audit({'body': 'looks good to me', 'html_url': ''})
    assert not cal.is_audit({'body': '## Some other heading', 'html_url': ''})


def test_a_booth_report_is_an_audit():
    assert cal.is_audit(_audit(7, '2026-09-07T10:00:00Z', CONFIRMED))


# --- only Booth's accounts (Stage 23) -----------------------------------------

def test_a_report_from_booth_on_the_workflow_token_is_an_audit():
    """Since Booth runs on GITHUB_TOKEN its reports are posted by
    github-actions[bot]; claude[bot] posted every one before that."""
    assert cal.is_audit(_audit(7, '2026-09-29T10:00:00Z', CONFIRMED,
                               login='github-actions[bot]'))
    assert cal.is_audit(_audit(7, '2026-09-07T10:00:00Z', CONFIRMED,
                               login='claude[bot]'))


def test_a_copied_heading_from_anyone_else_is_not_an_audit():
    """Anyone can post a comment that opens with Booth's heading. Before
    Stage 23 such a comment became a row on the page, SAFE TO MERGE and all."""
    forged = _audit(7, '2026-09-29T10:00:00Z', CONFIRMED, login='someone')
    assert not cal.is_audit(forged)
    real = _audit(8, '2026-09-29T10:00:00Z', CONFIRMED)
    assert [r['pr'] for r in cal.build([forged, real])['audits']] == [8]


def test_a_comment_with_no_author_is_not_an_audit():
    c = _audit(7, '2026-09-29T10:00:00Z', CONFIRMED)
    del c['user']
    assert not cal.is_audit(c)


def test_the_workflow_passes_each_comment_author_to_the_collector():
    """The workflow's jq decides which fields reach the collector. Without the
    login, every comment has no author and the log is empty."""
    wf = (Path(__file__).parent.parent / '.github' / 'workflows' /
          'collect-agent-log.yml').read_text(encoding='utf-8')
    jq = [l for l in wf.splitlines() if '--jq' in l]
    assert len(jq) == 1, jq
    assert 'user: {login: .user.login}' in jq[0], jq[0]


# --- nothing is dropped -----------------------------------------------------

def test_a_clean_audit_is_kept():
    """Audits finding nothing are the majority. A log keeping only the
    dramatic ones would describe a verifier that finds something every time."""
    out = cal.build([_audit(7, '2026-09-07T10:00:00Z', CONFIRMED)])
    assert out['summary']['audits_total'] == 1
    assert out['audits'][0]['discrepancies'] == 0


def test_a_report_without_a_verdict_block_is_recorded_not_dropped():
    """Reports predating PR #31 are older, not broken."""
    out = cal.build([_audit(5, '2026-09-06T10:00:00Z', block=False)])
    row = out['audits'][0]
    assert row['has_verdict_block'] is False
    assert row['discrepancies'] is None, (
        'a report with no block must not report zero findings; that would be '
        'indistinguishable from a clean audit'
    )
    assert out['summary']['audits_without_a_verdict_block'] == 1


def test_a_malformed_block_is_recorded_with_its_reason():
    c = _audit(9, '2026-09-07T10:00:00Z', CONFIRMED)
    c['body'] = c['body'].replace('"overall"', '"overall" "broken"')
    out = cal.build([c])
    row = out['audits'][0]
    assert row['block_error'], 'a malformed block was silently discarded'
    assert row['has_verdict_block'] is False


def test_a_report_predating_the_head_line_is_flagged():
    """PR #29 added `Head commit audited`. Its absence dates a report."""
    out = cal.build([_audit(5, '2026-09-06T10:00:00Z', CONFIRMED, head=None)])
    assert out['audits'][0]['records_head'] is False


# --- superseded audits ------------------------------------------------------

def test_only_the_newest_audit_of_a_pull_request_counts():
    """PR #28 carried five audits; three read replaced descriptions.

    Summing them would report five discrepancies where one defect was found
    repeatedly -- an inflated number in the one artifact that exists to be
    honest about this project's own verification.
    """
    out = cal.build([
        _audit(28, '2026-09-07T04:35:00Z', FOUND),
        _audit(28, '2026-09-07T04:46:00Z', FOUND),
        _audit(28, '2026-09-07T15:36:00Z', CONFIRMED),
    ])
    assert out['summary']['audits_total'] == 3
    assert out['summary']['audits_superseded'] == 2
    assert out['summary']['discrepancies_found'] == 0, (
        'superseded audits were counted; the newest run found nothing'
    )


def test_superseded_audits_are_kept_and_flagged():
    """The stale runs are themselves a finding about the harness."""
    out = cal.build([
        _audit(28, '2026-09-07T04:35:00Z', FOUND),
        _audit(28, '2026-09-07T15:36:00Z', CONFIRMED),
    ])
    assert len(out['audits']) == 2
    assert [r['superseded'] for r in out['audits']] == [True, False]


def test_supersession_does_not_depend_on_input_order():
    """Exercises mark_superseded DIRECTLY, on rows that are not sorted.

    Routing this through build() proved nothing: build() sorts by timestamp
    first, so picking "the last row" and "the newest row" give the same answer
    and the ordering logic is never tested. The mutation corpus caught that --
    replacing the timestamp key with indices[-1] SURVIVED.

    mark_superseded is a public function and GitHub does not promise comment
    order, so it must be correct on input nobody sorted.
    """
    rows = [
        {'pr': 28, 'posted_utc': '2026-09-07T15:36:00Z', 'superseded': False},
        {'pr': 28, 'posted_utc': '2026-09-07T04:35:00Z', 'superseded': False},
    ]
    cal.mark_superseded(rows)
    assert rows[0]['superseded'] is False, (
        'the newest audit was marked superseded because it happened to come '
        'first in the input'
    )
    assert rows[1]['superseded'] is True


def test_supersession_is_stable_through_the_whole_pipeline():
    newest = _audit(28, '2026-09-07T15:36:00Z', CONFIRMED)
    oldest = _audit(28, '2026-09-07T04:35:00Z', FOUND)
    for order in ([newest, oldest], [oldest, newest]):
        out = cal.build(list(order))
        current = [r for r in out['audits'] if not r['superseded']]
        assert len(current) == 1
        assert current[0]['posted_utc'] == '2026-09-07T15:36:00Z'


def test_audits_of_different_pull_requests_do_not_supersede_each_other():
    out = cal.build([
        _audit(28, '2026-09-07T04:35:00Z', FOUND),
        _audit(31, '2026-09-07T16:24:00Z', CONFIRMED),
    ])
    assert out['summary']['audits_superseded'] == 0
    assert out['summary']['discrepancies_found'] == 1


# --- the numbers ------------------------------------------------------------

def test_totals_come_from_the_block_not_the_prose():
    """The block is what booth_verdict can validate; the prose is not."""
    c = _audit(7, '2026-09-07T10:00:00Z', FOUND)
    c['body'] = c['body'].replace('Claims checked: 2', 'Claims checked: 99')
    out = cal.build([c])
    assert out['audits'][0]['claims'] == 2


def test_a_report_disagreeing_with_itself_is_counted():
    """cross_check catches a block that contradicts its own prose summary."""
    c = _audit(7, '2026-09-07T10:00:00Z', FOUND)
    c['body'] = c['body'].replace('Claims checked: 2', 'Claims checked: 5')
    out = cal.build([c])
    assert out['audits'][0]['inconsistencies']
    assert out['summary']['reports_disagreeing_with_themselves'] == 1


def test_implicated_paths_come_only_from_discrepancies():
    out = cal.build([_audit(7, '2026-09-07T10:00:00Z', FOUND)])
    assert out['audits'][0]['implicated'] == ['src/thing.py']


def test_pull_requests_with_a_discrepancy_counts_prs_not_findings():
    """Two findings on one pull request is one pull request."""
    claims = [
        {'id': 1, 'verdict': 'DISCREPANCY', 'implicates': ['a.py']},
        {'id': 2, 'verdict': 'DISCREPANCY', 'implicates': ['b.py']},
    ]
    out = cal.build([_audit(7, '2026-09-07T10:00:00Z', claims)])
    assert out['summary']['discrepancies_found'] == 2
    assert out['summary']['pull_requests_with_a_discrepancy'] == 1


def test_the_output_carries_its_own_caveat():
    """Anyone reading the file should learn how it counts without asking."""
    out = cal.build([_audit(7, '2026-09-07T10:00:00Z', CONFIRMED)])
    assert 'superseded' in out['note'].lower()
    assert out['generated_utc'].endswith('Z')
