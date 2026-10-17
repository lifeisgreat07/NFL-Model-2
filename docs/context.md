# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history; history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-10-16 (session 1014-15, Friday: Stage 80 done, the audit complete; Stage 44 done)

---

## Right now

**Suite:** run it before quoting it; CLAUDE.md's `Suite:` line is the checked
figure. The NFL lives in `src/sports/nfl/` and `*/nfl/`; shared modules in `src/core/`.

**The product is Sportalytics** (Stage 67). **Live:** home `/`, NFL `/nfl/` (Model **v2.6**),
NHL `/nhl/` (day board), NBA `/nba/` (day board, empty until opening night). One theme key, `site:theme`.

**The 2026-10-13 UI/UX audit is done** (Stages 75-80; text in `docs/history/09-more-sports.md`).
Stages 75-79 are #436-#493 (by item in `memory/2026-10-15.md` and `memory/2026-10-16.md`).
**Stage 80 is done:** 54, 59, 52, 53 are #494, #496, #498, #499; 55-58 are #500, #501, #503,
#505; 61, 62 are #507, #508; the NHL/NBA accuracy fix is #510; 63 is #511; 64 is #512;
Expand all is #513; item 60 was #452.
**After Stage 80 (Mark's yes 10-16):** the NHL board's eyebrow names the week it shows (#514);
**Stage 44 is done:** Line Judge judges the daily runs and the refresh (#515), and a finding now
gets an agent's diagnosis on its alert, with a weekly digest on one standing issue (#516).

**Decided, Mark 2026-10-14:** results read **Correct / Missed** on every surface and every sport
(Stage 77 item 26; this replaces Stage 64's "right so far"). Stage 78 item 36 takes option B: the
home's font sizes move onto tokens, with one new token `--fs-40` for the hero. Stage 78 item 37's
three tag tones (filled, outlined, accent) are approved as rendered. Item 40's 72ch is about
100-115 characters a line in this face. Item 42 moves the four surfaces the audit names to
`--surface-2` and leaves the More sheet's items alone.

**NBA goes live on Tue 10-20** (Stage 65). Its block (item 60 and B1-B5) is merged.
A reminder is set for the night itself.

**Week 6 locked Thu 10-15** at cron-job.org's 11:01 UTC dispatch, the first week under v2.6.

**Watching:** the missed-dispatch alert (#433) on Saturday 10-17 (Thursday's lock and the NBA's
16:00 slot were dispatched on time); the QB routine's Wed 22:00 UTC run (prompt fixed 10-13);
issue #428, whose first test since #429 is the 10-14 nightly shuffled suite (GitHub starts it hours late).
Live scores (#507) are new: the first NBA night (10-20) is their first real test there.

**Single next action:** read Line Judge's first weekly digest (Mon 10-19, 08:23 UTC) and the
NBA's opening night (Tue 10-20); then Stage 43 (Spotter).

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| Stage 44 (Line Judge) | Done: #435, #515, #516 | Its first digest, Mon 10-19 |
| Stage 42 | Items 1-4 done | 5: after four on-time weeks |
| Stage 39 | Items 1-4, 7 done | 5 in December; 6 wants a rendered choice in January |
| Stage 43 (Spotter) | Not started | Next |
| #428, #431 | Open | Mark |
| Stage 40 | Not to be touched | Mark |

One branch at a time. Full suite and mutation scope at the head, case files listed, a bounded
check for Booth. Never start the mutation runner under pythonw, and never two runners at once.

## Known and deliberately not fixed

- **GitHub's cron starts hours late**; cron-job.org starts on time. Every Weekly update slot runs once (slot guard).
- **Booth's prose can disagree with its own verdict block** (#286 ... #433). Re-run once; red again for the same reason, merge and log it.
- **Booth can say NEEDS HUMAN REVIEW on an all-green PR** whose only unverified claims are browser renders (#437, #488, #490). That is Mark's call, not a re-run; on 10-16 he made it standing for the session (0 discrepancies, only renders, measurements or mutation scope unverified: merge).
- **Booth's step "Fail if Booth posted no report" can go red beside a SAFE verdict** (#440, 10-14). One re-run cleared it.
- **Booth's runner has no Playwright**, so a Chromium claim in a PR body is UNVERIFIABLE there.
- **The file bridge can report a write and keep the old file**: commit to a new name, copy into place, compare hashes.
- **The N1 back-check is exact on local Windows, close but not exact on Linux runners.**
- **The drift check re-tests a growing sample every week**, so it will sometimes flag by chance.
- **A failed Thursday run leaves Thursday night's game unpicked** unless dispatched by hand that day.
- **GitHub moves `ubuntu-latest` to Ubuntu 26 from 2026-10-19; nothing here follows it.** All 35 `runs-on` are `ubuntu-24.04`, held by `tests/test_runner_image.py`. Moving is a deliberate change: run the suite and one of each writer on `ubuntu-26.04` first, then change WANT and every workflow together.
- **Mark's PC runs on Eastern time**, so a guard for an ET clock runs node with `TZ` far from ET, or a dropped `timeZone` survives there (Stage 77 item 30).
- **Windows Python ships no tz database**: `ZoneInfo('America/New_York')` fails at import on Mark's PC and passes on Linux CI. Read Eastern time through pandas, as `src/sports/nfl/tv_channels.py` does.
- **A parametrize over a page script needs `ids=`**: unnamed, the script is the test id, and Windows refuses an environment variable over 32,767 characters (items 57, 61).
- **GitHub's runners are UTC**: a test that reads a clock passes on Mark's Eastern PC and fails in CI unless it pins `TZ` (#501).
- **`src/core` type-checks under strict mypy** (`test_sport_isolation`, `test_type_check`); a pre-flight without mypy misses it (#515, #516).
- **A PowerShell `>` redirect writes UTF-16**, which `git apply` refuses: write patches with `git format-patch -o`.
- **The plain-language guard reads only `RENDERERS`**: add each new markup function with its page; a top-level literal is charged to the function above it (items 28, 31).
