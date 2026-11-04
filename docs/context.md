# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history; history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-11-03 (session 1102, Monday night into Tuesday: Stages 81-90 written; 20 PRs merged; #582 waits on Mark)

---

## Right now

**Suite:** run it before quoting it; CLAUDE.md's `Suite:` line is the checked
figure. The NFL lives in `src/sports/nfl/` and `*/nfl/`; shared modules in `src/core/`.

**The product is Sportalytics** (Stage 67). **Live:** home `/`, NFL `/nfl/` (Model **v2.6**),
NHL `/nhl/` and NBA `/nba/` (day boards, picks saved twice a day). One theme key, `site:theme`.

**Stages 81 to 90** came from the 2026-11-02 review; their text and Mark's decisions are in
`docs/history/10-review-2026-11-02.md`, what shipped in `memory/2026-11-03.md`. Order: 81, 82, 86, 88 items 1-2,
83, 84 and 85, 89, 87; 90 last. Stage 81 is done; 82 has items 4 (#582, Mark) and 5 left; 83 items 1, 3, 5, 6;
84 items 4, 5, 7 open (1-3, 8, 9 on a branch); 85 items 1-3, 5, 6 (4 on a branch); 86 items 2, 4, 5, 7 (3 dropped:
no gain); 88 items 1, 3-5, 7; 87, 89, 90 not started.

**Booth audits run one at a time.** Two at once each time out at 20 minutes; one alone takes about 11. Opening or
pushing to a PR starts its audit, so open the next PR only when no audit is running. Mark has not answered
whether to raise `timeout-minutes` to 30; do not change booth-pr-audit.yml for it until he does.

**Merge rule (Mark):** Booth SAFE TO MERGE, 0 discrepancies, the audited head the PR's head, every check green;
`merge_item.py PR WT BRANCH "Title"` (it merges a LOCAL branch: for a branch pushed by SHA, `git branch NAME SHA`
first). A wrong description means a replacement PR at the same head, never a patch.

**Single next action:** merge s84a's PR before anything that adds a mutation case file: README's case floor
("over 400") is stale at 451 files and s84a moves it to "over 450". Then #585, then the queue below.

**Deadline:** the week 9 QB override PR (Mark's routine, Wed 22:00 UTC) must merge before Thu 11-05 11:00 UTC.
Stage 81's override watch alerts at Thu 02:00 UTC if it is still open.

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| #582 Booth post job (Stage 82 item 4) | Fully green on its own run; Human review | Mark merges; then #578, #580 close |
| #585 deploy per-job permissions | Booth SAFE; Run tests red on README's case floor | s84a merged first, then main into s82-deploy-job-perms-2 |
| s84a `s84-forward-test` (Stage 84 items 1-3, 8, 9) | Suite passed at da46967b | An audit slot |
| s85d `s85-strictly-before` (Stage 85 item 4) | Built on s84a; suite queued at d63d12d9 | s84a merged |
| s83a, s86f, s88a, s88f | Suites passed | One audit each |
| #570, #575 (Dependabot) | Fail tests and Booth | Mark: a Dependabot secret `CLAUDE_CODE_OAUTH_TOKEN`; which updates to take |
| Issues #428 #528 #529 #540 #543 and older alerts | Fixed or stale | Mark closes them; s83a closes future ones itself |
| Stage 43 item 5 | Not started | Mark's go (edits Booth's instructions) |
| Stage 42 item 5, Stage 39 items 5-6, #431, Stage 40 | As before | December, January, Mark |

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
