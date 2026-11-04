# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history; history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-11-04 (session 1103, Tuesday night: #588, #585, #589, #591, #592 merged; #593 in audit; eight branches queued)

---

## Right now

**Suite:** run it before quoting it; CLAUDE.md's `Suite:` line is the checked
figure. The NFL lives in `src/sports/nfl/` and `*/nfl/`; shared modules in `src/core/`.

**The product is Sportalytics** (Stage 67). **Live:** home `/`, NFL `/nfl/` (Model **v2.6**),
NHL `/nhl/` and NBA `/nba/` (day boards, picks saved twice a day). One theme key, `site:theme`.

**Stages 81 to 90** came from the 2026-11-02 review; their text and Mark's decisions are in
`docs/history/10-review-2026-11-02.md`, what shipped in `memory/2026-11-03.md` and `memory/2026-11-04.md`. Order:
81, 82, 86, 88 items 1-2, 83, 84 and 85, 89, 87; 90 last. Done: 81; 82 except items 4 (#582, Mark) and 5 (after
#582); 83 item 1's first half, items 2, 4, 7; 84 items 1-3, 6, 8, 9; 85 item 4; 86 items 1, 6. Built and queued
below: 83 items 5, 6; 84 items 4, 5, 7; 85 item 5; 88 items 1 (part), 6. Not started: 83 item 1's repeat counter;
85 items 1-3, 6; 86 items 2, 4, 5, 7; 88 items 1 (actions), 3-5, 7; 87, 89, 90. 83 item 3 deprioritised (11-03).

**Booth audits run one at a time.** Two at once each time out at 20 minutes; one alone takes about 11. Opening or
pushing to a PR starts its audit, so open the next PR only when no audit is running. Mark has not answered
whether to raise `timeout-minutes` to 30; do not change booth-pr-audit.yml for it until he does.

**Merge rule (Mark):** Booth SAFE TO MERGE, 0 discrepancies, the audited head the PR's head, every check green;
`merge_item.py PR WT BRANCH "Title"` (it merges a LOCAL branch: for a branch pushed by SHA, `git branch NAME SHA`
first; it removes the worktree first, so let any suite there finish). A wrong description means a replacement PR at
the same head, never a patch. **Before every push: `ruff check .` and both mypy commands from `.github/workflows/run-tests.yml`**
(the local suite runs neither; `scratch-nba/prechecks.ps1`). A figure from a scratch script goes into the body
with the script inline, or Booth marks it UNVERIFIABLE (#587).

**Single next action:** merge #593 (s88a) on a clean audit, then open s88f's PR, then the queue in order.

**Deadline:** the week 9 QB override PR (Mark's routine, Wed 22:00 UTC) must merge before Thu 11-05 11:00 UTC.
Stage 81's override watch alerts at Thu 02:00 UTC if it is still open. A check-in fires at Wed 22:40 UTC.

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| #593 s88a (Stage 88 item 1, node 24 in the test runs) | Suite 11708+1 skip at 0456d9e8 | Its audit |
| s88f `s88-escape-id` (Stage 88 item 6) | Suite queued at b27fbfba; cases caught | An audit slot; body ready |
| s84e (84.5 calibration), s84g (84.7 NHL Brier), s84m (84.4 NHL M2), s84n (84.4 NBA M2), s83f (83.6 credentials), s83e (83.5 injury rows) | Built, ruff/mypy clean, cases caught; bodies in `scratch-nba/body_<wt>.md` (s84n, s83e not written) | Suite then one audit each, in this order; s83f: **Mark's OAuth token expiry date** |
| s85e (85.5 season prices) | 3270bf6d, built on s83e | s83e merged (same registry amendment list) |
| #582 Booth post job (Stage 82 item 4) | Fully green on its own run; Human review | Mark merges; then #578, #580 close |
| #570, #575 (Dependabot) | Fail tests and Booth | Mark: a Dependabot secret `CLAUDE_CODE_OAUTH_TOKEN`; which updates to take |
| Issues: 11 "Booth audit failed: PR #N", #543, #541, #540, #518, #517 | Stale | Mark closes them; #428, #495, #529 close on their next green run (#591) |
| Stage 43 item 5; Stage 42 item 5, Stage 39 items 5-6, #431, Stage 40 | As before | Mark's go (43.5 edits Booth); December, January |

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
