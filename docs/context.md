# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history — history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-10-04, afternoon ET (fourth audit reviewed; Stages 36 to 41 planned)

---

## Right now

**Suite:** run it before quoting it; CLAUDE.md's `Suite:` line is the checked
figure. `src/` is packaged: run modules with `python -m src.<package>.<module>`.
The dashboard template is parts under `src/dashboard/`, joined by
`src/pipeline/template_parts.py`. Read it with `read_template()`, never one
part as the page (traps).

**Next action: Stage 36, one PR at a time** (the fourth audit's loose
ends; none touches the weekly run except item 7, which waits). Alongside,
read-only: the Monday 22:00 UTC QB routine (its first run on the
`src.pipeline` imports); Tuesday 2026-10-06's Weekly update (summary reads
`DRIFT CHECK: OK`, the drift report has a "Model A, log loss" section,
Pages deploys from `src/dashboard/`); and **Thursday 2026-10-08, the first
LOCK on the new code**. Week 4 locked on 2026-10-01, before #255 and #258,
so it tested none of it.

**Stages 36 to 41 are planned** (fourth audit, 86/100, Mark approved
2026-10-04). Order at the top of that section in `docs/stage-history.md`;
the Stage 38 registration drafts are in `memory/2026-10-04.md`.

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| QB override routine | Prompt edited by Mark 2026-10-02 to `src.pipeline` | Its first run, Monday 22:00 UTC |
| Log-loss drift check (R4) | Merged #261; first real run OK on 48 games | Tuesday's Weekly update |
| Template parts (#265) | Merged; page byte-identical locally and on Booth's runner | Tuesday's scheduled build |
| claude-code-action pin | On v1.0.236 | A hand bump when a release matters |
| Season Accuracy's forecast score | Merged (#160), not on the page yet | 50 graded games: after week 4 at the earliest |
| TV exceptions for holiday and Saturday games | Weeks 12, 15, 16 | Sourced entries in `data/tv/exceptions.json` before those weeks |
| Audit Response Log | Updated 2026-10-04 with the fourth audit's verdicts | Fable, for the next audit |

## Queued, in order

1. **Stage 36** now; Stage 38's drafts to Mark; **Stage 37** after the
   2026-10-08 lock is seen to run.
2. **Stage 21** once week 5 is graded (Tuesday 2026-10-13 at the earliest).
3. **Stage 39** (playoffs) before December; **Stage 41** when a week has
   slack; **Stage 40** (season turnover) in January.
4. **Stage 34 item 32**: Stage 20's five real-person tests (Mark finds the
   testers), then the re-audit. **Stage 22** comes from 20; **Stage 28**
   after the regular season.

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
- **A Booth header can disagree with its verdict block**, logged by `cross_check()`. It has cost nothing yet.
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
