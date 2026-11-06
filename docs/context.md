# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history; history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-11-06 (session 1105 wrap-up: #628-#668 merged; #670 in audit; #669 being split in three)

---

## Right now

**Suite:** run it before quoting it; CLAUDE.md's `Suite:` line is the checked figure. NFL in `src/sports/nfl/`, shared modules in `src/core/`.
**Sportalytics** (Stage 67) is live: home `/`, NFL `/nfl/` (Model **v2.6**), NHL `/nhl/`, NBA `/nba/` (picks saved twice a day).

**Booth audits run one at a time**, and a diff of about a hundred files runs out of the 20-minute job time (#669 twice,
#670 once, #667 once). Split a big change rather than re-running it. Do not change booth-pr-audit.yml until Mark decides.

**Merge rule (Mark):** Booth SAFE TO MERGE, 0 discrepancies, audited head = PR head, every check green; `merge_item.py PR WT_NAME
BRANCH "Title"`; re-run a failed or timed-out audit once. **At the final head, before opening:** prechecks (ruff, both mypy),
every figure and mutation case by exact id, the suite (the session archive's prep and go scripts; CLAUDE.local.md has the paths).
A body that must change after opening: close the PR and open a new one from the same branch.
**Rules that merged this session bind every branch behind them:** every workflow installs with
`pip install --require-hashes -r requirements.lock` (`tests/test_lock.py`); every python or pip step of an alerting scheduled
job has its own `timeout-minutes` (`tests/test_step_timeouts.py`); src/core, src/site, src/sports/nhl and src/sports/nba pass
`mypy --strict`; a new test file needs a line in the suite map (the file #670 adds) once #670 merges.

**Single next action:** land #670 (s96w). Its re-run audit was SAFE with 0 discrepancies at aa4c9ddb, but the session 1105
wrap-up commit then changed CLAUDE.md's Suite line on main, the line #670 rewrites. Merge main into s96w and keep #670's
five-way line, recomputed with `python -m src.agents.session_wrapup --suite-line`. Prep, push, and let the new head be
audited once. Then open s96r part 1 (below), and cut parts 2 and 3 one at a time after it.

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| #670 s96w `s96-suite-line` (96.51: five-way suite split by a committed map of test files) | aa4c9ddb; SAFE on its re-run; main has since moved (wrap-up commit, CLAUDE.md) | Merge main, recompute the Suite line, one audit of the new head |
| s96r part 1 `s96-require-tool-1` (96.48: require_tool, injuries collection, first third) | Worktree s96r1, 5fab352c, not pushed; its body and the script that writes it are in the session archive (CLAUDE.local.md) | #670 merged; then merge main, prep, open |
| s96r parts 2 and 3 | The session archive's split_s96r script (argument 2 or 3) cuts each from branch `s96-require-tool` (the whole change, #669 closed) onto main; part 3 carries the guard test | Each after the part before merges; bodies modelled on part 1's, counts by the archive's part_counts script |
| Stage 87 items 2-4 (core Python move; one page renderer; app.js split) | Not built | After the queue |
| Stage 95 items 31-34, and 35 as the registered "day-sport v2" shadow (with 94 items 24, 27-30) | Not built | After the queue |
| s83f `s83-credentials` (83.6) | Built | **Mark: the OAuth token's real expiry date** |
| #582 Booth post job (Stage 82 item 4) | Green; Human review | Mark merges; then 82 item 5 |
| #664's auto-merge | Merged, off | **Mark sets AUTO_MERGE_OVERRIDES=true** when he wants it; the workflow file is read from the PR on `pull_request` (disclosed) |
| #570, #575 (Dependabot) | Fail tests and Booth | Mark: a Dependabot secret; which updates to take |
| Stage 88 item 1 (actions): one dispatch of each writer | Not done | Mark (dispatching the Weekly update can lock a week) |

## Known and deliberately not fixed

- **34 saved live picks were fitted on games of their own slate day** (5 NBA, 29 NHL; 26 earlier NHL picks
  cannot be checked). Saved picks are never rewritten; s85d lists them in both registrations and fits per day.
- **Booth's post job needs the Write tool**: told to write a file without it, Booth ends with permission denials
  and no report (#578, #580). Keep Write in `--allowedTools` while the report is a file.
- **Force-killing the mutation runner leaves its mutation in place**, and editing a worktree while its suite runs
  tests no commit. Let both finish.
- **Spotter's reading job takes its protocol and its checker from the pull request's base**, so it skips (and passes) on a base that predates them.
- **Spotter's clean-control key is looser than first written**: a problem is allowed only where its bullet says the base picture shows it too (the real reading listed base-present problems). Disclosed in the fixture and in #535; Mark has not yet ruled on it.
- **Spotter's head and base pictures can differ by a few antialiased pixels**; no pixel comparison is made on purpose. Both checkouts take full history because the NFL page reads the git log.
- **A browser check that assumes the pre-season page ages out on opening night.** `tests/browser/pre_opening.py` rewinds a built NBA page (no picks, every game scheduled); the countdown, rows and accuracy checks read it (#536). A new check about a state the real page has left should do the same.
- **GitHub's cron starts hours late**; cron-job.org starts on time. Every Weekly update slot runs once (slot guard).
- **Booth's prose can disagree with its own verdict block** (#286 ... #433). Re-run once; red again for the same reason, merge and log it.
- **Booth can say NEEDS HUMAN REVIEW on an all-green PR** whose only unverified claims are browser renders (#437, #488, #490). That is Mark's call, not a re-run. The relaxed overnight rule (0 discrepancies, only renders, measurements or mutation scope unverified: merge) is **off unless Mark turns it on**.
- **Booth's runner has no Playwright**, so a Chromium claim in a PR body is UNVERIFIABLE there. Mark's PC has none either; the container has Playwright and Chromium and can run a `tests/browser` check, but its Python cannot install the repo's pinned pandas.
- **Scout's body check ties any number near a test file's name to that file's whole count**, and reads `--id "glob"` as a mutation scope: quote the file's total, and run mutation cases by exact id.
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
- **Booth runs out of its 20-minute job on a diff of about a hundred files** (#669 twice). Split the change; parts that
  import a new helper are cut after the helper's part merges.
- **A test that calls a writer's `main()` writes into the real `data/` on a runner** when the code records only under
  `GITHUB_ACTIONS=true` (#661). Such a test chdirs to its tmp folder and pins the runner variables; reproduce with
  `GITHUB_ACTIONS=true` set on the PC.
- **One process per worktree**: mutation cases run while that worktree's suite runs fail the suite.
- **Scout's pre-flight reads `--durations=0 tests/test_x.py` as a count of 0 for that file**: put the flag after the files.
