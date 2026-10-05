"""
Raise an alert when a Booth audit run fails.

Why: a Booth run that fails is seen only by whoever opens the Actions tab.
Since 2026-09-23 the audit job fails when Booth posted no report
(src/agents/booth_report_posted.py), and on the first live run that caught a real
empty audit. A red check still reaches nobody unless someone is looking. So
.github/workflows/booth-alert.yml runs this on every completed "Booth PR
audit" run and turns a failure into a GitHub issue, which notifies the owner
and stays open until someone closes it.

Why a separate workflow instead of a step in booth-pr-audit.yml: the Claude
Code action refuses to run when a PR's copy of its workflow file differs from
main's, so a PR that edited booth-pr-audit.yml would sink its own audit.
Decided in Stage 4's notes in CLAUDE.md.

What counts: `failure` and `timed_out`. A `cancelled` run is normal (a newer
push cancels the older audit through the concurrency group) and a `success`
is the report having posted; neither is an alert. `skipped` means the job's
`if:` kept it off, such as a draft PR.

One issue per PR, matched on the exact title (src/pipeline/alerts.py): a PR whose
audit fails three pushes running gets one issue with three comments.

    python -m src.agents.booth_alert "$GITHUB_EVENT_PATH"
"""
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

ALERT_CONCLUSIONS = ('failure', 'timed_out')


def pr_number(run: dict[str, Any]) -> Any:
    """The PR the run audited, or None. A pull_request run lists it in the
    event; a workflow_dispatch run lists none, so the alert names it by its
    head commit instead."""
    prs = run.get('pull_requests') or []
    if prs and prs[0].get('number') is not None:
        return prs[0]['number']
    return None


def alert_for(event: dict[str, Any]) -> tuple[str, str] | None:
    """(title, body) for a run worth an alert, or None."""
    run = event.get('workflow_run') or {}
    conclusion = run.get('conclusion')
    if conclusion not in ALERT_CONCLUSIONS:
        return None
    number = pr_number(run)
    sha = (run.get('head_sha') or '')[:7] or 'unknown'
    subject = f'PR #{number}' if number is not None else f'commit {sha}'
    title = f'Booth audit failed: {subject}'
    body = '\n'.join([
        f'The Booth PR audit run for {subject} ended `{conclusion}`.',
        '',
        f'- Run: {run.get("html_url", "(no link in the event)")}',
        f'- Head: `{run.get("head_sha", "unknown")}` on `{run.get("head_branch", "unknown")}`',
        f'- Event: `{run.get("event", "unknown")}`, attempt {run.get("run_attempt", "?")}',
        '',
        'The audit job fails when Booth posted no report for the commit it '
        'checked out, as well as when a step errors. The run log says which. '
        'If a report IS on the PR and the job still failed, the report check '
        'itself broke: it runs from a copy of two files, so check that they '
        'import nothing else (PR #219). A PR that edits booth-pr-audit.yml is '
        'audited like any other since PR #176, so its failure is real too.',
        '',
        'Close this issue once the audit has been re-run or the cause is '
        'understood. The next failure for this PR opens a fresh one.',
    ])
    return title, body


def main(argv: list[str] | None = None,
         raise_alert: Callable[[str, str], tuple[str, Any]] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print('usage: booth_alert.py <event.json>', file=sys.stderr)
        return 2
    event = json.loads(Path(argv[0]).read_text(encoding='utf-8'))
    alert = alert_for(event)
    if alert is None:
        conclusion = (event.get('workflow_run') or {}).get('conclusion')
        print(f'no alert: the audit run ended {conclusion!r}')
        return 0
    if raise_alert is None:
        from src.pipeline.alerts import open_or_comment
        raise_alert = open_or_comment
    action, ref = raise_alert(*alert)
    print(f'{action}: {ref}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
