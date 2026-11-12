# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history; history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-11-12 (session 1112 wrap-up: #699, #700, #701, #703 and #704 merged)

---

## Right now

**Suite:** run it before quoting it; CLAUDE.md's `Suite:` line is the checked figure, split five ways by `tests/suite_classes.json` (`session_wrapup --suite-line` writes it). NFL in `src/sports/nfl/`, shared modules in `src/core/`.
**Sportalytics** (Stage 67) is live: home `/`, NFL `/nfl/` (Model **v2.6**), NHL `/nhl/`, NBA `/nba/` (picks saved twice a day).

**Booth audits run one at a time**, and a diff of about a hundred files runs out of the 20-minute job time. Split a big change rather than re-running it. Do not change booth-pr-audit.yml until Mark decides.

**Merge rule (Mark):** Booth SAFE TO MERGE, 0 discrepancies, audited head = PR head, every check green; `merge_item.py PR WT_NAME
BRANCH "Title"`; re-run a failed or timed-out audit once. **At the final head, before opening:** prechecks (ruff, both mypy),
every figure and mutation case by exact id, the suite (the session archive's prep and go scripts; CLAUDE.local.md has the paths).
A body that must change after opening: close the PR and open a new one from the same branch.
**Mark: "you can handle merges"**: 0 discrepancies and all green merges even if Booth says NEEDS HUMAN REVIEW only for
a claim it did not re-run. **Mutation scope = every case whose target or tests file the branch changes** (session
archive scope_by_target.py; full_prep.ps1 -Scope); #702 missed two broken cases with a narrower list.
**Rules on main that bind every branch:** every workflow installs with `pip install --require-hashes -r requirements.lock`;
every python or pip step of an alerting scheduled job has its own `timeout-minutes`; src/core, src/site, src/sports/nhl and
src/sports/nba pass `mypy --strict`; **a new test file needs a line in `tests/suite_classes.json`** (#675); **no test skips on a
missing node by hand**: `require_tool('node')`, or a `skipif(... and not in_ci())` (#678); **every mutation case names its
real file**: the app.js parts, never `src/dashboard/app.js` (Stage 87 item 4, guarded by `test_no_mutation_case_names_the_whole_file_any_more`).

**Single next action:** read #705's Booth audit and merge on the rule; then open the v2 registration (`s95-v2-registry`) the same way (scoped prep, body, preflight, audit, merge), before any v2 fit.

**The order of work (Mark, 2026-11-11):** Stage 95 item 32, then the v2 shadow (registration first); 102; 97-101 (MLB); 103 (`docs/history/12-mlb-and-more-2026-11-11.md`). Stage 104 and Stage 95 items 31, 33, 34 are done.

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| Stage 95 item 32: `s95-day-blocks`, **#705** (b7aa1cfa) | Open; suite 13100 and all 116 scoped cases CAUGHT at that head | Booth; merge on 0 discrepancies and every check green |
| v2 shadow registration: `s95-v2-registry` (47e8acca, unpushed) | Built; two item 29 rules corrected before opening and disclosed (NBA short boxes allow whole-minute rounding; NHL three-way prices get their own band); body and ids in the session archive | Item 32 merging; open before any v2 fit. Then the NBA v2 code (`s95-v2-nba-backtest`, b63704dc, not run on real games): run it only after the registration merges. NHL v2 not started (its history has no neutral-site field for item 28) |
| Stage 102 league logos: `s102-league-marks` (2814a0e1, unpushed) | Built: option B with sidebar fit 2 (Mark, 2026-11-11), tests/browser/check_switcher_fit.py; the Audit Response Log entry's text is in the session archive for Mark | The v2 registration merging (Mark's order) |
| Stage 97 item 1: `s97-mlb-probe` (e3fa12b1) | Built: src/sports/mlb/data_probe.py and mlb-data-probe.yml; the PR's own check answers whether a runner reads the Stats API. Items 2-7's draft doc is in the session archive | Stage 102 merging |
| `fix-home-theme-button`: tests/browser/check_theme.py presses the home page's theme button | Not opened | Rebase on main keeping only check_theme.py; NEEDS HUMAN REVIEW by nature, so Mark's call |
| s83f `s83-credentials` (83.6) | Built | **Mark: the OAuth token's real expiry date** |
| #582 Booth post job (Stage 82 item 4) | Green; Human review | Mark merges; then 82 item 5 |
| #664's auto-merge | Merged, off | **Mark sets AUTO_MERGE_OVERRIDES=true** when he wants it; the workflow file is read from the PR on `pull_request` (disclosed) |
| #570, #575 (Dependabot) | Fail tests and Booth | Mark: a Dependabot secret; which updates to take |
| Stage 88 item 1 (actions): one dispatch of each writer | Not done | Mark (dispatching the Weekly update can lock a week) |
| Leftover branches | `s96-require-tool` (local, with its worktree on the local Windows machine), `s96-require-tool-2` (local and on GitHub), `s87-app-targets-1` (local and on GitHub; its commit message carried a number, so the same tree shipped from `-1b`) | Mark: delete them (a force-push or branch deletion was refused to this session) |

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
