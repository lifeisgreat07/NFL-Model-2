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
