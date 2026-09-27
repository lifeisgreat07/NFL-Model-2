# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history — history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-09-26, evening session ended (Stages 11 to 14 complete, #110 to #130 merged, #131 open)

---

## Right now

**Suite:** 2830 passing, none skipped — `python -m pytest -q` on `main` at
`36fbc01`, HEAD level with origin.

**IN FLIGHT: #131 is OPEN (branch `stage15-espn-probe`, head `1b4201e`), the
last thing running when the session ended.** Stage 15's first item: an "ESPN
probe" workflow that reads ESPN's scoreboard (weeks 1-4 of 2026) from a GitHub
runner. On markys the probe passed (16/16 complete each week); **on GitHub's
runner the ESPN probe check FAILED** (Mark saw it, 2026-09-26 ~23:25 ET). Nobody
has read the failing log or Booth's audit yet. Next action: open the PR's
"ESPN probe" job log and find out why -- unreachable from Actions (blocked, 403,
timeout) or a shape problem -- and read Booth. If ESPN cannot be reached from
GitHub's runners, the TV-channel plan (CLAUDE.md Stage 15) needs a rethink with
Mark before any code; say so rather than working around it. Items 2 and 3 of
Stage 15 (weekend refresh, card status) do not depend on ESPN.

**Done this evening: Stages 11 (#110 to #115), 12 (#116 to #122), 13 (#123
to #127) and 14 (#128 to #130).** The
Browser checks workflow (Playwright + axe-core, `tests/browser/check_page.py`)
now runs on every PR touching the page and is green on `main`. Details, and
Booth's figure slips, are in `memory/2026-09-26.md`.

**Earlier the same day** (details in `memory/2026-09-26.md`): Next Gen Stats N1
answered FAIL (#108, #109; no Stage 6 slot spent), the UX/UI review, and Stages
11 to 22 planned with Mark.

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

Open decision for Mark, made from a render when its stage starts: the
team-colour bars on the new card (Stage 17). (Per 100 plays for Stage 14:
decided 2026-09-26.)
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
- **The co-occurrence trace, and the no-JS findings, are re-derivable only where a browser exists.** Browser checks (#120) now has one, but runs only `tests/browser/check_page.py`; these two are still guarded as premises in the suite, not re-derived.
- **Browser checks does not click.** States reached only by interaction (a switched-off series, an opened team dive, shared-picks mode) are covered by static tests, not by the browser run. #122 found the off-series contrast failure by reading, not by the checker.
- **60 of 496 team pairs sit under the CIEDE2000 floor on the Week Board's split bar, accepted 2026-09-21.** `src/verify_matchup_cvd.py` still reports it.
- **The Booth report check cannot tell WHY a run posted nothing.** Since #101 a failed audit at least opens an issue.
