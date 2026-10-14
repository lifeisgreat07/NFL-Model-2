# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history; history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-10-14, 01:00 UTC (session 1013b, Tuesday evening ET: #432, #433)

---

## Right now

**Suite:** run it before quoting it; CLAUDE.md's `Suite:` line is the checked
figure. The NFL lives in `src/sports/nfl/` and `*/nfl/`; shared modules in `src/core/`.

**The product is Sportalytics** (Stage 67, wordmark W2: "lytics" in the accent
colour). The repository keeps its name. `tests/test_product_name.py` fails on
the old name anywhere a visitor sees it.

**Live:** the home page at `/` (Stage 66), the NFL at `/nfl/` (Model **v2.6**), the NHL at `/nhl/`
(day board), the NBA at `/nba/` (day board, empty until opening night). One theme key, `site:theme`.

**NBA goes live on Tue 10-20** (Stage 65): `.github/workflows/nba-daily.yml` at 16:00 and 21:30 UTC,
`.github/workflows/nba-canary.yml` at 06:50 UTC. On 10-20/21 check picks were saved and priced
(ESPN, then Kalshi, else "no price"). A reminder is set.

**Week 6, not 7, locks Thu 10-15** and is the first week under v2.6 (Stage 38 N1: no home edge at a
neutral site). Weeks 1-5 are locked (5 under v2.5); week 6's Tuesday preview is v2.6 and has HOU at
JAX (London) neutral. Earlier docs said "week 7"; corrected. A reminder is set.

**The QB override routine was broken from #351 (10-08) to 10-13.** Its prompt imported `src.pipeline.*`
and wrote `data/qb_overrides/`; both moved to `src/sports/nfl/` and `data/nfl/qb_overrides/`. No override
PR since week 4. Mark pasted the corrected prompt 10-13 (verified with list_triggers); it now stops on a
ModuleNotFoundError instead of improvising. A path move must update it (agents cannot edit it).

**cron-job.org fixed 10-13 evening (Mark, checked in the console):** there was no 16:00 NBA job (the one
titled 16:00 ran at 21:30), no Saturday 05:17 job, and the Thursday Weekly update job pointed at the
workflow's pre-#351 file name and had never run. All three are now right, UTC. **Since #433 a miss is seen:** GitHub's late copy of a covered
slot asks the Actions API for a dispatch near the slot and, finding none, opens or comments on
"<workflow>: cron-job.org did not start the HH:MM UTC run" (`src/core/missed_dispatch.py`).
First tests: NBA 16:00 on 10-14, the Thursday lock 10-15, Saturday 10-17 (reminders set).

**Slot guard proven (10-13):** the 11:01 dispatch served the Weekly update's slot; GitHub's 17:56
copy ran only the guard, skipped the job and committed nothing.

**Stage 39 item 1 done (#432):** the synthetic league runs the postseason (weeks 19-22, empty 23).
Item 2's `game_type` and the Cancelled card were already built (Stage 68 item 27; Stage 39).

**Issue #428** (nightly shuffled suite red) should be fixed by #429; the first nightly after it is
10-14 07:15 UTC (reminder set). #431 (Booth's count-line red on #430) is open for Mark.

**Single next action:** check the 10-14 16:00 UTC NBA dispatch arrived. Mark pasted the QB
routine's corrected prompt (verified 10-13); its next run is Wed 22:00 UTC. Then: Stage 44's shape.

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| QB override routine | Prompt fixed 10-13 | Wed 22:00 UTC run: a week 6 PR or "none needed" |
| cron-job.org jobs | Fixed 10-13 (Thu URL, NBA 16:00, Sat 05:17) | First runs 10-14, 10-15, 10-17 |
| Stage 65 (NBA live) | Merged (#367-#370) | Opening night 10-20 |
| Stage 39 | Items 1-4, 7 done (#432 last) | 5 in December; 6 (bracket status) wants a rendered choice in January |
| Stage 42 | Items 1-4 done (#358, slot guard, #433) | 5: after four on-time weeks |
| Stage 44 (Line Judge) | Not started | Mark: plain checks in each workflow, agent only on a failure? |
| Stage 43 (Spotter) | Not started | After 44 |
| Stage 68 (Fable audit) | Done | Item 33 (U44) later |
| Stage 40 | Not to be touched | Mark |

## Queued, in order

Stage 44 (once Mark answers its shape); Stage 43; Stage 39 item 6 in January.

One branch at a time. Rebase on `main`, full suite and mutation scope at the
head, case files listed, and give Booth a bounded check when the scope is big.
Never start the mutation runner under pythonw, and never two runners at once.

## Known and deliberately not fixed

- **GitHub's cron starts hours late**; cron-job.org starts on time. Every Weekly update slot runs once (slot guard).
- **Booth's prose can disagree with its own verdict block**: the run goes red over a clean comment (#286, #332, #341, #351, #362, #430, #433). Re-run once; red again for the same reason, merge and log it. #433 went green on the re-run.
- **Booth's runner has no Playwright**, so a Chromium claim in a PR body is UNVERIFIABLE there.
- **Booth's audit can run past its 20-minute limit** on a big scope: keep whole-daily-run cases to a few.
- **The file bridge can report a write and keep the old file** (10-13 again): commit to a new name and copy into place on the PC, then compare hashes.
- **The N1 back-check is exact on local Windows, close but not exact on Linux runners.**
- **The drift check re-tests a growing sample every week**, so it will sometimes flag by chance.
- **A failed Thursday run leaves Thursday night's game unpicked** unless dispatched by hand that day.
- **`ubuntu-latest` moves to Ubuntu 26 from 2026-10-19.** Nothing pins the image; watch the first runs after it.
