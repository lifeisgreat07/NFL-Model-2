# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history; history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-11-23 (session 1122: Sunday 2026-11-22 with Mark, then overnight with Mark asleep; #798 to #808)

---

## Right now

**Suite:** run it before quoting it; CLAUDE.md's `Suite:` line is the checked figure, split five ways by `tests/suite_classes.json` (`session_wrapup --suite-line` writes it). NFL in `src/sports/nfl/`, shared modules in `src/core/`.
**Sportalytics** (Stage 67) is live: home `/`, NFL `/nfl/` (Model **v2.6**), NHL `/nhl/`, NBA `/nba/` (picks saved twice a day). **MLB's day board is built and tested but not published** (Stage 100 item 1, #808: `src/sports/mlb/site.py` and `pages/`, layout A, Board tab only, no picks until Stage 101 defines the pick file; `build.SPORTS` does not list MLB). March Madness (Stage 103) is built; its page and card appear only from the lock to 15 April.

**Run tests has 35 minutes (#748)**; it took 17-28 min tonight. **Booth audits run one at a time**; it timed out twice on #799 (Mark: merge) and its report check failed once on #805 (a re-run passed). Do not change booth-pr-audit.yml until Mark decides.

**Merge rule (Mark):** Booth SAFE TO MERGE, 0 discrepancies, audited head = PR head, every check green; `merge_item.py PR WT_NAME
BRANCH "Title"`; re-run a failed or timed-out audit once. **At the final head, before opening:** prechecks (ruff, both mypy),
every figure and mutation case by exact id, the suite (the session archive's prep and go scripts; CLAUDE.local.md has the paths).
A body that must change after opening: close the PR and open a new one from the same branch.
**Stacked branches (session 1122):** after the PR below merges, merge main into the next branch, re-prep, then open, and check the new PR's `mergeable` at once (GitHub marked #801 and #802 conflicting and ran no checks though `git merge-tree` was clean).
**Mutation scope = every case whose target or tests file the branch changes** (session archive scope_by_target.py; full_prep.ps1 -Scope).
**Rules on main that bind every branch:** every workflow installs with `pip install --require-hashes -r requirements.lock`;
every python or pip step of an alerting scheduled job has its own `timeout-minutes`; src/core, src/site, src/sports/nhl,
src/sports/nba and src/sports/mlb pass `mypy --strict`; **a new test file needs a line in `tests/suite_classes.json`**, and two
branches adding lines beside each other conflict there, so merge main before opening; **no test skips on a missing node by
hand**: `require_tool('node')`; **every mutation case names its real file**; **a new page meets every page guard at once**
(CSP `PAGES`, `SPORT_SHEETS`, Spotter's `RULES` and spotter.yml paths, the day boards' three-way copy guard).

**Single next action:** check that Tuesday's Weekly update (2026-11-24, 11:00 UTC) ran: it locks all of week 12, because GB at LA kicks off Wednesday, before Thursday's usual lock; if it failed, dispatch it by hand before Wednesday 20:00 ET. Then MLB Stage 100 item 3 (standings odds by simulation, independent of the pages), then item 2 (the other pages, options rendered first).

**Audit 9** is done: the last part, the drift paragraph as a table, merged as option B on Mark's behalf (#807). **The order of work (Mark, 2026-11-11, 2026-11-13):** the v2 shadow (done) and v3 (registered #732, writers open); 97-101 (MLB); 103. **Audit 8** is answered. Stages 102 and 104, Stage 95 items 31 to 35, Stages 97 and 98 are done.

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| v2 and v3 shadows (Stage 95, Stage 105) | Writers live (#721, #722; #740, #741); each saves only the picks its own run saved (#736) | Decided once after the 2026 regular season |
| MLB Stage 99 (model and backtest) | History, tuning, market, confirmation code, audit 8 fixes (#728-#735) | Retrosheet's 2026 log (gl2026.zip was 404 on 2026-11-22), then `python -m src.sports.mlb.backtest confirm`, once |
| MLB Stage 100 | Item 1 done: series place (#800), unset start (#805), the board (#808), not published | Items 3 (standings odds), 2 (other pages, rendered options first), 4 (home card countdown, browser checks, isolation read-set) |
| MLB Stage 101 | Not started: forward-test registration, daily run writing `results/mlb/schedule_<season>.json` and the pick file, canary, starters routine, going live | Opening Day 2027 (Thu Mar 25); probables timing measured in spring training |
| NCAAM Stage 103 | Everything built (#743-#787) | The lock between Selection Sunday and the First Four: dry-run the field read first |
| NFL week 12 | Locks on Tuesday's run (GB at LA, Wednesday 20:00 ET) | A QB override must be merged before Tue 06:00 ET; AUTO_MERGE_OVERRIDES is off |
| #582 Booth post job (Stage 82 item 4) | Green; Human review | Mark merges; then 82 item 5 |
| AUTO_MERGE_OVERRIDES | Off; weeks 10 and 11 locked without their override PRs (#706, #791); #692 and #756 are those PRs, stale | **Mark sets AUTO_MERGE_OVERRIDES=true** when he wants it; closes #692 and #756 |
| #683 (Dependabot, the actions group, 7 major bumps; replaces #570/#575) | Fails tests, Booth, preflight, probe | Mark: a Dependabot secret; which updates to take |
| Stage 88 item 1 (actions): one dispatch of each writer | Not done | Mark (dispatching the Weekly update can lock a week) |
| Open alerts | #747 Line Judge digest failing since 2026-11-16; #797 NHL canary on the goalie page (the run itself now degrades, #799); #794 is spam (an outside link: do not open) | Mark |

## Known and deliberately not fixed


- **34 saved live picks were fitted on games of their own slate day** (5 NBA, 29 NHL; 26 earlier NHL picks
  cannot be checked). Saved picks are never rewritten; s85d lists them in both registrations and fits per day.
- **Booth's post job needs the Write tool**: told to write a file without it, Booth ends with permission denials
  and no report (#578, #580). Keep Write in `--allowedTools` while the report is a file.
- **Force-killing the mutation runner leaves its mutation in place**, and editing a worktree while its suite runs
  tests no commit. Let both finish.
- **Spotter's reading job takes its protocol and its checker from the pull request's base**, so it skips (and passes) on a base that predates them.
- **Spotter's clean-control key is looser than first written**: a problem is allowed only where its bullet says the base picture shows it too (the real reading listed base-present problems). Disclosed in the fixture and in #535; Mark has not yet ruled on it. **Spotter's head and base pictures can differ by a few antialiased pixels**; no pixel comparison is made on purpose. Both checkouts take full history because the NFL page reads the git log.
- **A browser check that assumes the pre-season page ages out on opening night.** `tests/browser/pre_opening.py` rewinds a built NBA page (no picks, every game scheduled); the countdown, rows and accuracy checks read it (#536). A new check about a state the real page has left should do the same.
- **GitHub's cron starts hours late**; cron-job.org starts on time. Every Weekly update slot runs once (slot guard).
- **Booth's prose can disagree with its own verdict block** (#286 ... #433). Re-run once; red again for the same reason, merge and log it.
- **Booth can say NEEDS HUMAN REVIEW on an all-green PR** whose only unverified claims are browser renders (#437, #488, #490). That is Mark's call, not a re-run. The relaxed overnight rule (0 discrepancies, only renders, measurements or mutation scope unverified: merge) is **off unless Mark turns it on**.
- **Booth's runner has no Playwright**, so a Chromium claim in a PR body is UNVERIFIABLE there. Mark's PC has none either; the container has Playwright and Chromium and can run a `tests/browser` check, but its Python cannot install the repo's pinned pandas.
- **Scout's body check ties any number near a test file's name to that file's whole count**, and reads `--id "glob"` as a mutation scope: quote the file's total, and run mutation cases by exact id.
- **The file bridge can report a write and keep the old file**: commit to a new name, copy into place, compare hashes. **A PowerShell `>` redirect writes UTF-16**, which `git apply` refuses: write patches with `git format-patch -o`, or a Python script written with the file tool.
- **The drift check re-tests a growing sample every week**, so it will sometimes flag by chance.
- **A failed Thursday run leaves Thursday night's game unpicked** unless dispatched by hand that day.
- **GitHub moves `ubuntu-latest` to Ubuntu 26 from 2026-10-19; nothing here follows it.** All 35 `runs-on` are `ubuntu-24.04`, held by `tests/test_runner_image.py`. Moving is a deliberate change: run the suite and one of each writer on `ubuntu-26.04` first, then change WANT and every workflow together.
- **Mark's PC runs on Eastern time and GitHub's runners on UTC**: a clock-reading test pins `TZ` (#501), and a guard for an ET clock runs node with `TZ` far from ET (Stage 77 item 30). **Windows Python ships no tz database**: `ZoneInfo('America/New_York')` fails at import on Mark's PC and passes on Linux CI. Read Eastern time through pandas, as `src/sports/nfl/tv_channels.py` does.
- **Mark's PC checks files out as CRLF (autocrlf)**: a test that builds CRLF by replacing `\n` makes `\r\r\n`; write both forms from LF yourself (#538).
- **A parametrize over a page script needs `ids=`**: unnamed, the script is the test id, and Windows refuses an environment variable over 32,767 characters (items 57, 61).
- **The plain-language guard reads only `RENDERERS`**: add each new markup function with its page; a top-level literal is charged to the function above it (items 28, 31).
- **A test that calls a writer's `main()` writes into the real `data/` on a runner** when the code records only under
  `GITHUB_ACTIONS=true` (#661). Such a test chdirs to its tmp folder and pins the runner variables; reproduce with
  `GITHUB_ACTIONS=true` set on the PC.
- **One process per worktree**: mutation cases run while that worktree's suite runs fail the suite.
- **Scout reads any "N passed" in a body as the whole suite's count, "N test" in a commit message as a suite count,
  and `--durations=0 tests/test_x.py` as 0 for that file**: say "all N of their tests pass", keep counts out of commits,
  put flags after the files.
- **The anonymous GitHub API allows 60 requests an hour**: poll Booth with the session archive's authenticated
  `scratch-nba/pr_runs.py PR --wait SECONDS`, not every 15 s anonymously.
