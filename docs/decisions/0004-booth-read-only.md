# 0004. Booth cannot push, and merging stays a human decision

## Decision

Booth, the AI auditor that checks every pull request, runs on the
workflow's own `GITHUB_TOKEN` with `contents: read`. It cannot push to the
branch it audits and cannot merge. It can comment on pull requests, which
is how it reports. It reads `BOOTH_PROTOCOL.md` and shares no context with
Scout, the session that wrote the change. A pull request merges only when
Mark has said so for that session, on Booth's SAFE TO MERGE with no
discrepancies.

## Why

- An auditor that can change what it audits is not independent.
- Its verdict is advice with evidence attached: each claim in the
  description is re-executed and marked CONFIRMED, DISCREPANCY or
  UNVERIFIABLE. The decision to merge belongs to a person.
- Until 2026-09-28 the Claude Code action exchanged an OIDC token for the
  Claude app's installation token, which can write code, workflows and pull
  requests, so Booth held write access while the README said it did not.
  The workflows now hand the action `GITHUB_TOKEN` and cannot mint an OIDC
  token.

## What it costs

- The same comment permission would let Booth edit a pull request's
  description. That is accepted, and visible in the PR's edit history.
- A pull request that edits Booth's own instructions is audited by those
  edits, so pre-flight requires a "Human review required:" line on it.
- Booth's report can disagree with itself; since #279 the audit run fails
  when it does, and the merge is then a decision made by hand.

## What would reopen it

Nothing planned. Spotter and Line Judge (Stages 43 and 44) are being
designed to the same rule: read and comment only.

Sources: `tests/test_booth_permissions.py`; `docs/architecture.md`,
"Booth can't push"; CLAUDE.md, the PR loop.
