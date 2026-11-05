# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history; history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-11-05 (session 1104, in progress: #598, #599, #600 merged; s85a in pre-flight)

---

## Right now

**Suite:** run it before quoting it; CLAUDE.md's `Suite:` line is the checked figure. NFL in `src/sports/nfl/`, shared modules in `src/core/`.
**Sportalytics** (Stage 67) is live: home `/`, NFL `/nfl/` (Model **v2.6**), NHL `/nhl/`, NBA `/nba/` (picks saved twice a day).

**Stages 81 to 90** came from the 2026-11-02 review (`docs/history/10-review-2026-11-02.md`; shipped: `memory/2026-11-03.md`
to `memory/2026-11-05.md`). Order: the queue below; then 85 item 2; 86 item 5; 88 items 1 (actions), 3-5, 7; 89, 87; 90
last. Done: 81; 82 except 4 (#582, Mark) and 5 (after #582); 83 items 1 (first half), 2, 4, 5, 7; 84; 85 items 4, 5; 86
items 1, 6; 88 items 1 (part), 6. Built, queued: 83 items 1 (repeat counter), 6; 85 items 1, 3, 6; 86 items 2, 4, 7 and the
wrap-up clock test. 83 item 3 deprioritised. 86 item 7's second half (module-level reads into fixtures) is proposed to Mark
as not worth doing; 88 item 1 (actions) waits for Mark because it asks for a dispatch of each writer (memory/2026-11-05.md).

**Booth audits run one at a time** (two at once time out at 20 minutes; one takes about 11): open the next PR only when none
is running. Mark has not answered whether to raise `timeout-minutes` to 30; do not change booth-pr-audit.yml until he does.

**Merge rule (Mark):** Booth SAFE TO MERGE, 0 discrepancies, audited head = PR head, every check green; `merge_item.py PR WT_NAME
BRANCH "Title"` (the worktree's name, not its path). A wrong description means a replacement PR at the same head. **At the final
head, before opening:** `scratch-nba/prechecks.ps1` (ruff, both mypy), every figure and mutation case (by exact id), the suite
(`chain_suites.ps1`, one at a time, labelled by head); scratch-script figures go in the body inline, checking any per-pick claim.
**A branch that rewrites code re-anchors the existing mutation cases on it, and re-runs them** (memory/2026-11-05.md).
A CI run that crosses 00:00 UTC fails the wrap-up date tests until s86c merges; re-run it.

**Single next action:** open s85a's PR when its pre-flight passes; then s86c, s83r, s85s, then the built branches below.

**Week 9:** no QB override PR was opened (the routine ran 22:06 UTC Wed and opened nothing); Thursday 11:00 UTC locks week 9.

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| s85a `s85-drift-looks` (85.1) | f67e25a0 pushed; body_s85a_final.md filled; 16 cases and the drift figures at head | Pre-flight, then one audit |
| s86c `s86-wrapup-clock` | 00b46926 pushed; body_s86c_final.md; 2 cases at head | One audit |
| s83r `s83-alert-repeats` (83.1) | 83b3e66c; body_s83r_final.md (SUITE_LINE left); 10 cases at head | Push, pre-flight, one audit |
| s85s `s85-baseline-spread` (85.3) | 595b718f, suite green; no body; edits the drift section s85a rewrites (expect a conflict) | s85a merged, merge main, render the checks pages, body |
| s85r `s85-rederive` (85.6) | f1ea8159: two slow re-derivation tests, 3 cases | Suite (chain), body |
| s86s `s86-suite-split` (86.4) | 8df83009: the wrap-up checks the split; 3 cases | Suite (chain), body |
| s86h `s86-test-helpers` (86.7) | 11c37ee0: one function_source; 3 cases | Suite (chain), body |
| s86t `s86-shared-table` (86.2) | 4073f9ff: the NHL e2e tests share a feature table (158 s to 48 s); 3 cases | Suite (chain), body |
| s83f `s83-credentials` (83.6) | 00e5ea0f fixes the anchor that failed at d0f7f5d4; no body | **Mark: the OAuth token's real expiry date** |
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
