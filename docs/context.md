# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history — history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-09-29, late evening (#202 to #213 merged; Stage 27 done; Stage 29 nearly done; nothing open)

---

## Right now

**Suite:** 4460 passing, none skipped, on `main` at `743305e` (after #213).

**Next action: check Thursday's lock run** (2026-10-01, cron 11:00 UTC;
scheduled runs have been starting up to 6.5 hours late, so "not run yet"
before about 17:30 UTC is normal). Confirm it started, locked week 4
before the 00:15 UTC Friday kickoff, replaced the Tuesday preview on the
Week Board, and its push survived. Week 4 is the first locked card with
quarterback names and TV channels. If it has not started by 20:00 UTC,
start "Weekly update" by hand from the Actions tab. The 2026-09-29
session scheduled this check for Thursday 17:00 UTC (1pm ET); a fresh
session that picks it up first should do the same check.

Then, in this order:
1. **CLAUDE.md split** (the last Stage 29 item): rules into CLAUDE.md
   (about 400 lines), traps into a new docs/traps.md, stage history into
   a new docs/stage-history.md, keeping `tests/test_claude_md_freshness.py`
   green. One PR, docs only; do it in a fresh session.
2. **Website field and version tags**: Mark said "later". The Website
   field (repo About, gear icon) takes the live URL; tags `v2.0` to `v2.5`
   come from `VERSION_HISTORY`. Only on his say-so.
3. Stages 20 to 22 and Stage 28, as queued below.

**Done this session:** #202 nightly mutation slice; #203 Thursday lock at
11:00 UTC, slack 8h; #204 Tuesday preview (week 4's is live); #205 "Models
split" keyed on picks; #206 ruff; #207 runner reads UTF-8; #208 action pins
(Stage 27 done); #209 README "Running the tests"; #210 CONTRIBUTING and PR
template; #211 MIT; #212 favicon; #213 product name "Pick'em Model".

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| Thursday lock run | Due Thu 2026-10-01 11:00 UTC | Check as above |
| QB overrides | Must be merged by 11:00 UTC Thursday | Mark, Wednesday evening |
| Website field, version tags | Not done | Mark ("later") |
| CLAUDE.md split | Not started | A fresh session |
| claude-code-action pin | On v1.0.236; `v1` moved to v1.0.237 on 2026-09-29 | A hand bump when a release matters |
| Season Accuracy's forecast score | Merged (#160), not on the page yet | 50 graded games: after week 4 at the earliest |
| TV exceptions for holiday and Saturday games | Weeks 12, 15, 16 | Sourced entries in `data/tv/exceptions.json` before those weeks |
| Model Lab mappings | My calls, in #141 | Mark may overrule any (listed in `experiments/legacy/README.md`) |
| Drift issue | Never fired on a real event | A real event |

## Queued, in order

1. **Stage 29's last item** (CLAUDE.md split), then the Website field and tags when Mark says.
2. **Stages 20 to 22**: 20 needs five real testers; 21 waits for week 5; 22 comes from 20.
3. **Stage 28** and the closing-line backtest: after the regular season.

Merge one branch at a time: every branch that adds a mutation case file
moves the README count, so two open at once always conflict. Run the suite
and the mutation scope at the exact head being opened, after the last
rebase, and describe the scope as run whole with both counts.

## Known and deliberately not fixed

- **Scheduled runs start hours late** (3.5 to 6.5h since 2026-09-24). Absorbed by the 11:00 Thursday lock and 8h slack, not fixed; GitHub's queue is not ours.
- **Preview cards have no TV channel or team-news line**: those steps read locked weeks only (#204).
- **No PNG favicon or Apple touch icon** (#212): no renderer on the local Windows machine, and the bridge corrupts binaries.
- **The link preview and share image say "The Pick'em Model"** (#213): the same name with an article; the PNG was not redrawn.
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
