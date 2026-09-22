"""
Fail a Booth run that did not post a report for the commit it audited.

`booth-pr-audit.yml` exits 0 whenever the Claude Code action exits 0, and the
action exits 0 whether or not Booth ever reached `gh pr comment`. On PR #80
(2026-09-21) the first run reported Success in 3m55s and posted nothing; the
Checks tab showed it exactly the way it shows a clean audit. The workflow
asserted nothing about the one thing it exists to produce. This is that
assertion, run as the step after Booth.

What counts as "a report for this run" -- all four must hold for ONE comment:

  1. posted by a bot account. Booth posts through the action's app identity;
     a person quoting a report, or a Scout session commenting under Mark's
     login (PR #82 has one), must not satisfy the check on Booth's behalf.
  2. created at or after the moment this run started. An `edited` re-audit
     runs against the SAME head SHA as the audit before it, so without a time
     floor the previous run's report would satisfy this one forever.
  3. carrying a booth-verdict block that parses. BOOTH_PROTOCOL.md requires
     it, and src/collect_agent_log.py counts nothing without it -- a report
     with no block is invisible to the record even though a human can read it.
  4. whose `head` names the commit this run checked out. The protocol's own
     example writes a short SHA, so a prefix of at least seven characters
     counts; anything shorter is too ambiguous to be evidence.

The head SHA and the start time are recorded by the workflow in a step BEFORE
Booth runs, not read afterwards: Booth builds worktrees and may check out other
commits while auditing, so `git rev-parse HEAD` after the audit can name a
commit this run never audited.

Absence of a qualifying comment is a failure, and so is a comment that exists
but fails 3 or 4. The messages differ, because "Booth posted nothing" and
"Booth posted something the record cannot read" send you to different places.

Usage (as the workflow calls it):
    gh api repos/OWNER/REPO/issues/N/comments --paginate > comments.json
    python src/booth_report_posted.py comments.json HEAD_SHA STARTED_AT
Exit 0 with a one-line confirmation, or 1 with the reason.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from booth_verdict import VerdictError, extract  # noqa: E402

MIN_SHA_PREFIX = 7


def load_comments(text):
    """Parse `gh api --paginate` output, which is one JSON array PER PAGE.

    `--paginate` concatenates pages as `[...][...]`, which is not one JSON
    document. Reading it with json.loads fails on any PR with more than one
    page of comments -- i.e. only on the long-running PRs where a missed
    report is most likely. Decode array after array instead.
    """
    decoder = json.JSONDecoder()
    out, pos, text = [], 0, text.strip()
    while pos < len(text):
        chunk, end = decoder.raw_decode(text, pos)
        if not isinstance(chunk, list):
            raise ValueError(f"expected a JSON array of comments, got {type(chunk).__name__}")
        out.extend(chunk)
        pos = end
        while pos < len(text) and text[pos].isspace():
            pos += 1
    return out


def _parse_time(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc)


def head_matches(block_head, head_sha):
    block_head = (block_head or '').strip().lower()
    return len(block_head) >= MIN_SHA_PREFIX and head_sha.lower().startswith(block_head)


def check(comments, head_sha, started_at):
    """Return (ok, message). Pure: no I/O, so the rules are testable directly."""
    if len(head_sha) < 40:
        return False, f"head SHA {head_sha!r} is not a full SHA; the workflow must record `git rev-parse HEAD`"
    floor = _parse_time(started_at)

    candidates = [
        c for c in comments
        if (c.get('user') or {}).get('type') == 'Bot'
        and _parse_time(c['created_at']) >= floor
    ]
    if not candidates:
        return False, (
            f"Booth posted NO report during this run (no bot comment at or after {started_at}). "
            "The action exited 0, so without this step the run would read as a clean audit. "
            "Compare the run's duration with the usual 5-13 minutes and read the action's log."
        )

    problems = []
    for c in candidates:
        try:
            block = extract(c.get('body') or '')
        except VerdictError as exc:
            problems.append(f"{c.get('html_url', c.get('id'))}: malformed booth-verdict block ({exc})")
            continue
        if block is None:
            problems.append(f"{c.get('html_url', c.get('id'))}: no booth-verdict block")
            continue
        if head_matches(str(block.get('head')), head_sha):
            return True, (
                f"Booth report found for {head_sha[:7]}: {c.get('html_url', c.get('id'))} "
                f"(overall: {block['overall']})"
            )
        problems.append(
            f"{c.get('html_url', c.get('id'))}: verdict block names head {block.get('head')!r}, "
            f"this run audited {head_sha[:7]}"
        )

    return False, (
        "Booth commented during this run, but no comment is a readable report for the commit "
        "this run audited:\n  " + "\n  ".join(problems)
    )


def main(argv):
    if len(argv) != 4:
        print(__doc__.strip().splitlines()[0])
        print("usage: booth_report_posted.py COMMENTS_JSON HEAD_SHA STARTED_AT")
        return 2
    comments = load_comments(Path(argv[1]).read_text(encoding='utf-8'))
    ok, message = check(comments, argv[2].strip(), argv[3].strip())
    print(("OK: " if ok else "FAIL: ") + message)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))
