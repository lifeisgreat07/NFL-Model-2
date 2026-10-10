# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history; history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-10-10, 04:00 UTC (session 1010a: Stage 68 written; #380 merged)

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

**NBA goes live on Tue 10-20** (Stage 65, #367-#370). `.github/workflows/nba-daily.yml` runs at
16:00 and 21:30 UTC, and `.github/workflows/nba-canary.yml` at 06:50 UTC. Mark set up and enabled
all three cron-job.org jobs on 10-09. Before 10-20 the daily run only refreshes
the schedule. **Check the first scheduled "NBA daily run" is green**, and on
10-20/21 that picks were saved and priced (ESPN first, Kalshi fallback, else
"no price").

**NFL v2.6 (Stage 38 N1, #373/#374):** at a game the schedule calls neutral,
neither model gives the listed home team a home edge. Week 7 (lock Thu 10-15)
is the first week picked under it; earlier saved picks keep their edge and
their cards say so.

**Saturday 05:17 UTC weekend refresh** (#371) is in, with GitHub's fallback
line; Mark cloned the cron-job.org job. **Stage 39 item 4** (#372) says on
the Methodology page that ratings use regular-season plays and freeze
through the playoffs.

**Tuesday 10-13:** week 5 is graded; Stage 21 (`s21-insights`) can start,
rebased across #351's moves. 11:00 UTC is the slot guard's first real test.

**Stage 68 (the 2026-10-09 Fable audit, 29 items)** is the queue between the
dated checks: item 1 (pipefail, #380) is merged; items 4 to 6 must land
before 10-19/10-20. Text at the end of `docs/history/09-more-sports.md`;
every finding's verdict is in the Audit Response Log.

**Single next action:** Stage 68 item 2 (push retry); Stage 21 once week 5 is graded (Tue 10-13); before
that, check the first NBA daily run and the Saturday refresh slot's first run.

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| Stage 21 (`s21-insights`) | Built on the pre-move layout | Week 5 graded (Tue 10-13); rebase across #351's moves first |
| Stage 65 (NBA live) | All four PRs merged (#367-#370); cron jobs on | Opening night 10-20; watch the first runs |
| Stage 39 | Items 2, 3, 4, 7 merged | 2's `game_type`; 1's rest; 5 in December; 6 |
| Stage 42 | Item 1 merged (#358) | Its other items |
| Stage 43; 44 | Open | Nothing |
| Stage 68 (Fable audit) | Item 1 merged (#380) | Items 2-29 in order; Mark on E10, E15, U1-U3, U11, U27, U29-U36, U44, E22/24/25/28 |
| Stage 40 | Not to be touched | Mark |

## Queued, in order

Stage 21 once week 5 is graded (Tue 10-13); Stage 39's other items; Stage 42's
other items; 43; 44.

One branch at a time. Rebase on `main`, full suite and mutation scope at the
head, case files listed, and give Booth a bounded check when the scope is big.
A scope too long for one command line: run the whole corpus instead. Never
start the mutation runner under pythonw, and never two runners at once (a
timed-out foreground call keeps running: confirm it is gone first).

## Known and deliberately not fixed

- **GitHub's cron starts hours late**; cron-job.org starts on time. Every Weekly update slot runs once (slot guard).
- **Booth's prose can disagree with its own verdict block**: the run goes red over a clean comment (#286, #332, #341, #351, #362). Re-run once; red again for the same reason, merge and log it.
- **Booth's runner has no Playwright**, so a Chromium claim in a PR body is UNVERIFIABLE there; point it at the Browser checks workflow and keep Chromium figures as process notes.
- **Booth's audit can run past its 20-minute limit** on a big scope; a bounded check in the body keeps it inside.
- **The N1 back-check, like the reproducibility audit, is exact on local Windows and close but not exact on GitHub's Linux runners** (same pins; cause not isolated). Its registration says so.
- **The drift check re-tests a growing sample every week**, so it will sometimes flag by chance.
- **A failed Thursday run leaves Thursday night's game unpicked** unless dispatched by hand that day.
- **`ubuntu-latest` moves to Ubuntu 26 from 2026-10-19.** Nothing pins the image; watch the first runs after it.
