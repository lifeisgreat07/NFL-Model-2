# Contributing

Thank you for looking. This is a one-person project with an AI agent doing
most of the typing, so the rules below are mostly about evidence: every
change has to show that what it says is true.

## Set up and run the tests

Python 3.11 and node 20 (the tests that run the dashboard's JavaScript skip
without node). From the repository root:

```bash
pip install -r requirements.txt -r requirements-dev.txt
ruff check .
python -m pytest
```

## A pull request

- **One change per pull request.** If a branch grows past its title, split
  it or rewrite the description.
- **A command beside every number.** "4380 passed" is a claim about one
  commit; write the command that produced it and the commit it ran at. The
  rule and its reasons are in [VERIFICATION.md](VERIFICATION.md).
- **A new guard comes with a mutation case** in `tests/mutation/cases/`
  that breaks what the guard protects and names the test that must catch
  it. Run it with `python tests/mutation/runner.py --id <case id>`.
- **No suite counts in commit messages.** A commit message cannot be
  corrected; put figures in the pull request description.
- **Say what you did not check.** A limitation stated in the description is
  fine; one a reviewer has to find is not.

Every pull request is checked twice before a person reads it: Scout
pre-flight (`src/agents/scout_preflight.py`) checks the description against the
branch, and Booth, a second agent that shares no context with the author,
re-runs the claims and posts a report ([BOOTH_PROTOCOL.md](BOOTH_PROTOCOL.md)).
A pull request that changes `.github/workflows/booth-pr-audit.yml` or
`BOOTH_PROTOCOL.md` must carry a line beginning "Human review required:",
because Booth would then be auditing with the instructions under review.

## What not to send

Changes to the saved picks in `predictions/` or the grades in `results/`.
A pick is saved before kickoff and never edited; that is what makes the
season record honest.
