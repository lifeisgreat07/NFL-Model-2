# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history; history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-10-14, 23:30 UTC (session 1014, Wednesday: Stage 76 done, #443-#447)

---

## Right now

**Suite:** run it before quoting it; CLAUDE.md's `Suite:` line is the checked
figure. The NFL lives in `src/sports/nfl/` and `*/nfl/`; shared modules in `src/core/`.

**The product is Sportalytics** (Stage 67). **Live:** home `/`, NFL `/nfl/` (Model **v2.6**),
NHL `/nhl/` (day board), NBA `/nba/` (day board, empty until opening night). One theme key, `site:theme`.

**The 2026-10-13 UI/UX audit is being worked as Stages 75-80** (text in
`docs/history/09-more-sports.md`; one item per PR; merge granted by Mark for 75-80).
**Stage 75 is done:** items 1-6 are #436, #437, #438, #439, #440, #442 (#441 is not a PR).
Every finding reproduced.
**Stage 76 is done:** items 7-11 are #443, #444, #445, #446, #447. Every finding reproduced
(X6; X5, the NHL's half only after a redraw; F4; N12; C1).
**Next, in this order (Mark, 2026-10-14):** the NBA block that must be live by 10-20 - Stage 77
items 32, 33, 22, 21, then Stage 80 item 60 and Stage 79 items 51, 48, 46 - then Stage 77's
12-20 and 23-31, 34, 35, then Stage 78. All of these are built and guarded on a scratch branch,
one PR each; Stage 79's 45, 47, 49, 50 and Stage 80's 52-59 and 61-64 are not built yet.

**Decided for Stage 77 item 23 (copy row 12), Mark 2026-10-14:** the NFL's "numbers behind this"
are not printed in points per 100 plays, as the audit suggested. A `why` value is the part's push on
Model A's log-odds, not a rating, so that unit would be false. Each row reads the team the part
helped and the points of win chance it gave them ("DEN +1.2"), under a one-line caption. Team
Deep-Dive's game panels still print the raw values; that is outside the item.

**Decided, Mark 2026-10-14:** results read **Correct / Missed** on every surface and every sport
(Stage 77 item 26; this replaces Stage 64's "right so far"). Stage 78 item 36 takes option B: the
home's font sizes move onto tokens, with one new token `--fs-40` for the hero. Stage 78 item 37's
three tag tones (filled, outlined, accent) are approved as rendered. Item 40's 72ch is about
100-115 characters a line in this face. Item 42 moves the four surfaces the audit names to
`--surface-2` and leaves the More sheet's items alone. Merging Stage 79 and 80 items is granted.

**NBA goes live on Tue 10-20** (Stage 65). Before then: Stage 80 item 60 (countdown) and the
audit's B1-B5 must be merged. Merging Stage 79 and 80 items is granted (Mark, 2026-10-14).
A reminder is set for the night itself.

**Week 6 locks Thu 10-15**, the first week under v2.6 (HOU at JAX in London is neutral). Reminder set.

**Watching:** the first missed-dispatch alerts (#433) on the Thursday lock 10-15 and Saturday 10-17
(the NBA's 16:00 slot fired on time 10-14); the QB routine's Wed 22:00 UTC run (prompt fixed 10-13);
issue #428, whose first test since #429 is the 10-14 nightly shuffled suite (GitHub starts it hours late).
Two things for Mark, seen while rendering: the NHL board's eyebrow reads "This Week" on any week
(not in the audit; ask before adding it), and 10-13's NHL games still show as Live because the
saved status is stale (Stage 80 item 61, live scores, is the fix).

**Single next action:** open Stage 77 item 32 (the NBA eyebrow says "Next week" when it shows
next week) from its prepared patch, then 33, 22, 21, 60, 51, 48, 46 before Tue 10-20.

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| Stages 77-80 (UI/UX audit) | 75 and 76 done | the NBA block first; item 60 and B1-B5 before 10-20 |
| Stage 44 (Line Judge) | Item 1 merged (#435): checks first, agent on failure | PR 2 (other runs), PR 3 (agent, digest) after the audit stages |
| Stage 42 | Items 1-4 done | 5: after four on-time weeks |
| Stage 39 | Items 1-4, 7 done | 5 in December; 6 wants a rendered choice in January |
| Stage 43 (Spotter) | Not started | After 44 |
| #428, #431 | Open | Mark |
| Stage 40 | Not to be touched | Mark |

One branch at a time. Full suite and mutation scope at the head, case files listed, a bounded
check for Booth. Never start the mutation runner under pythonw, and never two runners at once.

## Known and deliberately not fixed

- **GitHub's cron starts hours late**; cron-job.org starts on time. Every Weekly update slot runs once (slot guard).
- **Booth's prose can disagree with its own verdict block** (#286 ... #433). Re-run once; red again for the same reason, merge and log it.
- **Booth can say NEEDS HUMAN REVIEW on an all-green PR** whose only unverified claims are browser renders (#437, 10-14). That is Mark's call, not a re-run.
- **Booth's step "Fail if Booth posted no report" can go red beside a SAFE verdict** (#440, 10-14). One re-run cleared it.
- **Booth's runner has no Playwright**, so a Chromium claim in a PR body is UNVERIFIABLE there.
- **The file bridge can report a write and keep the old file**: commit to a new name, copy into place, compare hashes.
- **The N1 back-check is exact on local Windows, close but not exact on Linux runners.**
- **The drift check re-tests a growing sample every week**, so it will sometimes flag by chance.
- **A failed Thursday run leaves Thursday night's game unpicked** unless dispatched by hand that day.
- **`ubuntu-latest` moves to Ubuntu 26 from 2026-10-19.** Nothing pins the image; watch the first runs after it.
- **An NBA tip time is read as a placeholder by hour** (Stage 77 item 33): a weekday tip before 5 PM ET reads "time TBD". ESPN's own time-valid flag would be exact, but reading it is a change to `src/sports/nba/schedule.py`, held until the audit's UI stages are done.
