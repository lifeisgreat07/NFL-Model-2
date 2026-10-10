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
- **Every action is pinned to a commit SHA**, not a movable tag, with the
  release it is named in a comment. `tests/test_action_pins.py`.
- **Booth, the AI auditor, cannot push code** and cannot mint a token: it
  holds `contents: read` and `pull-requests: write`, which posting its report
  needs and which could also edit a pull request's title or description
  (its workflow's header says so). `tests/test_booth_permissions.py`. A
  dispatched audit refuses a pull request from a fork before checking
  anything out (Stage 68 item 7).
- **A pull request's description or title is never interpolated into a
  shell**: it reaches a step only through an `env:` assignment.
  `tests/test_workflow_permissions.py`.
- **No `pull_request_target`**: a fork's pull request runs with a read-only
  token. `tests/test_workflow_permissions.py`;
  `.github/workflows/collect-agent-log.yml` explains why.

## Credentials outside GitHub

The scheduled runs are started on time by cron-job.org, which holds one
fine-grained GitHub token: this repository only, Actions read and write,
expiring a year after it was made (decision record 0005; renew it before
then). It cannot push code itself, but it can start any of the 21
workflows that accept a dispatch, the weekly lock's `force` included, and
give their inputs. So no free-text input reaches a shell line
(Stage 68 item 30).

Booth's audits run on `CLAUDE_CODE_OAUTH_TOKEN`, a repository secret that
only the Booth workflows read. The data sources the workflows read are
public and need no key.
