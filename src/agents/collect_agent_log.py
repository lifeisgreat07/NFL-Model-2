"""
Collect Booth's audits into data/agent_log.json, for the dashboard to render.

    python -m src.agents.collect_agent_log --comments comments.json
    gh api repos/:owner/:repo/issues/comments --paginate | \
        python -m src.agents.collect_agent_log --comments -

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

Only Booth's own accounts count (BOOTH_ACCOUNTS below). That is not a
selection of audits, which rule 1 forbids; it is the definition of one, so a
comment that merely copies Booth's heading cannot put a row on the page.

The counts come from the verdict block, never from the prose summary -- the
block is what src/agents/booth_verdict.py can validate, and cross_check() catches a
report whose two halves disagree.
"""
import argparse
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).parents[2]

from src.agents import booth_verdict as bv

OUT = REPO / 'data' / 'agent_log.json'

#: A comment is one of Booth's audits if it opens with the protocol's heading.
AUDIT_RE = re.compile(r'^##\s+Booth Audit:\s*PR\s*#(\d+)', re.M)

#: The header line PR #29 introduced. Its absence dates a report.
HEAD_RE = re.compile(r'^Head commit audited:\s*`?([0-9a-f]{7,40})`?', re.M)


def _pr_number(comment: dict[str, Any]) -> int | None:
    """The PR a comment belongs to, from its own heading or its URL."""
    m = AUDIT_RE.search(comment.get('body') or '')
    if m:
        return int(m.group(1))
    m = re.search(r'/(?:pull|issues)/(\d+)', comment.get('html_url') or '')
    return int(m.group(1)) if m else None


#: The accounts Booth posts as, and how a comment's author is read. Both live
#: in booth_verdict.py, which the audit workflow copies out of the checkout
#: alongside the report check; see the note there. Before the 2026-09-28
#: audit a comment from any account became a row on the page.
BOOTH_ACCOUNTS = bv.BOOTH_ACCOUNTS
author = bv.author


def is_audit(comment: dict[str, Any]) -> bool:
    """A comment is an audit only if it has Booth's heading AND was posted by
    one of Booth's accounts. A comment with no author recorded is not one:
    failing closed here means a collector fed the wrong shape logs nothing,
    which the page reports, rather than logging anyone."""
    body = comment.get('body') or ''
    return bool(AUDIT_RE.search(body)) and author(comment) in BOOTH_ACCOUNTS


def parse_audit(comment: dict[str, Any]) -> dict[str, Any]:
    """One comment -> one row. Never raises on a malformed block.

    A report whose block cannot be parsed is recorded with the reason. Dropping
    it would understate how often the format has been wrong, which is precisely
    the kind of thing this log should be able to show.
    """
    body = comment['body']
    row: dict[str, Any] = {
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


def mark_superseded(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Within a pull request, only the newest audit counts.

    Sorted by posted_utc so the rule does not depend on the order comments
    arrive in. Ties keep document order, which matches how GitHub returns them.
    """
    by_pr: dict[Any, list[int]] = {}
    for i, row in enumerate(rows):
        by_pr.setdefault(row['pr'], []).append(i)
    for indices in by_pr.values():
        newest = max(indices, key=lambda i: (rows[i]['posted_utc'] or '', i))
        for i in indices:
            rows[i]['superseded'] = i != newest
    return rows


def summarise(rows: list[dict[str, Any]]) -> dict[str, int]:
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


#: Stage 90 item 3: how many of the agents' latest outputs the page lists.
RECENT = 16
#: Spotter's comments open with this marker (src/agents/spotter_comment.py).
SPOTTER_MARKER = '<!-- spotter-comment -->'
#: Line Judge's weekly digest line (src/core/line_judge_digest.py) and its diagnosis heading.
DIGEST_RE = re.compile(r'^Line Judge, \w{3} \d{4}-\d\d-\d\d to \w{3} \d{4}-\d\d-\d\d: .*$', re.M)
DIAGNOSIS = "**Line Judge's diagnosis**"


def _first_sentence(text: str, limit: int = 200) -> str:
    """The first sentence of `text`, cut at `limit` characters with an ellipsis."""
    text = ' '.join(text.split())
    m = re.match(r'(.+?[.!?])(?:\s|$)', text)
    s = m.group(1) if m else text
    return s if len(s) <= limit else s[:limit - 1].rstrip() + '\u2026'


def agent_entry(comment: dict[str, Any]) -> dict[str, Any] | None:
    """One comment by Spotter or Line Judge as a line of the agents' record, or None.
    Only this repository's bot accounts count, as for Booth (is_audit)."""
    body = comment.get('body') or ''
    if author(comment) not in BOOTH_ACCOUNTS:
        return None
    base = {'pr': None, 'url': comment.get('html_url'), 'when': comment.get('created_at')}
    if body.startswith(SPOTTER_MARKER):
        reading = body.split('### Reading', 1)[1] if '### Reading' in body else ''
        return base | {'agent': 'Spotter', 'pr': _pr_number(comment),
                       'says': _first_sentence(reading) or 'posted the pages this change can alter'}
    m = DIGEST_RE.search(body)
    if m:
        return base | {'agent': 'Line Judge', 'says': m.group(0)}
    if body.startswith(DIAGNOSIS):
        rest = body[len(DIAGNOSIS):].split('\n', 1)[1] if '\n' in body else ''
        return base | {'agent': 'Line Judge', 'says': 'Diagnosis: ' + (_first_sentence(rest) or 'none posted')}
    return None


def scout_entry(run: dict[str, Any]) -> dict[str, Any] | None:
    """One Scout pre-flight run as a line of the record; Scout writes its findings
    to its run, not to a comment, so the link is the run."""
    prs = run.get('pull_requests') or []
    if run.get('conclusion') not in ('success', 'failure'):
        return None
    return {'agent': 'Scout', 'pr': prs[0].get('number') if prs else None, 'url': run.get('html_url'),
            'when': run.get('created_at'),
            'says': ('found nothing to fix in the description' if run['conclusion'] == 'success'
                     else 'found the description needs fixing before an audit')}


def recent(rows: list[dict[str, Any]], comments: list[dict[str, Any]],
           scout_runs: list[dict[str, Any]] | None, n: int = RECENT) -> list[dict[str, Any]]:
    """The four agents' latest outputs, newest first, each linked (Stage 90 item 3).
    Booth's are its counted audits, so a superseded run is not listed twice."""
    out = [{'agent': 'Booth', 'pr': r['pr'], 'url': r['url'], 'when': r['posted_utc'],
            'says': (f"{r['overall']}: {r['confirmed']} of {r['claims']} claims confirmed, "
                     f"{r['discrepancies']} wrong, {r['unverifiable']} unverifiable"
                     if r['has_verdict_block'] else 'an audit in prose, from before the verdict block')}
           for r in rows if not r['superseded']]
    out += [e for e in (agent_entry(c) for c in comments) if e]
    out += [e for e in (scout_entry(r) for r in scout_runs or []) if e]
    out.sort(key=lambda e: e['when'] or '', reverse=True)
    return out[:n]


def build(comments: list[dict[str, Any]], scout_runs: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    rows = [parse_audit(c) for c in comments if is_audit(c)]
    rows.sort(key=lambda r: (r['posted_utc'] or '', r['pr'] or 0))
    mark_superseded(rows)
    return {
        'generated_utc': datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'note': (
            'Every audit Booth has posted. Superseded runs are kept and '
            'flagged rather than deleted -- only the newest audit per pull '
            'request counts toward the totals. Reports predating the '
            'machine-readable verdict block are recorded as such.'
        ),
        'summary': summarise(rows),
        'audits': rows,
        'recent': recent(rows, comments, scout_runs),
    }


def unchanged(out: Path, payload: dict[str, Any]) -> bool:
    """True when the file at `out` holds this payload but for generated_utc."""
    try:
        old = json.loads(out.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return False
    def strip(d: dict[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in d.items() if k != 'generated_utc'}
    return isinstance(old, dict) and strip(old) == strip(payload)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument('--comments', required=True,
                    help="JSON array of issue comments, or - for stdin")
    ap.add_argument('--scout', default=None,
                    help='JSON array of Scout pre-flight workflow runs (Stage 90 item 3)')
    ap.add_argument('--out', default=str(OUT))
    args = ap.parse_args(argv)

    raw = sys.stdin.read() if args.comments == '-' else \
        Path(args.comments).read_text(encoding='utf-8')
    comments = json.loads(raw)

    scout = json.loads(Path(args.scout).read_text(encoding='utf-8')) if args.scout else None
    payload = build(comments, scout)
    out = Path(args.out)
    if unchanged(out, payload):
        # Stage 68 item 29 (the 2026-10-09 audit's E34): a run whose audits are the
        # ones already recorded rewrote the file anyway, because
        # generated_utc always moves, and the workflow committed it.
        print(f'{out} unchanged apart from its timestamp; left as it was')
        return 0
    out.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')

    s = payload['summary']
    print('{} audits across {} pull requests ({} superseded)'.format(
        s['audits_total'], s['pull_requests_audited'], s['audits_superseded']))
    print('{} claims re-executed, {} discrepancies on {} pull requests'.format(
        s['claims_checked'], s['discrepancies_found'],
        s['pull_requests_with_a_discrepancy']))
    print(f'written to {args.out}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
