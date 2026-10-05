# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history — history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-10-05, evening ET (#282 to #291 merged; Stages 45 to 49's approved ten done)

---

## Right now

**Suite:** run it before quoting it; CLAUDE.md's `Suite:` line is the checked
figure. `src/` is packaged: run modules with `python -m src.<package>.<module>`.
The dashboard template is parts under `src/dashboard/`, joined by
`src/pipeline/template_parts.py`. Read it with `read_template()`, never one
part as the page (traps). `python -m src.agents.session_start --skip-tests`
now prints the unattended jobs, the QB routine's PR and open issues.

**Next action: the read-only checks**: Tuesday 2026-10-06's Weekly update
(`DRIFT CHECK: OK` in its run summary, a "Model A, log loss" section, Pages
from `src/dashboard/`, its row in the runs table) and **Thursday 2026-10-08,
the first LOCK on the new code**. Nothing that touches the weekly run or the
weekend refresh merges until that lock has been seen to run. Then Stage 42's
slot guard, and only then does Mark switch on the Weekly update's
cron-job.org job.

**Scheduled runs start from cron-job.org** (Stage 42; `docs/decisions/`),
GitHub's cron the fallback: canary 06:00, slice 06:30, refreshes Fri 05:17,
Sun 21:47, Mon 01:47 (no repo cron yet) and Mon 05:37 UTC. Each shows a
requested run on time and a late `schedule` copy (2h24m to 8h39m on 10-05).
The nightly shuffled suite (07:15) is GitHub cron only.

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| cron-job.org dispatch | Six jobs on, Weekly update job off | The slot guard (Stage 42), after the 10-08 lock |
| QB override routine | Prompt on `src.pipeline` since 10-02 | Monday 22:00 UTC run: see memory/2026-10-05.md |
| Log-loss drift check (R4) | First real run OK on 48 games | Tuesday's Weekly update |
| Nightly shuffled suite (#290) | Merged; never run yet | Tonight's 07:15 UTC |
| Issue #287 | Booth's report disagreed with itself on #286; cause understood | Mark closes it |
| Private vulnerability reporting | Off (SECURITY.md covers both) | Mark's choice, Settings, Security |
| Season Accuracy's forecast score | Merged (#160), not on the page yet | 50 graded games |
| TV exceptions for holiday and Saturday games | Weeks 12, 15, 16 | Sourced entries before those weeks |
| Audit Response Log | Updated 2026-10-05 with this session's deviations | Fable, for the next audit |

## Queued, in order

1. After the 10-08 lock is seen to run: Stage 42's slot guard (then Mark
   switches on the Weekly update job), Stage 36 item 7, Stage 37 items 3,
   4 and 6, Stage 41 items 5 and 7, the Monday 01:47 UTC fallback cron line
   for the Sunday evening refresh, and the cancelled-game state (Mark's
   call: "Cancelled", not graded; Stage 39).
2. Then Stage 45 items 1 and 2, and **multi-sport, NHL then NBA (Stages
   50 to 61)**: 50 and 51 may start before the lock; 52 waits for it.
3. **Stage 21** once week 5 is graded (Tuesday 2026-10-13 at the earliest).
4. Stages 44, 43, 39, 41 (item 6 needs rendered options), 40; the rest of
   45 to 49 (3, 5 to 14, 18, 24); 20, 22, 28 as before.

One branch at a time still: the README case count no longer conflicts
(#282), but the one-PR rule is Mark's. Run the suite and the mutation scope
at the exact head being opened, after the last rebase, and list the case
files (scope_run.py in the session archive's one-off scripts runs the
scope whole in a detached worktree, hidden). Keep counts out of
commit messages.

## Known and deliberately not fixed

- **Scheduled runs start hours late** on GitHub's cron; cron-job.org starts them on time.
- **Preview cards have no TV channel or team-news line**: those steps read locked weeks only (#204).
- **The link preview and share image say "The Pick'em Model"**: Mark's decision (#242).
- **The drift check re-tests a growing sample every week**, so it will sometimes flag by chance. R4 registered it as written.
- **A failed Thursday run leaves Thursday night's game unpicked** unless dispatched by hand that day. The failure opens an issue.
- **Mutation runs quote a count Booth cannot always rerun**: a large scope is UNVERIFIABLE by design; the files are listed.
- **Booth's prose can count an UNVERIFIABLE its block does not**: the run goes red over a SAFE TO MERGE comment (#286), and booth-alert's issue (#287) does not name that cause.
- **Season Accuracy's trend end-labels** stack where Model A and Model B end on the same value.
- **`check_scoped_test_counts` skips a count for a module that does not exist.**
- **Only the wrap-up gate and session-start recompute CLAUDE.md's `Suite:` line.**
- **A human approval leaves no artifact in the repo.** `memory/` records it.
- **60 of 496 team pairs sit under the CIEDE2000 floor on the Week Board's split bar, accepted 2026-09-21.**
- **The reproducibility audit flips between GitHub runners**; local Windows reproduces exactly.
