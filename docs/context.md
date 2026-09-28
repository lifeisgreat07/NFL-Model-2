# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history — history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-09-28, afternoon session (Stage 6 closed; Mark's page review built and merged)

---

## Right now

**Suite:** 3755 passing, none skipped — `python -m pytest -q` on `main` at
`35cfb6d` (README screenshots, after #168), HEAD level with origin.

**Next action: check the QB routine's first run** (Mon 2026-09-28 22:00 UTC):
it should have opened a PR, or said in one line that none was needed. Then
Tuesday's weekly summary (11:00 UTC). No PR is open.

**Done today:** Stage 19 (#160 to #162); Stage 6 closed — referees registered
(#163) and R1 FAILED (#164, correlation +0.18, interval −0.28 to +0.65; a
first run with a team-abbreviation join bug was discarded and disclosed).
Mark's page review: #165 Week Board card (logos at the bar's ends, two
redundant lines gone), #166 Methodology table alignment, #167 Model Lab frames
and one-line pills, #168 Team Deep-Dive logo. README screenshots retaken with
logos (`35cfb6d`, docs only). Details: `memory/2026-09-28.md`.

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| First run of the QB routine | Due Mon 2026-09-28 22:00 UTC | Check it opened a PR, or said in one line that none was needed |
| First weekly summary | Due Tue 2026-09-29 11:00 UTC | Open the run's page and check the summary reads right |
| Thursday lock run | Due Thu 2026-10-01 16:00 UTC | Check it started, locked before kickoff, and its push survived; week 4 is the first card with quarterback names and TV channels |
| Season Accuracy's forecast score | Merged (#160), not on the page yet | 50 graded games: after week 4 at the earliest |
| TV exceptions for holiday and Saturday games | Weeks 12, 15, 16 | Sourced entries in `data/tv/exceptions.json` before those weeks |
| Model Lab mappings | My calls, in #141 | Mark may overrule any (listed in `experiments/legacy/README.md`) |
| Drift issue | Never fired on a real event | A real event |
| #147's catch-up step under a race | Ran once with nothing to catch up | A refresh or weekly run during which main moves |

## Queued, in order

1. **Stages 23 to 29, from the 2026-09-28 audit** (approved by Mark the same
   day; items and order in CLAUDE.md). Stage 23 first, starting with its
   item 1 (one escaping helper for every JSON fill).
2. **Stages 20 to 22**: 20 needs five real testers and comes after Stage 26;
   21 waits for week 5; 22 comes from 20.
3. **Line movement and the closing-line backtest**: not before the 2026 regular season ends, beside Stage 28.

Merge one branch at a time: every branch that adds a mutation case file
moves the README count, so two open at once always conflict. Describe a
mutation scope as run whole, with both the whole-file and the case-by-case
counts (CLAUDE.md trap, #165).

## Known and deliberately not fixed

- **The drift check is on accuracy**, which cannot carry a result at this sample size. Its issue says so and points at log loss and Brier.
- **A failed Thursday run leaves Thursday night's game unpicked** unless someone dispatches the workflow by hand that day. Since #105 the failure opens an issue.
- **A Booth header can disagree with its verdict block**, logged by `cross_check()`. It has cost nothing yet.
- **The generator writes `index.html` without `encoding=`**, so a non-cp1252 character in generated text crashes the Windows build or breaks UTF-8 readers (#164's en dash). Avoid literal non-ASCII in generated text.
- **Season Accuracy's trend end-labels**: where Model A and Model B end on the same value the labels stack beside one marker (seen in the README screenshot). Not yet looked at.
- **`tests/browser/check_page.py` flaked in Booth's environment** on 2 of 7 runs (#156 audit), unrelated to the change.
- **`check_scoped_test_counts` skips a count for a module that does not exist** — a DELETED module passes silently.
- **Only the wrap-up gate and session-start recompute CLAUDE.md's `Suite:` line.** Both manual, accepted.
- **Preflight checks commits and suite counts, not every number in prose.** Read the body against `git log` before opening.
- **A human approval leaves no artifact in the repo.** `memory/` is what records it.
- **Browser checks does not click.** Interaction-only states are covered by static tests.
- **60 of 496 team pairs sit under the CIEDE2000 floor on the Week Board's split bar, accepted 2026-09-21.**
- **The Booth report check cannot tell WHY a run posted nothing.** Since #101 a failed audit at least opens an issue.
