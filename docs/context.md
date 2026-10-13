# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history; history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-10-13, 18:30 UTC (session 1011a, Tuesday: week 5 graded; #429, #430)

---

## Right now

**Suite:** run it before quoting it; CLAUDE.md's `Suite:` line is the checked
figure. The NFL lives in `src/sports/nfl/` and `*/nfl/`; shared modules in `src/core/`.

**The product is Sportalytics** (Stage 67, wordmark W2: "lytics" in the accent
colour). The repository keeps its name. `tests/test_product_name.py` fails on
the old name anywhere a visitor sees it.

**Live:** the home page at `/` (Stage 66: option A, scoreboard first, with
option C's "New here?"), the NFL at `/nfl/` (Model **v2.6**), the NHL at `/nhl/`
(day board), the NBA at `/nba/` (day board, empty until opening night).
Puck P3 and ball B2 sit top left on the NHL and NBA pages and on the home
cards (Stage 62.2). One theme key, `site:theme`, everywhere.

**NBA goes live on Tue 10-20** (Stage 65, #367-#370): `.github/workflows/nba-daily.yml` at 16:00 and 21:30 UTC,
`.github/workflows/nba-canary.yml` at 06:50 UTC. Before 10-20 the daily run only refreshes the schedule. On
10-20/21 check picks were saved and priced (ESPN, then Kalshi, else "no price").

**NFL v2.6 (Stage 38 N1, #373/#374):** at a game the schedule calls neutral,
neither model gives the listed home team a home edge. Week 7 (lock Thu 10-15)
is the first week picked under it; earlier saved picks keep their edge and
their cards say so.

**Two cron-job.org jobs Mark made on 10-09 have never fired:** the NFL Saturday 05:17 UTC weekend refresh
(#371) and the NBA 16:00 UTC daily run. GitHub's fallback covered both, hours late (Sat 10-10's refresh ran
11:10 UTC; week 5 is covered). Every older job fires on time. The cause is in Mark's account; Claude cannot
sign in there. Next Saturday test: 10-17 05:17 UTC.

**NHL picks no longer die with a source (#427):** on Sat 10-10 an odds-feed timeout ended the 21:00 UTC run
and nine games started unpicked (#423, #424). **Main's suite was red on 10-11 (#425)** until #426: the
end-to-end test read a schedule rewritten since its moment. Data commits start no test run, so the nightly
shuffled suite is main's only daily check. **Stage 39 item 4** (#372) says on the Methodology page that
ratings use regular-season plays and freeze through the playoffs.

**Week 5 graded on time (Tue 10-13, 11:03 UTC);** NYG 27 WAS 27, the first real tie, scored as neither.
**Stage 21 is merged (#430):** Worth a look box, movers line, season sparklines. #429 made main green
again (8-character short SHAs; a real tie in the tie state). Slot guard: GitHub's late copy of 11:00 had
not run by 18:30 UTC, so the skip is still unproven.

**Stage 68 (the 2026-10-09 Fable audit) is done:** #380 to #421; item 33 (U44, shared fonts) later, Mark's
call. Item-to-PR map at the end of `docs/history/09-more-sports.md`; verdicts in the Audit Response Log.
#387, #389, #401, #417 reviewed 10-11 (`memory/2026-10-11.md`): no reverts, two wording/contrast questions.

**Single next action:** check the week 7 lock under v2.6 (Thu 10-15, a reminder is set). Mark:
open the two silent cron-job.org jobs (NFL Saturday 05:17, NBA 16:00). NBA opening night 10-20.

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| cron-job.org: NFL Sat 05:17, NBA 16:00 | Never fired since made on 10-09 | Mark, in his account |
| Stage 65 (NBA live) | All four PRs merged (#367-#370); cron jobs on | Opening night 10-20; watch the first runs |
| Stage 39 | Items 2, 3, 4, 7 merged | 2's `game_type`; 1's rest; 5 in December; 6 |
| Stage 42 | Item 1 merged (#358) | Its other items |
| Stage 43; 44 | Open | Nothing |
| Stage 68 (Fable audit) | Done (#380-#421) | Item 33 (U44) later |
| Stage 40 | Not to be touched | Mark |

## Queued, in order

Stage 39's other items; Stage 42's other items; 43; 44.

One branch at a time. Rebase on `main`, full suite and mutation scope at the
head, case files listed, and give Booth a bounded check when the scope is big.
A scope too long for one command line: run the whole corpus instead. Never
start the mutation runner under pythonw, and never two runners at once (a
timed-out foreground call keeps running: confirm it is gone first).

## Known and deliberately not fixed

- **GitHub's cron starts hours late**; cron-job.org starts on time. Every Weekly update slot runs once (slot guard).
- **Booth's prose can disagree with its own verdict block**: the run goes red over a clean comment (#286, #332, #341, #351, #362). Re-run once; red again for the same reason, merge and log it.
- **Booth's runner has no Playwright**, so a Chromium claim in a PR body is UNVERIFIABLE there; point it at the Browser checks workflow and keep Chromium figures as process notes.
- **Booth's audit can run past its 20-minute limit** on a big scope; a bounded check in the body keeps it inside. A test that drives a daily run whole costs about 30 s a run, and the bounded check runs it once per mutation case too: keep such cases to a few (#427 timed out twice at five).
- **The N1 back-check, like the reproducibility audit, is exact on local Windows and close but not exact on GitHub's Linux runners** (same pins; cause not isolated). Its registration says so.
- **The drift check re-tests a growing sample every week**, so it will sometimes flag by chance.
- **A failed Thursday run leaves Thursday night's game unpicked** unless dispatched by hand that day.
- **`ubuntu-latest` moves to Ubuntu 26 from 2026-10-19.** Nothing pins the image; watch the first runs after it.
