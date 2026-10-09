# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history; history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-10-09, 08:50 UTC (overnight session: #353 to #360, #362 and #364 merged; no PR open)

---

## Right now

**Suite:** run it before quoting it; CLAUDE.md's `Suite:` line is the checked
figure. The NFL lives in `src/sports/nfl/` and `*/nfl/`; shared modules in `src/core/`.

**Live:** the home page at `/`, the NFL at `/nfl/`, the NHL at `/nhl/` (now a
day board: a seven-day strip, one row per game, tap to open the card), the
NBA's backtest at `/nba/`. One theme key, `site:theme`, is shared by every
page. Every scheduled run writes a "Record the start delay" line, and the
NFL's runs table shows "Late by".

**The morning runs on the moved tree ran green on 10-09**, the 05:17
weekend refresh from cron-job.org included. The shuffled suite (GitHub's
own cron, 07:15) had not started by 08:50; check it first (10-08's failed,
issue #325, closed). The dependency audit's #361 (pypdf) stays open until
the next audit after #364 reports clean. Tuesday 10-13 11:00 UTC is the
slot guard's first real test. Unconfirmed: whether Mark updated the QB
routine's prompt for the move; its next PR (Mon 22:00 UTC) shows which path
it used.

**Waiting on Mark (each written up in `memory/2026-10-09.md`):**
1. **NBA go/no-go** (Stage 65). Claude's call is GO for both models; opening
   night is Tuesday 10-20. Mark picks Model B's market (ESPN's odds, as the
   backtest, or Kalshi) and the start date, and sets up cron-job.org jobs.
2. **Stage 38's neutral-site rule**: the draft amendment N1 and its
   back-check. Model B's intercept is negative, so decide whether the rule
   covers Model B before it is registered. No model change until then.
3. **Stage 66**: home page option A, B or C (canvas "Sportalytics Home Page
   Options"); the audit is `docs/design/HOME-AUDIT-2026-10-09.md`.
4. **Stages 62.2 and 67**: a puck and ball icon and a wordmark (canvas
   "Sportalytics Icons and Wordmark").
5. **A Saturday refresh slot** on cron-job.org, if Friday NFL games
   (Black Friday, Christmas) should not wait two days for a status refresh.
6. **Stage 39 item 4** (ratings frozen through the playoffs): disclose or register.

**Single next action:** build the NBA's live run (Stage 65 items 2 to 5)
once Mark answers 1; until then, Stage 21 once week 5 is graded (Tue 10-13).

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| Stage 21 (`s21-insights`) | Built on the pre-move layout | Week 5 graded (Tue 10-13); rebase across #351's moves first |
| Stage 65 (NBA live) | Probe merged (#357); go/no-go written | Mark's answers above |
| Stage 62.2, 66, 67 | Options rendered on two canvases | Mark's choice |
| Stage 38 neutral-site rule | Draft N1 and back-check written | Mark: Model B in or out |
| Stage 39 | Items 2 (stepper), 3, 7 merged | Item 2's `game_type` in saved picks; 1's rest; 5 in December; 6; 4 is Mark's |
| Stage 42 | Item 1 merged (#358) | Its other items |
| Stage 43; 44 | Open | Nothing |

## Queued, in order

Stage 65's live run once Mark answers; Stage 21 once week 5 is graded; Stage 39
item 2's `game_type` in saved picks, then item 6; whichever of 62.2, 66 and 67
Mark chooses; Stage 42's other items; 43; 44.

One branch at a time. Rebase on `main`, full suite and mutation scope at the
head, case files listed, and give Booth a bounded check when the scope is big.
A scope too long for one command line: run the whole corpus instead. Never
start the mutation runner under pythonw. Scout pre-flight reads "<number>
test" in a commit subject as a suite count ("Stage 39 test" failed it).

## Known and deliberately not fixed

- **GitHub's cron starts hours late**; cron-job.org starts on time. Every Weekly update slot runs once (slot guard).
- **Friday NFL games wait up to two days for a status refresh**: no slot runs between Friday 05:17 and Sunday 21:47 UTC. `tests/test_playoff_weeks.py` holds the exception.
- **Booth's prose can disagree with its own verdict block**: the run goes red over a clean comment (#286, #332, #341, #351, #362). Re-run once; red again for the same reason, merge and log it.
- **Booth's runner has no Playwright**, so a Chromium claim in a PR body is UNVERIFIABLE there; point it at the Browser checks workflow and keep Chromium figures as process notes.
- **Booth's audit can run past its 20-minute limit** on a big scope; a bounded check in the body keeps it inside.
- **The drift check re-tests a growing sample every week**, so it will sometimes flag by chance.
- **A failed Thursday run leaves Thursday night's game unpicked** unless dispatched by hand that day.
- **The reproducibility audit flips between GitHub runners**; local Windows reproduces exactly.
- **`ubuntu-latest` moves to Ubuntu 26 from 2026-10-19.** Nothing pins the image; watch the first runs after it.
