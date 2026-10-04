# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history — history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-10-04, night ET (#266 to #281 merged; on-time runs started through cron-job.org)

---

## Right now

**Suite:** run it before quoting it; CLAUDE.md's `Suite:` line is the checked
figure. `src/` is packaged: run modules with `python -m src.<package>.<module>`.
The dashboard template is parts under `src/dashboard/`, joined by
`src/pipeline/template_parts.py`. Read it with `read_template()`, never one
part as the page (traps).

**Next action: the read-only checks**: the Monday 22:00 UTC QB routine
(first on `src.pipeline`); Tuesday 2026-10-06's Weekly update (`DRIFT CHECK:
OK`, a "Model A, log loss" section, Pages from `src/dashboard/`); and
**Thursday 2026-10-08, the first LOCK on the new code** (week 4 locked
before #255 and #258). Then Stage 42's slot guard (patch ready; it touches
the Weekly update, so it waits for that lock), and only then does Mark
switch on the Weekly update's cron-job.org job.

**Scheduled runs start from cron-job.org** (Stage 42), GitHub's cron the
fallback: canary 06:00, slice 06:30, refreshes Fri 05:17, Sun 21:47, Mon
01:47 (no repo cron yet) and Mon 05:37 UTC. Each shows a `workflow_dispatch`
run on time and a late `schedule` copy.

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| cron-job.org dispatch | Six jobs on, Weekly update job off; canary test run started at once (2026-10-04 19:57 UTC) | The slot guard (Stage 42), after the 10-08 lock |
| QB override routine | Prompt edited by Mark 2026-10-02 to `src.pipeline` | Its first run, Monday 22:00 UTC |
| Log-loss drift check (R4) | Merged #261; first real run OK on 48 games | Tuesday's Weekly update |
| Template parts (#265) | Merged; page byte-identical locally and on Booth's runner | Tuesday's scheduled build |
| claude-code-action pin | On v1.0.236 | A hand bump when a release matters |
| Season Accuracy's forecast score | Merged (#160), not on the page yet | 50 graded games: after week 4 at the earliest |
| TV exceptions for holiday and Saturday games | Weeks 12, 15, 16 | Sourced entries in `data/tv/exceptions.json` before those weeks |
| Audit Response Log | Updated 2026-10-04 with the fourth audit's verdicts | Fable, for the next audit |

## Queued, in order

1. After the 10-08 lock: Stage 42's slot guard, Stage 36 item 7, Stage 37
   items 3, 4 and 6. Page-only Stage 37 item 5 any time.
2. **Stage 21** once week 5 is graded (Tuesday 2026-10-13 at the earliest).
3. Stages 44 (Line Judge), 43 (Spotter), 39 (playoffs, before December;
   item 1's first part done), 41 (items 2 to 4 done; 5 and 7 after the lock,
   6 needs rendered options for Mark), 40 (January); 20, 22, 28 as before.
4. Mark's call: a cancelled game reads "started" forever (#280's finding).

Merge one branch at a time: every branch that adds a mutation case file
moves the README count, so two open at once always conflict. Run the suite
and the mutation scope at the exact head being opened, after the last
rebase, and describe the scope as run whole with both counts, listing the
case files (Booth cannot reproduce a count whose selection it cannot see).
Keep counts out of commit messages: scout-preflight fails on one even when
the body discloses it.

## Known and deliberately not fixed

- **Scheduled runs start hours late** (3.5 to 6.5h since 2026-09-24). Absorbed by the 11:00 Thursday lock and 8h slack, not fixed; GitHub's queue is not ours.
- **Preview cards have no TV channel or team-news line**: those steps read locked weeks only (#204).
- **The link preview and share image say "The Pick'em Model"**: Mark's decision, recorded in `test_product_name`; the re-audit's redraw was declined (#242).
- **The drift check re-tests a growing sample every week**, so it will sometimes flag by chance. The issue says so. R4 registered the rule as written; changing it needs a new registration.
- **A failed Thursday run leaves Thursday night's game unpicked** unless someone dispatches the workflow by hand that day. Since #105 the failure opens an issue.
- **Mutation runs quote a count Booth cannot always rerun**: a large scope is UNVERIFIABLE in the audit by design; list the files so the selection is at least checkable.
- **Season Accuracy's trend end-labels** stack where Model A and Model B end on the same value. Not yet looked at.
- **`check_scoped_test_counts` skips a count for a module that does not exist** — a DELETED module passes silently.
- **Only the wrap-up gate and session-start recompute CLAUDE.md's `Suite:` line.** Both manual, accepted.
- **Preflight checks commits and suite counts, not every number in prose.** Read the body against `git log` before opening.
- **A human approval leaves no artifact in the repo.** `memory/` is what records it.
- **Browser checks does not click.** Interaction-only states are covered by static tests; since #245 the tie, skipped-week and stale-preview states are built and checked.
- **60 of 496 team pairs sit under the CIEDE2000 floor on the Week Board's split bar, accepted 2026-09-21.**
- **Booth's runner shows CLAUDE.md modified on every PR that edits it**: claude-code-action restores it from `main` before Booth starts, by design (traps). Stashing it is right; Booth's prompt says so since #263, and #265's audit did exactly that.
- **The reproducibility audit flips between GitHub runners** (same commit, same packages). Machine-dependent; traps. Local Windows reproduces exactly. Since #262 each record names its CPU, so the next flip can be tied to hardware.
- **The Booth report check cannot tell WHY a run posted nothing.** Since #101 a failed audit at least opens an issue.
