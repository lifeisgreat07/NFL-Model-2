"""
Collect Booth's audits into data/agent_log.json, for the dashboard to render.

    python src/collect_agent_log.py --comments comments.json
    gh api repos/:owner/:repo/issues/comments --paginate | \
        python src/collect_agent_log.py --comments -

Every audit Booth has ever posted becomes a row. The dashboard then shows what
this project has actually been doing: an independent verifier re-executing
claims, and what it found.

THREE HONESTY RULES, because a log of your own verifier is the easiest thing in
this repository to quietly flatter yourself with.

1. NOTHING IS DROPPED. Audits where Booth confirmed everything are the majority
   and they stay in. A log that kept only the dramatic findings would report a
   verifier that finds something every time, which is both false and the exact
   shape of the selection bias this project's methodology section exists to
   prevent.

2. SUPERSEDED AUDITS ARE MARKED, NOT DELETED, AND NOT COUNTED. PR #28 carries
   five audits; three read descriptions that had already been replaced. Summing
   their findings would report five discrepancies where there was one defect
   found repeatedly. Only the newest audit per pull request counts toward
   totals -- the rest stay visible, flagged, because "Booth reported against a
   stale body three times" is itself a real finding about the harness, and
   deleting the evidence for it would be the second mistake.

3. AUDITS WITHOUT A MACHINE-READABLE VERDICT ARE RECORDED AS SUCH. The
   booth-verdict block arrived in PR #31. Earlier reports are prose only. They
   are not failures and not omissions; they are older, and the log says so
   rather than silently reporting zero findings for them.

The counts come from the verdict block, never from the prose summary -- the
block is what src/booth_verdict.py can validate, and cross_check() catches a
report whose two halves disagree.
"""
import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO / 'src'))

import booth_verdict as bv  # noqa: E402

OUT = REPO / 'data' / 'agent_log.json'

#: A comment is one of Booth's audits if it opens with the protocol's heading.
AUDIT_RE = re.compile(r'^##\s+Booth Audit:\s*PR\s*#(\d+)', re.M)

#: The header line PR #29 introduced. Its absence dates a report.
HEAD_RE = re.compile(r'^Head commit audited:\s*`?([0-9a-f]{7,40})`?', re.M)


def _pr_number(comment):
    """The PR a comment belongs to, from its own heading or its URL."""
    m = AUDIT_RE.search(comment.get('body') or '')
    if m:
        return int(m.group(1))
    m = re.search(r'/(?:pull|issues)/(\d+)', comment.get('html_url') or '')
    return int(m.group(1)) if m else None


def is_audit(comment):
    body = comment.get('body') or ''
    return bool(AUDIT_RE.search(body))


def parse_audit(comment):
    """One comment -> one row. Never raises on a malformed block.

    A report whose block cannot be parsed is recorded with the reason. Dropping
    it would understate how often the format has been wrong, which is precisely
    the kind of thing this log should be able to show.
    """
    body = comment['body']
    row = {
        'pr': _pr_number(comment),
        'url': comment.get('html_url'),
        'posted_utc': comment.get('created_at'),
        'head': None,
        'records_head': False,
        'has_verdict_block': False,
        'block_error': None,
        'claims': None,
        'confirmed': None,
        'discrepancies': None,
        'unverifiable': None,
        'overall': None,
        'implicated': [],
        'inconsistencies': [],
        'superseded': False,
    }

    m = HEAD_RE.search(body)
    if m:
        row['head'] = m.group(1)[:7]
        row['records_head'] = True

    try:
        verdict = bv.extract(body)
    except bv.VerdictError as exc:
        row['block_error'] = str(exc)
        return row

    if verdict is None:
        return row

    row['has_verdict_block'] = True
    row['overall'] = verdict['overall']
    row['head'] = row['head'] or verdict.get('head')
    tally = {v: 0 for v in bv.VERDICTS}
    for claim in verdict['claims']:
        tally[claim['verdict']] += 1
    row['claims'] = len(verdict['claims'])
    row['confirmed'] = tally['CONFIRMED']
    row['discrepancies'] = tally['DISCREPANCY']
    row['unverifiable'] = tally['UNVERIFIABLE']
    row['implicated'] = sorted(bv.implicated_paths(verdict))
    row['inconsistencies'] = bv.cross_check(body, verdict)
    return row


def mark_superseded(rows):
    """Within a pull request, only the newest audit counts.

    Sorted by posted_utc so the rule does not depend on the order comments
    arrive in. Ties keep document order, which matches how GitHub returns them.
    """
    by_pr = {}
    for i, row in enumerate(rows):
        by_pr.setdefault(row['pr'], []).append(i)
    for indices in by_pr.values():
        newest = max(indices, key=lambda i: (rows[i]['posted_utc'] or '', i))
        for i in indices:
            rows[i]['superseded'] = i != newest
    return rows


def summarise(rows):
    current = [r for r in rows if not r['superseded']]
    scored = [r for r in current if r['has_verdict_block']]
    return {
        'audits_total': len(rows),
        'audits_superseded': sum(r['superseded'] for r in rows),
        'pull_requests_audited': len({r['pr'] for r in rows if r['pr']}),
        'audits_without_a_verdict_block': sum(
            not r['has_verdict_block'] for r in current),
        'claims_checked': sum(r['claims'] or 0 for r in scored),
        'discrepancies_found': sum(r['discrepancies'] or 0 for r in scored),
        'unverifiable': sum(r['unverifiable'] or 0 for r in scored),
        'pull_requests_with_a_discrepancy': len({
            r['pr'] for r in scored if r['discrepancies']}),
        'reports_disagreeing_with_themselves': sum(
            bool(r['inconsistencies']) for r in scored),
    }


def build(comments):
    rows = [parse_audit(c) for c in comments if is_audit(c)]
    rows.sort(key=lambda r: (r['posted_utc'] or '', r['pr'] or 0))
    mark_superseded(rows)
    return {
        'generated_utc': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'note': (
            'Every audit Booth has posted. Superseded runs are kept and '
            'flagged rather than deleted -- only the newest audit per pull '
            'request counts toward the totals. Reports predating the '
            'machine-readable verdict block are recorded as such.'
        ),
        'summary': summarise(rows),
        'audits': rows,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument('--comments', required=True,
                    help="JSON array of issue comments, or - for stdin")
    ap.add_argument('--out', default=str(OUT))
    args = ap.parse_args(argv)

    raw = sys.stdin.read() if args.comments == '-' else \
        Path(args.comments).read_text(encoding='utf-8')
    comments = json.loads(raw)

    payload = build(comments)
    Path(args.out).write_text(
        json.dumps(payload, indent=2) + '\n', encoding='utf-8')

    s = payload['summary']
    print('{} audits across {} pull requests ({} superseded)'.format(
        s['audits_total'], s['pull_requests_audited'], s['audits_superseded']))
    print('{} claims re-executed, {} discrepancies on {} pull requests'.format(
        s['claims_checked'], s['discrepancies_found'],
        s['pull_requests_with_a_discrepancy']))
    print('written to {}'.format(args.out))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
