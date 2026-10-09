# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history — history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-10-08, 21:55 UTC (week 5 locked by hand; slot guard, site build, home page and seven post-lock items merged; no PR open)

---

## Right now

**Suite:** run it before quoting it; CLAUDE.md's `Suite:` line is the checked
figure. `src/` is packaged: run modules with `python -m src.<package>.<module>`.
The dashboard template is parts under `src/dashboard/`, joined by
`src/core/template_parts.py`. Read it with `read_template()`, never one
part as the page (traps). The NFL is still `src/sports/nfl/` until Stage 52 merges.

**Live:** the home page at `/`, the NFL at `/nfl/`, the NHL at `/nhl/`, the
NBA's backtest at `/nba/`, with sport pills on each (#329, #330). The NHL's
daily run (14:00, 21:00 UTC) and canary (06:40) start on time from cron-job.org.

**The Weekly update's cron-job.org job is ON** (Mark, 10-08 14:29 ET) behind
the slot guard (#327). `data/nfl/run_slots/weekly-update.json` records the last
served slot. Tuesday 2026-10-13 11:00 UTC is its first real test: one run
does the work and GitHub's late copy is skipped by `slot-guard`. Check it.

**Next action: `s42-monday-fallback`** (rebase, suite, scope, PR), then the queue below.

**Mark delegated decisions to Claude on 2026-10-05 ("until I say so")** and
on 2026-10-08 put Claude in charge of finishing the queue. Each decision is
logged with its reason in `memory/` and the Audit Response Log.

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| `s42-monday-fallback` | Rebased on `353797a`, suite green, scope at `16ac4ff`: 48 caught | Rebase, suite, PR (body_scron.md) |
| `s39-cancelled-state` | Rebased on `353797a`; card rendered and checked; scope `scan_a` running at stop | Its scope result, rebase, suite, PR (body_scan.md) |
| Stack s45-1 to s49-24, then s21 | Rebased on `9882b0b` 10-08 (s45-1 counts resolved; s45-3 got a count-fix commit `6f4b833`); suite green at the top but for that fix | One PR each, rebasing the next after each merge; bodies in the session archive |
| Stage 52 | Not re-rehearsed since 10-06 | After the stack: s52r_run.cmd on then-current main, proof52, PR; then Mark re-points cron-job.org (stage52_repoint.md) |
| Stage 21 (`s21-insights`) | Last of the stack | Week 5 graded (Tuesday 10-13) |
| Issue #333 | Booth count-mismatch alert for #332 (merged at Mark's word) | Mark to close |

## Queued, in order

1. `s42-monday-fallback`, then `s39-cancelled-state` (render-checked: "Cancelled · not played, so not graded").
2. The stack: `s45-1-pins`, `s45-2-csp`, `s45-3-pip-audit`, `s46-7-picks-csv`, `s46-5-lock-proof`, `s47-12-canonical`, `s47-11-print`, `s47-10-forced-colors`, `s48-18-dead-code`, `s49-24-history`. Restack with `one-off-scripts\restack.ps1` (session archive).
3. Stage 52 (migrate_nfl v11, byte-identical proof), then Mark's re-pointing.
4. Stage 21 once week 5 is graded.

One branch at a time. Rebase on `main`, full suite and mutation scope at the
head (prep_branch.ps1, scope_run.py), case files listed, and give Booth a
bounded check when the scope is big (it returns NEEDS HUMAN REVIEW when it
cannot re-run a large scope). Never start the mutation runner under pythonw.

## Known and deliberately not fixed

- **GitHub's cron starts hours late**; cron-job.org starts on time. Every Weekly update slot now runs once (slot guard).
- **Booth's audit can run past its 20-minute limit** on a big scope; a bounded check in the body keeps it inside.
- **Booth's prose can count an UNVERIFIABLE its block does not**: the run goes red over a SAFE TO MERGE comment (#286, #296, #303, #307, #332).
- **The drift check re-tests a growing sample every week**, so it will sometimes flag by chance. R4 registered it as written.
- **A failed Thursday run leaves Thursday night's game unpicked** unless dispatched by hand that day.
- **Preview cards have no TV channel or team-news line**; **the share image says "The Pick'em Model"** (Mark, #242).
- **A human approval leaves no artifact in the repo.** `memory/` records it.
- **60 of 496 team pairs sit under the CIEDE2000 floor on the Week Board's split bar, accepted 2026-09-21.**
- **The reproducibility audit flips between GitHub runners**; local Windows reproduces exactly.
- **`ubuntu-latest` moves to Ubuntu 26 from 2026-10-19.** Nothing pins the image; watch the first runs after it.
- **The nightly dependency audit (s45-3) has no cron-job.org job yet**; Mark adds one after it merges.
