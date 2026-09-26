# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history — history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-09-26, evening session in progress (Stage 11 complete, #110 to #115 merged)

---

## Right now

**Suite:** 2505 passing, none skipped — `python -m pytest -q` on `main` at
`2e8efce`, HEAD level with origin.

**Next action: Stage 12's first item, self-host the font** (inlined into the built
page at build time). Mark approved exactly four files on 2026-09-26 (latin and
latin-ext, 73,692 bytes); they are downloaded, with hashes, in
`E:\nfl-session-archive\fonts\` on markys (outside the repo). Logos stay
hot-linked (his decision). CLAUDE.md's Stage 12 section has the three PRs.

**Done this evening: all of Stage 11**, one PR at a time, each merged on SAFE TO
MERGE with no discrepancies: #110 kickoff lock, #111 More sheet inert, #112 24px
text toggles, #113 pick'em rank wording, #114 illustrative margin retired, #115
sidebar provenance line. #113 was closed unmerged by a failed chained merge and
reopened (CLAUDE.md trap); #115 needed Mark's hand edit of its description after
Booth's one discrepancy, then re-audited clean.

**Earlier the same day:** Next Gen Stats, one PR at a time, each merged after Booth
said SAFE TO MERGE with no discrepancies. #108 registered the questions
before any data was loaded (`experiments/stage6/registry.json`: one budget of
five slots, 99% intervals, for all of Stage 6). #109 answered N1: FAIL. Four
Next Gen Stats passing numbers did not predict a quarterback's next game
beyond his recent EPA plus play-by-play CPOE, so N2 and N3 were never run
and no slot is spent. Booth re-ran the build and N1 from raw data on its own
runner and got the same figures.
Later the same day: the UX/UI review, and Stages 11 to 22 planned with Mark,
team news included (Stage 16; nflverse's injury reports carry 2026).

**Stage 4's first live runs:** the Nightly canary passed on 2026-09-25 and
2026-09-26, and the `pbp-2026-09` cache was saved on the first night and read
on the second. Both runs started 4.5 to 5 hours after their 06:00 UTC cron,
which is GitHub's scheduler, not the workflow. No alert issue has opened.

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| First run of the QB routine | Due Mon 2026-09-28 22:00 UTC | Check it opened a PR, or said in one line that none was needed |
| First weekly summary | Due Tue 2026-09-29 11:00 UTC | Open the run's page and check the summary reads right |
| Scheduled-run delay | Canary ran ~5 h late twice | Watch Thursday 2026-10-01's 16:00 UTC lock run; a 5 h delay still locks before the Thursday kickoff |
| Booth alert, drift issue, failure alerts | Live, never fired | Each needs a real event; when one opens an issue, check it reads right |
| Which claim Booth's fixture claim 1 was | Inferred as the "Two commits." line | Reading that run's report artifact, if it is ever worth it |
| Leak table splits two ways on Linux | Recorded in the QB case study | Nothing, unless it is ever worth finding the cause |

## Queued, in order

1. **Stages 11 to 22**, in order, one PR at a time: integrity and access; self-hosted
   assets and browser CI; landing and links; one meaning per number; weekend
   refresh; team news; Week Board card v2; Model Lab rebuilt; team pages; testing
   with five people; the week-5 extras; beyond 95.
2. **The rest of Stage 6** (referee crews, personnel) after Stage 18, registered
   into `experiments/stage6/registry.json` first. None of the five slots is spent.

Open decisions for Mark, each made from a render when its stage starts: net rating
per 100 plays (Stage 14); the team-colour bars on the new card (Stage 17).
TV channel per game added to Stage 15 (from ESPN's scoreboard, with the checks
that keep a wrong channel off the page) and shown on the card in Stage 17.

Merge one branch at a time: every branch that adds a mutation case file
moves the README count, so two open at once always conflict.

## Known and deliberately not fixed

- **The drift check is on accuracy**, which cannot carry a result at this sample size. Its issue says so and points at log loss and Brier. Rewriting the check itself was not in Stage 4.
- **A failed Thursday run leaves Thursday night's game unpicked** unless someone dispatches the workflow by hand that day. Since #105 the failure opens an issue, so it at least reaches Mark in time.
- **A Booth header can disagree with its verdict block**, logged by `cross_check()`. Should it fail? It has cost nothing yet.
- **`check_scoped_test_counts` skips a count for a module that does not exist** — a DELETED module passes silently.
- **Only the wrap-up gate and session-start recompute CLAUDE.md's `Suite:` line.** Both manual, accepted.
- **Preflight checks commits and suite counts, not every number in prose.** Read the body against `git log` before opening.
- **Nothing on the page reaches the listbox edge flip**; kept and checked over synthetic geometries.
- **A human approval leaves no artifact in the repo.** `memory/` is what records it.
- **The co-occurrence trace, and the no-JS findings, are re-derivable only where a browser exists.** No CI job here has one; the premise is guarded in the suite and the finding is not.
- **60 of 496 team pairs sit under the CIEDE2000 floor on the Week Board's split bar, accepted 2026-09-21.** `src/verify_matchup_cvd.py` still reports it.
- **The Booth report check cannot tell WHY a run posted nothing.** Since #101 a failed audit at least opens an issue.
