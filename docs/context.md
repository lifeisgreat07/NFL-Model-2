# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history; history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-10-15 (session 1014-15, Thursday night: Stage 78 done, #479-#488)

---

## Right now

**Suite:** run it before quoting it; CLAUDE.md's `Suite:` line is the checked
figure. The NFL lives in `src/sports/nfl/` and `*/nfl/`; shared modules in `src/core/`.

**The product is Sportalytics** (Stage 67). **Live:** home `/`, NFL `/nfl/` (Model **v2.6**),
NHL `/nhl/` (day board), NBA `/nba/` (day board, empty until opening night). One theme key, `site:theme`.

**The 2026-10-13 UI/UX audit is being worked as Stages 75-80** (text in
`docs/history/09-more-sports.md`; one item per PR; merge granted by Mark for 75-80).
**Stages 75 and 76 are done:** items 1-6 are #436-#440, #442; items 7-11 are #443-#447.
**Stage 77 is done:** items 32, 33, 22, 21 are #448-#451; 12-14 are #456-#458; 15-20 are
#460-#465; 23, 24 are #466, #467; 25-31 are #469-#475; 34 is #477; 35 is #478.
**Stage 78 is done:** items 36-39 are #479-#482; 40-43 are #484-#487; 44 is #488.
The NBA block is in: Stage 80 item 60 is #452, Stage 79 items 51, 48, 46 are #453-#455.
**Next:** Stage 79's 45, 47, 49, 50, then Stage 80's 54, 59, 52, 53, 55-58, 61, 62, the
NHL/NBA accuracy fix (the three forecasts compared on the same games), 63, 64 and Expand
all. All are built, guarded and queued on Mark's PC, one PR each, run by a pipelined queue
(the next item's suite runs while the one ahead is audited). Mark approved 63 and 64's renders.
Built beside the queue, each its own PR after Stage 80: the NHL board's eyebrow (Mark's yes
10-15) and Stage 44's PRs 2 and 3.
First, by Mark's call 10-15: the NBA tip-time fix (Stage 77 item 33 read opening night's real 3 PM
BOS at DET as a placeholder; ESPN's own `timeValid` flag is read instead), PR from branch `nba-tip-flag`.

**Decided, Mark 2026-10-14:** results read **Correct / Missed** on every surface and every sport
(Stage 77 item 26; this replaces Stage 64's "right so far"). Stage 78 item 36 takes option B: the
home's font sizes move onto tokens, with one new token `--fs-40` for the hero. Stage 78 item 37's
three tag tones (filled, outlined, accent) are approved as rendered. Item 40's 72ch is about
100-115 characters a line in this face. Item 42 moves the four surfaces the audit names to
`--surface-2` and leaves the More sheet's items alone. Merging Stage 79 and 80 items is granted.

**NBA goes live on Tue 10-20** (Stage 65). Its block (item 60 and B1-B5) is merged.
A reminder is set for the night itself.

**Week 6 locks Thu 10-15**, the first week under v2.6 (HOU at JAX in London is neutral). Reminder set.

**Watching:** the first missed-dispatch alerts (#433) on the Thursday lock 10-15 and Saturday 10-17
(the NBA's 16:00 slot fired on time 10-14); the QB routine's Wed 22:00 UTC run (prompt fixed 10-13);
issue #428, whose first test since #429 is the 10-14 nightly shuffled suite (GitHub starts it hours late).
10-13's NHL games still show as Live because the saved status is stale (Stage 80 item 61,
live scores, is the fix). Issue #483 (Booth's alert for #482, cleared by a re-run) waits for Mark.

**Single next action:** watch the Stage 79 queue (45, 47, 49, 50) through to its wrap-up.

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| Stages 79-80 (UI/UX audit) | 75-78 done; 60, 51, 48, 46 done | 79 in order, then 80 |
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
- **Mark's PC runs on Eastern time**, so a guard for an ET clock runs node with `TZ` far from ET, or a dropped `timeZone` survives there (Stage 77 item 30).
- **The plain-language guard reads only `RENDERERS`**: add each new markup function with its page; a top-level literal is charged to the function above it (items 28, 31).
