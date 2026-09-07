# Verification Protocol

This repository is built by delegating real engineering work to AI agents
(see [AI Reliability](https://lifeisgreat07.github.io/NFL-Model-2/) on the
live dashboard for the incidents that motivated this document). This file
states the rule explicitly so it's a structural expectation for any agent
working on this repo, not something that only holds when someone happens
to be paying close attention.

## The Rule

**Any claim about test results, repository state, reproducibility, or
model performance must be backed by real, re-executed output -- not a
description of one.**

Concretely:

- "All tests pass" is not a valid claim on its own. The actual command
  output (or a copy of it) is.
- "This PR is merged" / "this branch is up to date" is not a valid claim
  on its own. A real `git log`, `git status`, or GitHub UI screenshot is.
- "This result is reproducible" is not a valid claim on its own. A fresh
  re-run, from the current code, with the actual numbers, is.
- A test file existing in the repository is not evidence it works.
  Existence and passing are different claims -- verify both, separately.
  (See [AI Reliability](https://lifeisgreat07.github.io/NFL-Model-2/),
  Incident 3, for exactly this failure mode occurring for real.)
- **A screenshot that is not attached is not evidence.** "Verified in both
  themes" describes a process; the images are the artifact. Booth marked the
  same visual claim UNVERIFIABLE three times on PR #21 because the screenshots
  existed only in the working session -- and it was right to. Attach them, or
  state the claim as a process note rather than as proof.
- **A figure is only true at a commit.** "144 passed" is a claim about a
  specific tree, and a branch that grows makes it false without anyone editing
  it. PR #21 quoted three different counts, each correct when written. If a
  number is worth putting in a description, it is worth re-checking at the
  head that description will be read against.

## Why External Verification, Not Self-Checking

Asking an agent to "double-check" its own claim is a weaker mitigation
than it sounds like: the same failure mode that produced a wrong claim
can just as easily produce a confident re-confirmation of it. What
actually catches errors in this project's history is *external,
mechanical* verification -- a real command re-run, a real screenshot, a
real diff -- not another round of the same kind of reasoning that
produced the original claim.

## Structural Enforcement, Not Just Discipline

Where possible, this rule is enforced mechanically rather than relying on
an agent remembering to follow it:

- **CI runs the leak-free test suite on every PR** touching model logic
  (`.github/workflows/run-tests.yml`) -- so a real, visible pass/fail
  status exists on every PR, not just a description of one. Making this
  a hard *requirement* for merge (blocking a bad merge, not just showing
  a status) needs one additional manual step -- a branch protection rule
  in repo Settings -- which is a real, separate action from the workflow
  existing. Check the repo's current branch protection settings before
  assuming this is already enforced as a hard gate; if it isn't yet, the
  workflow still gives real, visible signal, it just isn't unbypassable.
- **Scout pre-flight** (`src/scout_preflight.py`): run against a PR
  description *before* the PR is opened. It checks the claims whose truth is
  mechanically decidable -- that a quoted test count matches a real run at
  HEAD, that a multi-commit branch enumerates its commits so a reviewer knows
  what they are approving, and that a visual claim carries an attachment.
  Exits non-zero, so it can gate.

  It exists because every one of those three failures happened on PR #21 and
  was caught by Booth *after* the PR was public, at the cost of a full audit,
  when each was a two-second check beforehand. It is not a replacement for
  Booth and cannot be: it is a regex over a description, and it has no opinion
  about whether the work is right. It exists so that Booth's audit is spent on
  substance rather than on arithmetic Scout could have done itself.

  `tests/test_scout_preflight.py` replays PR #21's original description
  against PR #21's real commit range and asserts the tool reaches the same two
  findings Booth did. A checker that cannot catch the failure it was written
  for is decoration.
- **Booth**: a dedicated verification role (see below) whose job is
  auditing a PR's claims against the PR's own actual, re-executed output
  before it's trusted.

## Booth

Booth is a separate agent role from the one that does the primary work
("Scout" -- the agent writing code, running experiments, and opening
PRs throughout this project). Booth's only job is auditing: given a PR,
re-run the exact commands it claims were run, compare the real output to
what was claimed, and flag any discrepancy before the PR is trusted.

Booth does not re-read Scout's claims and reason about whether they
sound plausible -- that would just be the same failure mode wearing a
different name. Booth re-executes.

See `BOOTH_PROTOCOL.md` for Booth's exact operating instructions.

## Scope

This protocol governs claims about *this repository's* code, tests, and
results. It does not cover the model's own predictive uncertainty (that's
what confidence intervals, bootstrap tests, and honest ACCEPT/REJECT/
INCONCLUSIVE labeling on Model Lab are for) -- those are separate,
already-established disciplines in this project, not something this
document introduces.
