# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history; history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-10-09, 14:55 UTC (Mark's answers on the six waiting items; no PR open)

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

**Mark's answers, 2026-10-09 10:52 ET (reasons in `memory/2026-10-09.md`):**
1. **NBA: GO** for both models from opening night (Tue 10-20). Model B's market
   is ESPN's odds (the backtest's), Kalshi the named fallback, "no price"
   rather than a silent switch. Mark adds the cron-job.org jobs when the PR
   gives him the literal steps.
2. **Stage 38 N1** covers both models, registered, shipped as a
   `MODEL_VERSION` bump between locks, if Mark confirms (he asked what was needed).
3. **Home page: option A** with C's "New here?" (Claude's recommendation).
4. **Icons and wordmark: puck P3, ball B2, wordmark W2** (canvas "Sportalytics
   Icons and Wordmark"), with Stage 67's rename.
5. **Saturday refresh:** a PR adds `'17 5 * * 6'` to `.github/workflows/nfl-weekend-refresh.yml`
   and retires the Friday exception; then Mark clones the Friday cron-job.org job to Saturday.
6. **Stage 39 item 4: disclose**, no model change (Claude's recommendation).

**Single next action:** Stage 65's live run (registration, daily run, canary,
board from the NHL day board) before 10-20.

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| Stage 21 (`s21-insights`) | Built on the pre-move layout | Week 5 graded (Tue 10-13); rebase across #351's moves first |
| Stage 65 (NBA live) | GO 10-09; probe merged (#357) | Nothing; cron-job.org jobs by Mark at the end |
| Stage 62.2, 66, 67 | Chosen 10-09: P3, B2, W2; home option A + "New here?" | Nothing |
| Stage 38 neutral-site rule | Draft N1, both models | Mark's yes to the model change |
| Stage 39 | Items 2 (stepper), 3, 7 merged | Item 4 (disclose), 2's `game_type`; 1's rest; 5 in December; 6 |
| Stage 42 | Item 1 merged (#358) | Its other items |
| Stage 43; 44 | Open | Nothing |

## Queued, in order

Stage 65's live run; Stage 21 once week 5 is graded (Tue 10-13); the Saturday
refresh slot; Stage 39 item 4's disclosure; Stage 38 N1 once Mark says yes; 62.2
icons, then 67's name and wordmark, then 66's home page; Stage 39's other items;
Stage 42's other items; 43; 44.

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
