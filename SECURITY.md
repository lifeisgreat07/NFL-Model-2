# Security

This is a public, single-maintainer portfolio project: a static dashboard
on GitHub Pages and the workflows that build it. There is no server, no
account and no form that sends anything anywhere. The things worth
protecting are the repository's tokens and what the scheduled workflows
write to `main`.

## How to report a vulnerability

Please do not put the details in a public issue.

- If the repository's **Security** tab shows a **Report a vulnerability**
  button, use it: that opens a private advisory only the maintainer sees.
- If it does not, open an issue titled "Security report" that says only
  that you have one, with no details, and the maintainer will reply with a
  private way to send it.

Expect a first reply within a week. There is no bounty.

## What is already in place, and where it is checked

Each of these is held by a test, so a change that weakens it fails the suite
rather than relying on someone noticing.

- **Every workflow declares its token's permissions, and holds no scope it
  does not use.** `tests/test_workflow_permissions.py`: each scope beyond
  `contents: read` must name the step in that workflow that spends it.
- **The Claude Code action, the auto-commit action, checkout and
  setup-python are pinned to commit SHAs**, not movable tags.
  `tests/test_action_pins.py`. The Pages, cache, artifact and setup-node
  actions are still on tags; pinning them is queued (Stage 45 item 1) for
  after the 2026-10-08 lock, because the deploy runs on every data commit.
- **Booth, the AI auditor, runs on a token that cannot write** and cannot
  mint one. `tests/test_booth_permissions.py`.
- **A pull request's description or title is never interpolated into a
  shell**: it reaches a step only through an `env:` assignment.
  `tests/test_workflow_permissions.py`.
- **No `pull_request_target`**: a fork's pull request runs with a read-only
  token. `tests/test_workflow_permissions.py`;
  `.github/workflows/collect-agent-log.yml` explains why.

## Credentials outside GitHub

The scheduled runs are started on time by cron-job.org, which holds one
fine-grained GitHub token: this repository only, Actions read and write,
expiring after a year. It can start a workflow; it cannot push code
itself. The data sources the workflows read are public and need no key.
