# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history — history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-09-29, afternoon (#202 to #207 merged; #208 open)

---

## Right now

**Suite:** 4389 passing, none skipped, on `main` at `e545aed` (after #207).

**Next action: #208 (Stage 27 item 1, action pins) waits for Mark's explicit
"merge 208".** Booth: NEEDS HUMAN REVIEW (expected: it edits Booth's own
workflow), 0 discrepancies, every SHA checked against its tag. On his OK,
merge it with the archive's `merge_pr.ps1`; if `main` has moved since
`e545aed`, rebase, re-run the suite and the 26-file scope at the new head,
and edit the description before merging. That finishes Stage 27.

Then Stage 29, one PR at a time, each run at its exact head after the last
rebase (CLAUDE.md trap, #206):
1. `s29-readme-front` (worktree `s29r`, `734547a`): README "Running the
   tests" and two recruiter bullets. Not pushed yet.
2. `s29-contributing` (worktree `s29c`, `cf92259`, stacked on 1):
   CONTRIBUTING.md and the PR template.
3. Name, favicon, LICENSE: Mark picks from the artifact "Front Door
   Options" (recommended: "Pick'em Model", favicon B, MIT).
4. Website field and version tags `v2.0` to `v2.5`: only on Mark's say-so.
5. Collector: Mark chooses between as-is (recommended), daily, or on PR
   close (see CLAUDE.md Stage 29).
6. CLAUDE.md split into rules plus traps and history (large; its own session).

**Today:** Thursday's lock run is **11:00 UTC** on 2026-10-01 (moved from
16:00 by #203). A check is scheduled in the 2026-09-29 session for 17:00
UTC. Scheduled runs have been starting up to 6.5 hours late, so "not run
yet" before about 17:30 UTC is normal.

**Done this session:** #202 nightly mutation slice (first run 30/30
caught); #203 Thursday lock at 11:00 UTC, slack 8h; #204 Tuesday preview
(week 4's preview is live since a manual run at 18:58 UTC); #205 "Models
split" keyed on picks; #206 ruff; #207 runner reads UTF-8. Week 3 graded:
Model A 6/16, Model B 8/16, market 8/16.

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| #208 action pins | Audited, 0 discrepancies | Mark's "merge 208" |
| Thursday lock run | Due Thu 2026-10-01 11:00 UTC | Check it started, locked week 4 before kickoff, replaced the preview, and its push survived; week 4 is the first locked card with quarterback names and TV channels |
| QB overrides | Must be merged by 11:00 UTC Thursday now | Mark, Wednesday evening |
| Stage 29 picks | Options sent | Mark: name, favicon, licence, Website/tags, collector |
| Season Accuracy's forecast score | Merged (#160), not on the page yet | 50 graded games: after week 4 at the earliest |
| TV exceptions for holiday and Saturday games | Weeks 12, 15, 16 | Sourced entries in `data/tv/exceptions.json` before those weeks |
| Model Lab mappings | My calls, in #141 | Mark may overrule any (listed in `experiments/legacy/README.md`) |
| Drift issue | Never fired on a real event | A real event |

## Queued, in order

1. **Stage 27 item 1** (#208), then **Stage 29** as above.
2. **Stages 20 to 22**: 20 needs five real testers; 21 waits for week 5; 22 comes from 20.
3. **Stage 28** and the closing-line backtest: after the regular season.

Merge one branch at a time: every branch that adds a mutation case file
moves the README count, so two open at once always conflict. Describe a
mutation scope as run whole, with both the whole-file and the case-by-case
counts, run at the head being opened.

## Known and deliberately not fixed

- **Scheduled runs start hours late** (3.5 to 6.5h since 2026-09-24). Absorbed by the 11:00 Thursday lock and 8h slack, not fixed; GitHub's queue is not ours.
- **Preview cards have no TV channel or team-news line**: those steps read locked weeks only (#204).
- **The drift check is on accuracy**, which cannot carry a result at this sample size. Its issue says so and points at log loss and Brier.
- **A failed Thursday run leaves Thursday night's game unpicked** unless someone dispatches the workflow by hand that day. Since #105 the failure opens an issue.
- **A Booth header can disagree with its verdict block**, logged by `cross_check()`. It has cost nothing yet.
- **Season Accuracy's trend end-labels** stack where Model A and Model B end on the same value. Not yet looked at.
- **`tests/browser/check_page.py` flaked in Booth's environment** on 2 of 7 runs (#156 audit), unrelated to the change.
- **`check_scoped_test_counts` skips a count for a module that does not exist** — a DELETED module passes silently.
- **Only the wrap-up gate and session-start recompute CLAUDE.md's `Suite:` line.** Both manual, accepted.
- **Preflight checks commits and suite counts, not every number in prose.** Read the body against `git log` before opening.
- **A human approval leaves no artifact in the repo.** `memory/` is what records it.
- **Browser checks does not click.** Interaction-only states are covered by static tests.
- **60 of 496 team pairs sit under the CIEDE2000 floor on the Week Board's split bar, accepted 2026-09-21.**
- **The Booth report check cannot tell WHY a run posted nothing.** Since #101 a failed audit at least opens an issue.
