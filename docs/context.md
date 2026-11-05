# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history; history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-11-05 (session 1104, in progress: #598-#602 merged; audit 7 received, Stages 91-96 written)

---

## Right now

**Suite:** run it before quoting it; CLAUDE.md's `Suite:` line is the checked figure. NFL in `src/sports/nfl/`, shared modules in `src/core/`.
**Sportalytics** (Stage 67) is live: home `/`, NFL `/nfl/` (Model **v2.6**), NHL `/nhl/`, NBA `/nba/` (picks saved twice a day).

**Audit 7 (2026-11-04, executed)** wrote Stages 91 to 96 (`docs/history/11-audit7-2026-11-04.md`, with the response and
Mark's answers). Order now: the built queue below; then Stage 91's rest and 92, 93 together; 94 items 23, 25 (built), 26;
95 (31 after #601, as a second amendment); the model-changing items (94: 24, 27-30; 95: 35) as one registered shadow
"day-sport v2" (Mark agreed 2026-11-05); 96 alongside. Before 11-19: 94 items 23 and 25 and 95 item 31.
Stages 81-90 left: 82 items 4-5 (Mark's #582), 83 item 6 (s83f, Mark's token date), 85 item 2, 86 item 5, 88, 89, 87, 90.

**Booth audits run one at a time** (two at once time out at 20 minutes). Do not change booth-pr-audit.yml until Mark decides.

**Merge rule (Mark):** Booth SAFE TO MERGE, 0 discrepancies, audited head = PR head, every check green; `merge_item.py PR WT_NAME
BRANCH "Title"`. **At the final head, before opening:** prechecks (ruff, both mypy), every figure and mutation case by exact
id, the suite. **A branch made with `git worktree add -b X origin/main` tracks origin/main**: push it with `-u` (the
pre-flight chain now does), or the wrap-up's "nothing unpushed" test fails on it. **A branch that rewrites code re-anchors
the existing mutation cases on it, and re-runs them.** Render any page change in Chromium before opening (s91e's first
version broke the sidebar grid; caught only by the render).

**Single next action:** open s83r's PR when its pre-flight passes; then s85r, s86s, s85s (merge main, render), s86h, s86t,
then the Stage 91/93/94 branches, one audit at a time.

**Week 9:** no QB override PR was opened (the routine ran 22:06 UTC Wed and opened nothing); Thursday 11:00 UTC locks week 9.

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| s83r `s83-alert-repeats` (83.1) | 83b3e66c; body_s83r_final.md | Pre-flight (running), one audit |
| s85r `s85-rederive` (85.6) | 4cee82cb (tolerance 5e-4); suite 11838 at head | Pre-flight again (upstream fixed), one audit |
| s86s `s86-suite-split` (86.4) | 8df83009 | Pre-flight again (upstream fixed), one audit |
| s85s `s85-baseline-spread` (85.3) | 595b718f; no body; conflicts with #601's drift section | Merge main, render, body |
| s86h (86.7 function_source), s86t (86.2 shared table) | 11c37ee0, 4073f9ff; suites green | Bodies, pre-flight, audits |
| s91a (91.1 pull_check), s91b (91.2 schedule_guard), s91c (91.3 after_save), s91d (91.5-6 pick writer), s91e (91.4 site) | aae2eadf, a826514f, 316a500f, ecf81a93, 11f4d162 | Suites (chain), bodies |
| s93t (93.13 step timeouts), s94d (94.23, 94.25 disclosures) | 1736ab29, d9292d86 | Suites, bodies |
| Slow-test count | s85r pins 7 slow tests; s91c adds 2 | Whichever merges second updates `test_the_slow_marker_is_registered_and_used` |
| s83f `s83-credentials` (83.6) | 00e5ea0f | **Mark: the OAuth token's real expiry date** |
| #582 Booth post job (Stage 82 item 4) | Green; Human review | Mark merges; then #578, #580 close |
| #570, #575 (Dependabot) | Fail tests and Booth | Mark: a Dependabot secret; which updates to take |
| Issues: 11 "Booth audit failed", #543, #541, #540, #518, #517 | Stale | Mark closes them |

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
