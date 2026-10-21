# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history; history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-10-21 (session 1020, Tuesday night, Wednesday UTC: Stage 43 items 1-4 done; NBA browser checks and NFL Line Judge on-time fixed; item 5 waits for Mark)

---

## Right now

**Suite:** run it before quoting it; CLAUDE.md's `Suite:` line is the checked
figure. The NFL lives in `src/sports/nfl/` and `*/nfl/`; shared modules in `src/core/`.

**The product is Sportalytics** (Stage 67). **Live:** home `/`, NFL `/nfl/` (Model **v2.6**),
NHL `/nhl/` (day board), NBA `/nba/` (day board; **opened Tue 10-20**, picks saved, live scores #507 running).
One theme key, `site:theme`.

**The 2026-10-13 UI/UX audit is done** (Stages 75-80, #436-#513; items by PR in `memory/2026-10-15.md`
and `memory/2026-10-16.md`; text in `docs/history/09-more-sports.md`). Stage 44 (Line Judge) is done, and
its NFL on-time check now skips GitHub's late copy of a slot a dispatch served (#537), as the daily runs do (#521).

**Stage 43 (Spotter):** items 1-4 are merged (#524, #525, #527, #535). Spotter renders the pages, reads the head
and base pictures, and posts one comment; `tests/spotter_fixtures/` holds a planted-defect page it must name and a
clean change it must not blame (recorded readings, re-checked free on every suite run). **Item 5 waits for Mark**: it
edits `BOOTH_PROTOCOL.md` and Booth's instructions so Booth cites Spotter, and Scout's pre-flight needs a
"Human review required:" line. Do not start it without him.

**Decided, Mark 2026-10-14:** results read **Correct / Missed** on every surface and every sport
(Stage 77 item 26). Stage 78 item 36 option B: font sizes on tokens, one new `--fs-40`. Item 37's three tag
tones approved. Item 40's 72ch is about 100-115 characters a line. Item 42 moves four surfaces to `--surface-2`.

**Week 6 locked Thu 10-15** (first week under v2.6). Week 7 locks Thu 10-22, 11:00 UTC.

**Watching:** the Line Judge weekly digest failed at "Post the digest" on its first run (Mon 10-19, #529); the run
page shows only "exit code 1" and logs need a sign-in, so the cause is unknown until someone reads the step's last
lines (or Mon 10-26 runs). The missed-dispatch alert (#433); the QB routine's Wed 22:00 UTC run; issue #428.
The NBA's first night (10-20) was never looked at by eye this session: open `/nba/` and look.

**Single next action:** Mark runs a **Fable audit tomorrow (10-21) on criteria other than UI/UX**. Read what it
finds, turn the findings into staged items in the "Stage N - Short Name" chat format with a numbered-objectives
stage and an honest sequencing call, and put them in the Progress tab. Before that, ask Mark about #530 (week 7
QB override, Darnold for Lock at SEA, inferred from the coach's remarks, must merge before the Thu 10-22 lock) and
about #529's log.

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| Fable audit (non-UI criteria) | Mark runs it 10-21 | Its findings |
| Stage 43 (Spotter) | Items 1-4 done; 5 not started | Mark's go (edits Booth's instructions) |
| #530 (week 7 QB override) | Open, Booth SAFE, one watch claim unverifiable | Mark, before Thu 10-22 11:00 UTC |
| #529 (digest failed) | Open issue | The failing step's log, or the 10-26 run |
| Stage 42 | Items 1-4 done | 5: after four on-time weeks |
| Stage 39 | Items 1-4, 7 done | 5 in December; 6 wants a rendered choice in January |
| #428, #431, #528 | Open (#528 is stale: Mark closes it) | Mark |
| Stage 40 | Not to be touched | Mark |

One branch at a time. Full suite and mutation scope at the head, case files listed, a bounded
check for Booth. Never start the mutation runner under pythonw, and never two runners at once.

## Known and deliberately not fixed

- **Spotter's reading job takes its protocol and its checker from the pull request's base**, so it skips (and passes) on a base that predates them.
- **Spotter's clean-control key is looser than first written**: a problem is allowed only where its bullet says the base picture shows it too (the real reading listed base-present problems). Disclosed in the fixture and in #535; Mark has not yet ruled on it.
- **Spotter's head and base pictures can differ by a few antialiased pixels**; no pixel comparison is made on purpose. Both checkouts take full history because the NFL page reads the git log.
- **A browser check that assumes the pre-season page ages out on opening night.** `tests/browser/pre_opening.py` rewinds a built NBA page (no picks, every game scheduled); the countdown, rows and accuracy checks read it (#536). A new check about a state the real page has left should do the same.
- **GitHub's cron starts hours late**; cron-job.org starts on time. Every Weekly update slot runs once (slot guard).
- **Booth's prose can disagree with its own verdict block** (#286 ... #433). Re-run once; red again for the same reason, merge and log it.
- **Booth can say NEEDS HUMAN REVIEW on an all-green PR** whose only unverified claims are browser renders (#437, #488, #490). That is Mark's call, not a re-run. The relaxed overnight rule (0 discrepancies, only renders, measurements or mutation scope unverified: merge) is **off unless Mark turns it on**.
- **Booth's runner has no Playwright**, so a Chromium claim in a PR body is UNVERIFIABLE there. Mark's PC has none either; the container has Playwright and Chromium and can run a `tests/browser` check, but its Python cannot install the repo's pinned pandas.
- **Scout's body check ties any number near a test file's name to that file's whole count**, and reads `--id "glob"` as a mutation scope: quote the file's total, and run mutation cases by exact id.
- **The PC merge scripts take the worktree's NAME (`lj7`), not its path**; a path stops the merge at "delete local branch" after GitHub has merged.
- **The file bridge can report a write and keep the old file**: commit to a new name, copy into place, compare hashes.
- **The drift check re-tests a growing sample every week**, so it will sometimes flag by chance.
- **A failed Thursday run leaves Thursday night's game unpicked** unless dispatched by hand that day.
- **GitHub moves `ubuntu-latest` to Ubuntu 26 from 2026-10-19; nothing here follows it.** All 35 `runs-on` are `ubuntu-24.04`, held by `tests/test_runner_image.py`. Moving is a deliberate change: run the suite and one of each writer on `ubuntu-26.04` first, then change WANT and every workflow together.
- **Mark's PC runs on Eastern time**, so a guard for an ET clock runs node with `TZ` far from ET, or a dropped `timeZone` survives there (Stage 77 item 30).
- **Mark's PC checks files out as CRLF (autocrlf)**: a test that builds CRLF by replacing `\n` makes `\r\r\n`; write both forms from LF yourself (#538).
- **Windows Python ships no tz database**: `ZoneInfo('America/New_York')` fails at import on Mark's PC and passes on Linux CI. Read Eastern time through pandas, as `src/sports/nfl/tv_channels.py` does.
- **A parametrize over a page script needs `ids=`**: unnamed, the script is the test id, and Windows refuses an environment variable over 32,767 characters (items 57, 61).
- **GitHub's runners are UTC**: a test that reads a clock passes on Mark's Eastern PC and fails in CI unless it pins `TZ` (#501).
- **`src/core` type-checks under strict mypy** (`test_sport_isolation`, `test_type_check`); a pre-flight without mypy misses it (#515, #516).
- **A PowerShell `>` redirect writes UTF-16**, which `git apply` refuses: write patches with `git format-patch -o`, or a Python script written with the file tool.
- **The plain-language guard reads only `RENDERERS`**: add each new markup function with its page; a top-level literal is charged to the function above it (items 28, 31).
