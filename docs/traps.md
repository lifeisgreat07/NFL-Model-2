# Traps

Moved verbatim out of `CLAUDE.md` on 2026-09-29 (Stage 29, the CLAUDE.md
split). Read it at the start of any session that will open a PR, measure
a page or run the mutation corpus. An "above" or "below" that points at
the methodology or a stage now means `CLAUDE.md` or
`docs/stage-history.md`.

## The rules, on one screen

Each line is the durable shape of one or more entries below; the stories
follow. Read this list whole; read an entry when you are about to do what
it describes. (Stage 36 item 8, from the 2026-10-04 fourth audit: three
entries below each call themselves "the recurring one".)

**Numbers**
- A number in prose is a claim: quote the command that produced it, at a named commit, with its scope.
- Mutation counts: list the case files, say "run whole" and give the case-by-case count too; never quote a count from an `--id` glob.
- No counts in commit messages (scout-preflight fails them); run the suite before quoting it, with HEAD pushed.

**The mutation corpus**
- One runner at a time, from a hidden console; never in parallel, never while pytest or `git add` runs in the same checkout.
- After any interrupted run, `git status` and restore; stale `.pyc` files can make it lie.
- Editing template text or moving a function moves the anchors that quote it; re-anchor in the same PR.
- A fixture that raises reads as WRONG-GUARD with "Failures: none reported".

**Guards**
- Mutation-test every guard; a guard named after the instance that prompted it misses the class, so enumerate the class.
- An assertion over a scan needs a floor that the scan found something.
- A guard reading source counts commented-out markup; a regex on a class name matches its CSS too.

**Process**
- One PR open at a time; no commits to `main` while one waits; the full suite before any docs commit.
- A PR description is its own artifact, and Booth reads it once: get it right before opening.
- Before starting an item, `git log --grep` it: a handoff can carry finished work as open.
- Before blaming a stranger for a change, check this session's own commands.
- Booth runs under `main`'s CLAUDE.md, restored in its tree; stash it, as its prompt says.
- A scheduled run races every merge; the pushers catch up with `main` first.
- A migration or bulk rewrite never touches a record (`data/`, `experiments/`, `memory/`): an early Stage 52 run rewrote `data/agent_log.json`.
- Jobs an Actions outage cancelled stay cancelled until someone re-runs them from the PR page; Booth passing again does not re-run preflight or the browser check.

**The page**
- Render it and look at it; a measurement from one browser or font does not travel.
- Never sort by a fact the page does not show; there are two navigations; a wholesale `innerHTML` re-render destroys state.
- The template is parts: read it with `read_template()`, never one part as the page.

**This machine**
- The file bridge corrupts binaries and can report a write it did not make; check the hash.
- PowerShell: no heredocs, `>` writes UTF-16, `Set-Content -Encoding utf8` adds a BOM, `^{tree}` is mangled, `| Select -First N` stops the script.
- A Desktop Commander call drops after 60 seconds; GitHub's anonymous API allows 60 calls an hour.
- Windows Python has no time-zone database.
- Desktop Commander's `start_process` hands even `cmd /c` lines to PowerShell, which eats every `$name`: put anything with a variable in a script file.

## Environment traps

Moved from CLAUDE.md's "Environment and workflow" list.

- **THE FILE BRIDGE CORRUPTS BINARY FILES.** Three PNGs committed from the
  sandbox to the local Windows machine with `device_commit_files` each arrived about 4.5%
  larger, with a different MD5, and the call reported success. Carriage
  returns were added to the bytes, which is harmless to text and fatal to an
  image. What worked: base64-encode in the sandbox, commit the text, decode
  on the local Windows machine with a short script, and compare the MD5 to the sandbox copy.
  Staging the other way (device to sandbox) was not seen to do this, but
  check a hash before trusting a binary either way.
- **A file-bridge commit can report success and leave the old content in
  place.** Writing an edited file from the sandbox to the same destination
  path twice in a row wrote the FIRST version both times, with a `written`
  result each time. Caught only because a guard on `docs/context.md` failed
  twice with byte-identical output, including an unchanged line count,
  which is not what an edited file does. Staging under a new filename
  worked. **Verify the destination rather than the return value**, and read
  two identical failure messages from a file you just changed as evidence
  that you did not change it.
  **The cache is keyed on the sandbox side too** (2026-10-06, twice): re-staging an edited copy under
  the same staged path sent the first version, and a folder that already held a file of the same
  name kept it. Give every staged copy a name it has never had, and make the script that copies
  them into a worktree check every file's SHA-256 before it copies any.
- **`kill_run.ps1` kills every mutation runner, not just the one you mean.** On 2026-10-06 it was
  used to stop a branch's suite and also stopped the full corpus run at case 760, leaving
  `src/pipeline/paths.py` mutated in the `mutseq` worktree. While a corpus run is going, stop
  anything else by its process id (`taskkill /PID <n> /T /F`).
- **A figure slips into a commit message through a sentence about a test.** "by more than the
  50 its test allows" is a count; preflight's check caught it after the push. Describe the rule,
  not its number.
- **Killing a run mid-test can leave a mutation in place.** On 2026-10-06 a full suite killed
  while the mutation harness's self-test ran left `tests/mutation/selftest_fixtures/subject.py`
  edited in the worktree. Run `git status` after any killed run, and before quoting a suite.
- **A comparison of two empty frames always passes.** `test_a_games_features_use_only_earlier_days`
  (NBA, #319) cut its synthetic season before the first rated day and compared nothing; only its
  mutation case, a WRONG-GUARD, showed it. A test that compares slices asserts they are not empty.
- **An exact reproduction on Windows is not exact on Linux.** #319's body said the NBA confirmation re-run
  equals the committed file and printed True; on Booth's runner it printed False, every number within
  1.6e-16. A reproduction check for an audit compares numbers to a tolerance (1e-12), and a claim of
  byte-identity names the machine it was seen on.
- **Desktop Commander's `write_file` refuses to overwrite a file unless `mode` is given.** The
  refusal is an error, but a script started in the same breath runs whatever the file held before:
  twice on 2026-10-05 and 06 a commit went out with the previous commit's message. Pass
  `mode: 'rewrite'` on every write to a path that may exist.
- **The mutation corpus edits the working tree in place, and is now slow.**
  On 2026-09-24 a full run on the local Windows machine reached 104 of 328 cases in about 17
  minutes, on pace for close to an hour, not the six minutes recorded
  earlier. 328 was the size THEN: on 2026-09-26 after #120 it is 470 cases
  in 88 files, so a full run is well over an hour. Count before estimating
  (`sum(len(cases))` over `tests/mutation/cases/*.json`); Booth's #115 audit
  quoted the 328 as current. While it runs, do not run pytest, `git add`, or a
  second corpus run in the same checkout: a suite run during it failed a
  test for a mutation that was live at that moment. Killing it mid-case
  leaves that case's file mutated (`src/agents/scout_preflight.py` and
  `tests/test_dashboard_charts.py` both were), so run `git status` and
  restore after any interrupted run. Naming the ids a change touches, each
  run with `--id`, is the form preflight accepts when the full run won't fit.
- **Parallel corpus runs give wrong answers, even in separate worktrees.**
  On 2026-10-03, four runners in four worktrees reported 20 WRONG-GUARDs
  with "Failures: none reported". The same case run alone was CAUGHT; run
  one at a time, all 536 were. Started DETACHED, each runner's pytest
  children also opened a console window apiece, and Mark restarted the PC
  thinking something was wrong. Run ONE runner, from a hidden console
  (`Start-Process -WindowStyle Hidden`, many `--id` in one call), so its
  children share that console. Sequential, about 45 cases a minute here.

## Traps that have actually bitten

- **A handoff can carry finished work as open.** Stage 33 items 20 and 25
  shipped on 2026-09-29, but `docs/stage-history.md` never marked them
  DONE, so the 10-02 handoff and the next opening prompt listed both as
  "next". Before starting a queued item, `git log --oneline --grep "item
  <N>"` and grep for its test; mark an item DONE in the stage section in
  the same session it merges.
- **The dashboard template is parts now (#265).** Read it with
  `read_template()` (Python), `JOINED_TEMPLATE.read_text()` where a test
  held its Path, or `tests/template_source.js` (harnesses). Never open a
  part and treat it as the page: the stylesheet guards read the first
  `<style>` and the script guards the last `<script>` of the JOINED text.
  A mutation case targets the part holding its anchor; an anchor that
  spans a cut has to be rewritten against `src/dashboard/page.html`.
- **scikit-learn 1.9 deprecates `LogisticRegression(penalty=...)`.** Passing
  `penalty='l2'` or `penalty=None` raises a FutureWarning on every fit
  (removed in 1.10), and `get_params()` reports `penalty='deprecated'`. L2
  is `l1_ratio=0.0` with `C`; unpenalised is `C=np.inf`, bit-identical to
  `penalty=None` (`tests/test_model_specs.py`). Found 2026-10-02 writing
  `MODEL_SPECS`, whose registry text said `penalty='l2'`.
- **`:g` prints a Bonferroni level to six figures.** 1 - 0.05/3 rendered as
  "at 98.3333%" on every Stage 33 Model Lab row; Stage 5's 99.5% had never
  shown it. Seen only by rendering the page (#260). Round a printed level
  to two decimals before `:g`.
- **The browser pane serves a cached localhost page.** After regenerating
  `index.html`, the reload showed the old "98.3333%" while the file on disk
  said "98.33%". Load it with a query string (`index.html?v=<sha>`).
- **Model Lab ids repeat across stages.** Stage 6 and Stage 33 both have an
  R1 and an R2. The page writes "Stage 33 R1"; the tests matched by id alone
  and one asserted "R2 has no result" (Stage 6's). Match on (stage, id).
- **PowerShell 5's `Set-Content -Encoding utf8` and `Out-File -Encoding
  utf8` write a BOM.** A `.py` rewritten that way began EF BB BF. Write with
  `[IO.File]::WriteAllText(path, text, (New-Object System.Text.UTF8Encoding $false))`.
- **PowerShell mangles `^{tree}`** in `git rev-parse <sha>^{tree}`. Use
  `git show -s --format=%T <sha>`.
- **A count in a commit message fails scout-preflight even when the body
  discloses it.** Its advice ("if pushed, disclose") still leaves a red
  check. Keep counts out of commit messages; if one slips into a pushed
  commit that no PR or Booth report names yet, reword it and compare tree
  hashes, as #261 did.
- **The reproducibility audit passes or fails on GitHub depending on
  which runner you get.** On 2026-10-02, two dispatches of
  `run-backtest.yml` (`reproducibility_audit`) on the same commit
  (`0e590c0`), seconds apart, with identical package versions from the
  install log and the same `ubuntu-24.04` image: one REPRODUCED bit for bit,
  the other gave Model A log loss 0.6499472 against the published
  0.6498122 (Brier and AUC also outside the 5e-5 tolerance), and Model B
  moved in the sixth decimal. The market row was bit-identical on both, and
  each run's two passes agreed with each other. So the result depends on the
  machine, not the code or the data, and the likeliest cause is the CPU's
  SIMD width changing float sums over the ~48k plays a season (the same
  aggregation the pandas finding localised). That is a hypothesis: the runner
  CPU was not recorded. Booth's two audits of #256 hit one machine each, so
  the same claim was CONFIRMED once and a DISCREPANCY ten minutes later.
  Until the audit records the CPU, a NOT REPRODUCED on GitHub alone is not
  evidence against a PR. Rerun it, or run it on the local Windows machine,
  which has reproduced exactly every time.
- **On a pull request, Booth runs under `main`'s CLAUDE.md, not the
  PR's, by design.** claude-code-action restores a fixed list of paths
  from the PR's base branch before Claude starts (the .claude folder,
  the MCP and Claude JSON configs, .gitmodules, .ripgreprc, CLAUDE.md,
  CLAUDE.local.md and the .husky folder), so a PR cannot rewrite the instructions
  it is audited under. That is why Booth's runner reported an uncommitted
  CLAUDE.md edit after its mutation runs on #254 and #255: the "edit" was
  `main`'s copy over the PR's. It is not a leftover mutation. Stashing it
  and auditing the committed head is the right response. With it present,
  any test that reads CLAUDE.md measures `main`'s file against the PR's
  tree (#255's freshness test failed on old `src/*.py` paths that way).
  Found 2026-10-01 in the action's own security documentation
  (github.com/anthropics/claude-code-action, docs folder, security page).
- **Do not commit to `main` while a rebuilt branch waits to merge.** #255
  was rebuilt on `main`, then the Stage 33 registry went to `main`
  (`8ddbcec`), and the branch had to be rebuilt again and its suite rerun.
  A docs or registry commit that waits an hour costs nothing.
- **A mutation scope built from each file's `target` and `tests` misses
  cases.** `tests` is a list in some case files and a single string in
  others, and a case can override its file's `target` (the workflow cases
  in `weekend_refresh.json`). The first selection for the Ruff PR found 305
  cases; counting both forms and the per-case overrides found 547.
  Normalise `tests` to a list and read every case's own `target` and
  `tests` before deciding a file is out of scope.
- **`tests/test_wrapup_date_slack.py` fails across midnight.** It takes
  `TODAY = date.today()` at import, and the gate it checks reads
  `date.today()` again when it runs. A suite started at 23:59 that reaches
  the test after midnight fails both `day0` cases with "not today". Rerun
  it. The durable fix is for the test to pass its own date into the check.
- **A documentation commit goes straight to `main`, and the suite reads the
  documentation.** `21515bc` (2026-09-30) ran only the CLAUDE.md freshness
  test before pushing; `test_context_stays_short_enough_to_actually_read`
  caps `docs/context.md` at 70 non-blank lines, it had grown to 74, and
  `main`'s Run tests went red. Every pull request's merge then inherited the
  failure, so #251 showed a red check its own diff did not cause. Run the
  whole suite before pushing a docs commit, as for code.
- **Editing template text moves mutation anchors that quote it.** #251
  changed `width:${r.pct}%` to `width:${r.pct ?? 0}%`, the exact text an
  existing case found; only the full suite's anchor test saw it, after the
  branch was pushed. Run `tests/test_mutation_corpus.py` after any template
  edit, before the long mutation scope.
- **An exception inside a test fixture hides the test from the mutation
  runner.** The runner counts `FAILED` lines. A fixture that raises reports
  its tests as `ERROR`, and a `SystemExit` raised in one stops pytest before
  it reports anything, so both read WRONG-GUARD with "Failures: none
  reported" (#245's states builder, #248's scoreboard harness). A fixture
  that builds or runs something should record the failure and let each test
  assert on it; a builder a test calls should raise its own exception, and
  only its command line should turn that into an exit code.
- **A test of an environment variable inherits it from whoever runs the
  test.** #247's check that the mutation runner sets `PYTHONUTF8` SURVIVED
  its own mutation at first: the outer runner had already set the variable
  for the process running the test. Clear it with `monkeypatch.delenv` first.
- **A mutation can be equivalent without looking it.** #245's case removed
  the fixed past kickoffs from a synthetic stale preview; the week it copied
  had past kickoffs too, so nothing could catch it. Before writing a case,
  say what input would differ, and check the input actually differs.
- **Moving a function moves the mutation anchors that name it, even across
  modules.** #241 moved `current_season` from `src/pipeline/canary.py` to `src/pipeline/paths.py`; the
  canary's case still targeted `src/pipeline/canary.py`, and only the full suite's anchor
  test saw it. Grep the case files for every moved definition's text.
- **PowerShell's `>` writes UTF-16.** A `git diff > x.patch` made that way
  fails `git apply` with "No valid patches in input". Use
  `git diff --output=x.patch`.
- **A check that runs from a copy needs its imports checked against the
  copy.** `booth-pr-audit.yml` copies `booth_report_posted.py` and
  `booth_verdict.py`, and nothing else, out of the checkout before Booth
  runs, so the audit cannot edit the check that judges it. #219's first
  commit imported Booth's account list from `collect_agent_log.py`. Every
  test passed, because tests run inside the checkout; in CI "Fail if Booth
  posted no report" went red on a run whose report was sitting on the PR.
  The list moved into `booth_verdict.py`, and
  `tests/test_booth_report_posted.py` now reads the workflow's `cp` line and
  fails if a copied module imports a `src/` module that is not copied.
- **Moving a definition between files moves its mutation anchors.** The same
  PR's fix left two `collect_agent_log.json` cases anchored on text that had
  moved (BAD-ANCHOR, and two red anchor tests). Run the case files of every
  file a move touches, source and destination, before pushing it.
- **Run the whole suite before committing, not the tests you think are
  affected.** The hygiene branch added `referrerpolicy` to the logo tag and
  ran four test files; three node-harness tests elsewhere compare the
  rendered tag exactly, and the suite at the head of a long mutation run was
  red. The session archive's pr_verify.py now stops before the mutation
  run when the suite is not green.
- **`set /p` in cmd reads at most 1023 characters, and an unquoted comma
  list through `Start-Process` into a `.bat` splits on the commas.** A
  79-file scope list was cut to "...scor" and the run died on a missing
  file; another run silently covered only its first case file. Pass long
  lists to a Python driver (the session archive's pr_verify.py), never
  through cmd variables.
- **A reply can answer an earlier ask; match it by its send time.** Mark's
  "Comment updated" was sent at 20:36 local and answered the #216 fix; it
  reached the session after the #219 request, was read as #219's, and he was
  told his edit had not saved. The API had the facts all along: #216's body
  had changed, #219's had not yet. Before acting on a short reply, check its
  timestamp against the asks it could answer, and read the PR's `body` from
  the API (the new head's SHA in it) before waiting on a re-audit.
- **A multi-line mutation anchor fails on a working file with mixed line
  endings.** Desktop Commander's edit and append wrote LF lines into a CRLF
  workflow file; an anchor spanning two lines matched in one place and not
  another. Anchor on a single line.

- **An upstream tag can move while a PR is in review.** #208 said every
  pinned action's major tag "still points at the same commit today"; at
  19:30 UTC Anthropic moved claude-code-action's `v1` to v1.0.237, and
  Booth's re-audit called the sentence a discrepancy. A claim about someone
  else's repository is true only at the moment it was checked: say when.
- **Desktop Commander's `write_file` wrote a `.svg` as six bytes of
  binary.** It treats some extensions as images. Write SVG (and anything
  not plain text by extension) with a short Python script, and check the
  file parses. Separately, `--` is illegal inside an XML comment, so a CSS
  token name like `--n0` in an SVG comment breaks the file.

- **Scheduled Actions runs here start 3.5 to 6.5 hours late (since
  2026-09-24),** off-the-hour minutes included: canary up to 6h35m, the
  2026-09-24 Thursday lock at 19:34 for a 16:00 cron. Moving the minute does
  not help; only the start time does. So the Thursday lock is 11:00 UTC and
  `LOCK_SLACK` is 8h (#203). Nothing time-critical may sit within about 8
  hours after a cron, and "it hasn't run yet" is normal until then. Pull
  `created_at` for every schedule run from the API before concluding a run
  failed.
- **Evidence from before a rebase is evidence Booth cannot check.** #206's
  mutation run was quoted from a commit a rebase then replaced; Booth could
  not see that commit and said NEEDS HUMAN REVIEW. Stacking branches makes
  this certain. Run the suite and the mutation scope at the exact head you
  open, after the last rebase. If a figure must change after opening, edit
  the description: Booth re-audits on `edited`.
- **Run the full suite before starting a long mutation run.** `run_wt.ps1`
  runs the suite and then the mutation scope whatever the suite said. #205's
  first 45-minute run was void: ten tests had failed on an undefined
  function before it began, visible in the suite file from minute one.
- **A new `memory/` file needs its row in `memory/README.md` in the same
  commit.** `tests/test_workflow_docs.py` fails otherwise; `0c8574e` left `main`
  red for a few minutes on 2026-09-29. Run the suite before pushing a docs
  commit too.
- **GitHub can take many minutes to mark a locally merged PR merged.** #205
  showed open for about 15 minutes after its merge commit was on `main`;
  the next push to `main` seemed to wake it. `merge_pr.ps1` stops before
  deleting the branch, which is right: wait and re-check with the archive's pr_merged.py,
  never press Merge in the UI (it would add a second merge commit).
- **The device bridge drops a call after 60 seconds.** `Start-Sleep 120`
  in one call failed. Poll in steps under a minute; background anything
  longer with `Start-Process`.
- **`merge_pr.ps1` stops at "delete local branch" when a session-archive
  worktree has the branch checked out.** Remove the worktree first
  (`git worktree remove --force`; stop any `http.server` serving from it,
  which holds the folder open), then `git branch -d`.
- **"Desktop unchanged" needs the desktop numbers diffed, not a desktop
  look.** #201's first version made the reliability diagram's plot size
  come from its width at every width, not only on a phone, so the desktop
  plot grew from 390 to 406 units. The browser check at 1280px compared
  widths and text sizes and passed; Booth found it by diffing the base's
  constants against the PR's. When a change branches on a width, compare
  every desktop-side value with `main` before writing "unchanged", and
  hold the desktop values in a test as well as the phone ones.
- **`| Select -First N` on a PowerShell script's output stops the script.**
  Piping `prep_pr.ps1` through `Select-Object -First 12` ended it once 12
  lines had printed: the push had happened, but the background suite and
  mutation run never started, and nothing said so. Redirect a script's
  output to a file and read the file (`*> file`), or re-run only the tail
  (`start_run.ps1` in the session archive).
- **A helper's leftover message file became a docs commit's message.**
  `merge_pr.ps1` wrote `.commit-msg.txt` into the main checkout and left it
  there; the next docs commit, whose own write of that file was refused,
  used it, so `7ebf8b6` (a docs update) is titled "Merge pull request #200"
  on `main`. Not rewritten, since `main` is shared. `merge_pr.ps1` now
  deletes the file after merging. Check a commit's subject with
  `git log -1` before pushing it.
- **A SESSION CAN FORGET ITS OWN ACTIONS AND REPORT THEM AS A STRANGER'S.**
  The 2026-09-28 overnight session merged #148 itself at 02:59 UTC, then
  wrote into `docs/context.md` that "something other than this session"
  had done it, and asked Mark. Desktop Commander keeps its own call history
  on the local Windows machine, outside the repo, and `get_recent_tool_calls` with a `since`
  time answers "who ran this" in one call. Read it before calling any
  action on the local Windows machine unexplained.
- **WORK LEFT IN THE CLOUD SANDBOX DIES WITH THE SESSION.** The same night's
  log-loss row ("written and tested") and Stage 6 registration draft were
  never copied to the local Windows machine, and the next session found neither. Anything
  another session may need goes to the session archive on the local Windows machine, or it
  does not exist.
- **BOOTH COUNTS A MUTATION SCOPE CASE BY CASE.** A case file pulled in only
  because some of its cases override target/tests to a changed file: the
  runs here run it whole, Booth counts only those cases. #165 claimed 382
  (whole) and Booth derived 345, a DISCREPANCY until the description said
  both. State "run whole" and both counts; the scope checker script in the
  session archive on the local Windows machine (one-off-scripts) prints them.
  **That script was wrong until 2026-09-28 (#176).** For a file matched at
  the top level it counted EVERY case as case-by-case, including cases
  whose own target overrides to an unchanged file (`readme_and_docs.json`
  holds several). #173, #174 and #175 said 12, 34 and 14 case by case; the
  fixed script, run against `main` after #176, gives 9, 31 and 11. Booth confirmed all three (twice without
  re-deriving, once saying no override applied) and caught it on #176.
  Fixed in the script; the merged bodies are left as they are.
- **POWERSHELL `.Split('.json')` SPLITS ON CHARACTERS, NOT THE STRING.** A
  scope list built that way ran the wrong case files; use `-replace`. And a
  stop script that matches `run...ps1` also matches its own name
  (`kill_runs.ps1`) and kills itself: anchor on the path separator.
- **A PIXEL WIDTH MEASURED IN THE LOCAL BROWSER IS THIS MACHINE'S.** #165
  said 174px; Booth's runner measured 176px on both builds. Say "on this
  machine", or leave the figure out.

- **AN UNCLOSED CSS COMMENT SWALLOWS THE RULES AFTER IT, AND A TEST OF THE RAW
  TEXT STILL PASSES.** #155's first draft never closed the comment above its
  `@media` block, so the phone cards did nothing; every test read the rules
  from the template's text and passed. Rendering found it. A CSS guard reads
  the stylesheet with comments blanked out.
- **A SELECTOR ADDED TO AN EXISTING RULE CAN BREAK A TEST THAT READS THAT RULE
  BY NAME.** #156 grouped `.rel-how summary` onto `.onboarding-more summary`;
  `tests/test_orientation_banner.py` and a mutation anchor read
  `.onboarding-more summary{` literally and failed. Give a new component its
  own rules, or `git grep` the selector in `tests/` first.
- **PIXEL FIGURES DO NOT TRAVEL BETWEEN ENVIRONMENTS.** Booth's Chromium put
  the same build's text a few pixels, and on a long prose page hundreds of
  pixels, away from this session's (#155, #156). Say which environment
  measured a figure, give a range when two disagree, and never write one
  machine's pixel as a constant in code.

- **A NEW CSS CLASS NAME CAN ALREADY BE TAKEN.** #149's first commit named its
  label `.why-label`; `whyRow()` already used that class for the numbers
  panel's rows, and the new rule restyled them (uppercase, 11px, a 12px top
  margin). No test failed. Counting the class on the built page found it: 64
  on 16 cards. `git grep` a class name before introducing it, and count it on
  the rendered page after.
- **KILLING A MUTATION RUN MEANS KILLING ITS WRAPPER TOO.** Stopping only the
  pytest child let the wrapper script carry on to the next case. Stop the
  wrapper, then the runner, then pytest; `git status` after, and restore the
  one mutated file only once the diff is confirmed to be just the mutation.
- **A SCHEDULED RUN RACES EVERY MERGE.** The first weekend refresh (run
  36360495917) read everything and saved nothing: #143 merged between its
  checkout and its push, and the push was refused (issue #145). The scheduler
  starts jobs hours late, so "not at cron time" protects nothing. Since #147
  both committing workflows rebase onto main (`--autostash`) just before the
  commit. The window is now seconds, not closed.
- **SAY HOW A MUTATION SCOPE WAS COUNTED.** Booth twice read "every case file
  whose target names a changed file" as top-level targets only, and missed
  files counted through per-case targets (`case_studies.json`,
  `self_hosted_font.json`). Name those files in the body, as #146 and #147 do;
  a small script in the session archive (one-off-scripts, cases_rule_check) prints why each file counts.
- **A RENDERED COUNT NEEDS ITS CUTOFF, AND CARDS ARE NOT PAIRS.** #146 quoted
  11 and 14 overlapping cards; at the half-pixel cutoff it was 12 and 13 (the
  11 used 2px, the 14 counted pairs). State the threshold and what is counted.
- **RE-SENDING A FILE TO THE SAME PATH ON THE LOCAL MACHINE CAN LEAVE THE OLD ONE.** Once
  on 2026-09-27 the hash did not change. Use a fresh folder or name per
  revision and compare hashes before copying into the repo.

- **WINDOWS PYTHON HAS NO TIME-ZONE DATABASE.** `ZoneInfo('America/New_York')`
  raises `ZoneInfoNotFoundError` on the local Windows machine and passes on Linux CI, so a test
  can be green in CI and crash the tool locally, or the reverse. Convert
  through pandas (`pd.Timestamp(...).tz_convert('America/New_York')`), as
  `src/pipeline/weekly_update.py` and `src/pipeline/tv_channels.py` do. Found 2026-09-27.
- **GITHUB'S ANONYMOUS API IS 60 CALLS AN HOUR, AND POLLING SPENDS IT.** A
  poll that listed every job of every run for a PR burned it in minutes on
  2026-09-27, and the session archive's `merge_pr.ps1` then stopped at its merged check -- the safe
  direction, branch not deleted. Poll only the comments, and check
  the API's rate-limit endpoint (free) first. The merged check now falls back to the PR's
  HTML page, and its first draft matched ANOTHER PR's "Merged" badge in
  #131's timeline and called a closed PR merged: read the page's first
  `"state"` field and treat anything else as not merged.

- **A CHAINED MERGE COMMAND KEEPS GOING AFTER THE MERGE FAILS, AND DELETING THE
  BRANCH CLOSES THE PR UNMERGED.** 2026-09-26, #113: the merge was one
  PowerShell line, `git merge ... -m "..."` then push, then
  `git push origin --delete <branch>`. The PR title had double quotes in it,
  PowerShell split the `-m` argument, and `git merge` failed ("not something we
  can merge"). The line went on anyway: `push main` said everything was up to
  date, and the delete removed the remote branch, so GitHub closed #113
  unmerged. Recovered by pushing the branch back at the audited SHA and
  reopening the PR (the built-in browser is signed in to GitHub). Reopening
  re-runs Booth, which agreed. **Merge through
  the session archive's `merge_pr.ps1` or its equivalent**: the message comes
  from a file (`git merge -F`), every step checks `$LASTEXITCODE` before the
  next, and no branch is deleted until the API says the PR is merged. Note
  `$ErrorActionPreference = 'Stop'` is the wrong fix: git writes progress to
  stderr, so it stops the first `git checkout`.
  Same session, the older trap came back: a `.commit-msg.txt` write refused
  because the file existed, and the commit reused the old message. Write it with
  an explicit rewrite, then read `git log -1` every time.

- **QUOTE THE COMMAND YOU RAN, NOT A SHORTER ONE.** #105's body said
  `python -m src.pipeline.weekly_summary --season 2026` printed the summary. The run
  behind that sentence had passed `--log` and `--drift`; the bare command
  crashed on `Path(None)`, and Booth found it by running the sentence
  verbatim. The flags left out of the quote were exactly where the bug
  was. Copy the command from the terminal, never retype it from memory.
  Same evening: a refused write to `.commit-msg.txt` left the previous
  message in place, and the commit went up carrying it. **Read `git log -1`
  after every commit made from a message file.**
- **A TEST THAT SLICES "FROM HERE TO A LANDMARK" GROWS WHEN SOMETHING IS
  INSERTED BETWEEN THEM.** The drift step's guard read the workflow from the
  drift step down to the commit step. When the summary step was added in
  between, its own `if: ${{ !cancelled() }}` satisfied the assertion, and
  `drift-workflow-skipped-after-a-failed-lock` SURVIVED. Nothing about the
  drift step had changed. Bound a slice by the structure's own delimiter
  (the next `- name:`), not by a later landmark, and re-run a file's
  mutation cases whenever another branch adds to that file.

- **`index.html` in a working tree is rewritten by the test suite and by
  mutation runs, so it can be a MUTATED build.** Several tests call the
  generator, which writes the repo's `index.html`; during a mutation run
  that happens with a mutation applied, and the restore puts the template
  back but not the page. On 2026-09-23 a render of the scale branch showed
  "ATL   at   GB" spread wide on My Picks: the page had been built during
  `card-header-quiet-variant-inherits-flex`, with `display:block` removed.
  The template was fine. **Regenerate immediately before staging a page to
  look at it, and never render straight after a mutation run.**

- **A MISSING WEBFONT DOES NOT SHIFT A MEASUREMENT, IT CAN FLIP THE ANSWER.**
  The first reproduction of the Week Board sort defect ran from a `file://`
  copy in the cloud sandbox, where Google Fonts is blocked, and found **no
  defect at all**: the open list landed 9px inside the right edge. Same commit,
  same 390px viewport, same script — the fallback face is narrower, so the
  list, whose width is set by its longest option, simply fit. Fetching the
  eight woff2 files on the local Windows machine, staging them in and serving the page over
  localhost reproduced it immediately at 41px of overflow. The existing entries
  here say a rendered figure is a sum of text widths and is not portable
  between machines; this is the stronger form. **A layout defect measured in
  the wrong typeface can be absent rather than merely different, and absence
  reads as "I checked and it was fine".** Any render measurement states which
  face it was taken in, and a reproduction that finds nothing in an environment
  missing the webfont has found nothing about the page.
- **`document.fonts.check()` answers "is anything still pending", not "is this
  font loaded".** With no `@font-face` at all it returns **true**, because
  nothing is pending. It was used as the assertion gating three measurement
  scripts before that was noticed, which means those asserts proved nothing for
  as long as they existed. What actually distinguishes the two environments is
  the numbers themselves — 218px with the webfont against 205px without — or
  `[...document.fonts]`, which is empty when no face is declared. **A readiness
  check that is vacuously true when the thing is absent is worse than no check,
  because it is written in the place a reader looks for the check.**
- **AN ALLOWLIST THAT COVERS EVERYTHING MAKES ITS OWN INTERESTING BRANCH
  UNREACHABLE.** Two mutations against the new colour-pair guard SURVIVED the
  corpus: one gutted "report a pair nobody wrote down", the other gutted
  "report an entry that stopped being true". Both survived because today's
  palette reaches neither branch — every close pair is already accepted and no
  entry is stale — so the assertions ran over empty sets and passed whatever
  the code did. This is the same shape as the edge flip the day before, and the
  same shape as `check_scoped_test_counts` skipping a module that does not
  exist. The tell is structural and can be seen before writing the test:
  **if the guard's failure message can only be produced by data the repository
  does not currently contain, the guard needs synthetic inputs, not a better
  assertion.** Both rules are now plain functions checked twice, over the real
  palette and over a synthetic one carrying a deliberate collision.

- **A figure nobody can trace to a command is the worst kind of wrong, because
  it reads as evidence.** PR #67's body claimed the pre-PR tap target was
  `163x62`. It was `163x41`. Booth measured it against the exact commit the
  sentence named; so did I, afterwards, and got 41 too. The `88` was measured
  and the `62` was not — and it could not be traced to any run at all. Two
  things generalise. First, the tell was available at writing time: I could not
  have said which command produced it, and that question is the check. **Before
  a figure goes in a body, name the command that produced it, or delete the
  figure.** Second, it *understated* the improvement — +47px/+115% was written
  as +26px/+42%. A fabricated number does not flatter you; it lands anywhere,
  which is why "but it was in the right direction" is not reassurance. A third,
  smaller point: quoting a WIDTH in a before/after pair was wrong in principle,
  because `.pick-btn` is `flex:1` and its width follows the viewport while only
  the height is a property of the change.
- **Scope a figure to the commit it was measured at, and it survives the base
  moving.** This is the stronger version of the "number right when written,
  falsified by the base moving" trap below, and it was demonstrated rather than
  theorised. #66's body said "Measured at `4f76432`, after pushing". The branch
  later merged `main`, which moved the suite from 961 to 1044 and the corpus
  from 25 files to 28 — and Booth, rather than reporting four discrepancies,
  built a worktree AT `4f76432` and confirmed every one of them there. The
  prediction going in was that the merge would manufacture discrepancies; it
  did not, purely because the original author had written down which commit the
  numbers described. **Name the SHA next to the numbers.** The one claim that
  did fail was the one sentence carrying no scope: the opening "One commit.",
  falsified the moment a merge commit arrived.
- **Sorting by a fact you do not display.** #65 ordered the Week Board by
  kickoff. #67's first cut put the kickoff line on My Picks only. The Board
  therefore presented its cards in an order with nothing on the page to explain
  it — nothing errored, every test passed, and the only symptom was a human
  asking why one page had the date and the other did not. The durable shape is
  **an invisible sort key**: whenever ordering changes, check that the thing
  being ordered by is on screen. Now `board-card-loses-the-kickoff-it-is-sorted-by`
  in the mutation corpus.
- **A green suite does not prove a mutation corpus still works.**
  `test_every_anchor_still_matches_exactly_once` is parametrized per case and
  proves each `find` string still RESOLVES — it never runs the mutation. A case
  can therefore anchor cleanly and still be caught by the wrong guard, or by
  nothing. After merging two branches that had both edited
  the dashboard template (then one file), all 147 cases were run individually (147/147
  CAUGHT) precisely because clean auto-merge only means no two edits touched the
  same *lines*.
- **Booth's environment is not the same from run to run.** #67's audit drove
  headless Chromium and confirmed a rendered-geometry table. #66's audit, an
  hour later, had no browser, no Playwright and no `node_modules`, returned
  UNVERIFIABLE for the same class of claim, and fell back to CSS box-model
  arithmetic. Do not read UNVERIFIABLE on a render claim as doubt about the
  claim; check which runner it landed on. Conversely, do not assume a render
  claim will be checked just because one was last time.
- **Stack onto `main`, not onto an open PR, whenever the work allows.** The
  picks-card branch was cut from an open PR and merged another open branch in,
  so its diff against that base carried four already-merged commits: 15 files,
  1091 insertions, most of it already audited. Cherry-picking the single commit
  onto `main` produced 6 files and 334 insertions — the actual change. The two
  PRs then merged in either order, with a one-digit README conflict either way,
  verified by test-merging both directions before choosing.
- **Reading your own code back is not verification, and the failure is
  asymmetric.** Stage 8's design phase re-derived every numeric claim rather
  than believing it: contrast by recomputing WCAG luminance from the hex
  values, colour-blindness by running the Machado 2009 matrices and CIEDE2000,
  geometry by rendering in headless Chromium and reading
  `getBoundingClientRect`. That caught three false claims from Fable — and then
  two more of my own, in code I had just written and was confident about. One
  was a CSS comment asserting three rules shared a specificity so source order
  would decide; `.brand:hover .brand-mark .spin` is four classes and the rule
  it was supposed to lose to was three, so hovering the logo froze the loading
  spinner *and* hung the logic waiting for an animation that was no longer
  running. One wrong assumption, two failures, neither visible by re-reading.
  The other generalised a width measurement taken from one table row to rows
  that carry an extra element. **Measure the specific case; specificity beats
  source order; and a claim about rendered geometry is only true after
  rendering.**
- **An animated disclosure can leak its contents into the accessibility tree.**
  Replacing `display: none` with a `grid-template-rows: 0fr` transition
  animates beautifully and leaves the collapsed content readable by screen
  readers and findable by find-in-page, contradicting the toggle's own
  `aria-expanded="false"`. `display: none` had been doing that job correctly
  and the animation quietly removed it. Fix: `visibility: hidden` on the inner
  wrapper with `transition: visibility 0s linear var(--dur-slow)`.
- **A wholesale `innerHTML` re-render silently destroys interaction state.** An
  open breakdown vanished on a filter change. Whatever the user has toggled
  must live in `state` and be re-derived on render, and floating UI (tooltips,
  popovers) must live outside the rendered tree entirely. Worth naming because
  the same deliverable that recommended this rule did not follow it.
- **Naming a path in `docs/context.md` that does not exist fails the suite.**
  `tests/test_workflow_docs.py` parses these documents for path-shaped strings
  and asserts each one exists, and separately asserts `memory/README.md` lists
  every file in `memory/`. Both fired within a minute of a wrap-up commit that
  pointed at files delivered into a chat rather than committed. The guard is
  right; fix the doc, do not reword around it — and if the answer is that the
  files should not be in the repo, say so in the doc instead of implying they
  are coming.
- **A safeguard written down twice, both times as a benefit, hid what it broke.**
  A push made with the default `GITHUB_TOKEN` cannot trigger another workflow.
  The collector and the dashboard builder both documented that rule as loop
  protection, which it genuinely is. Neither noticed it also severs the
  handoff between them, so the collector wrote 44 audits to `main` and the page
  went on saying "The record has not been collected yet". Fixed with a
  `workflow_run` trigger and guarded by
  `tests/test_generated_data_reaches_the_page.py`. **Ask what a safeguard also
  prevents.** *(The builder was the Auto-regenerate dashboard workflow; Stage 8c
  phase 2 deleted it and moved the trigger to the Pages workflow. The guard
  moved with it — that is what the test is for.)*
  Note the general shape too: a step that runs, produces correct
  output, and has nothing downstream consuming it — the same shape as the
  collector itself having never run, one link further along.
- **Correct arithmetic on absent data still produces a lie.** Season Accuracy
  showed 64.3%, three flat trend lines, and a row reading zero-of-zero. Every number
  was computed correctly from what it was given. 2026 Week 1 had been graded
  before it was played, so an empty week became a row that reads "we got none of
  none right" and a second point for the chart to draw to — and underneath, the
  entire page rested on one week of the *previous* season. The `return {}`
  entry below is the same failure; this is what it looks like on a page.
  Absent inputs must be dropped where the data is built, not filtered downstream.
- **A sign error in generated prose is invisible.** The Week Board's
  "the betting line agrees" shipped on all sixteen cards with `spread_line`'s
  sign inverted — it is positive when the HOME team is favoured, and the card
  displays it negated, football-style. "Agrees" reads exactly as well as
  "disagrees". Caught only by loading the page and noticing the sentence
  contradicted the card's own Vegas line two inches above it. **The convention
  was already written down**, in `tests/team_dive_harness.js`; it was got wrong
  by assuming rather than reading. When copy is generated from signed numbers,
  execute it in a harness with mirrored inputs — `tests/test_why_words.py` does.
- **Renaming a piece of UI leaves references behind.** Retitling the Week Board
  toggle orphaned its own reset label, a line in the onboarding banner, and a
  sentence in Methodology. Third instance of this shape, after the mobile nav
  still listing Playoff Odds. `git grep` the old string before considering a
  rename finished.
- **A guard can ban a term and miss its abbreviation.** The jargon list held
  "confidence interval" while `95% CI` sat on the Week Board's every card.
  Anchor the abbreviation to a phrase that cannot false-positive (`95% ci`, not
  a bare `ci`) — a guard that cries wolf earns an allowlist entry and then gets
  ignored, which is worse than the leak.
- **Two CI jobs can disagree about the same commit, and the green one wins by
  default.** `run-tests.yml` was red on every pull request for days while
  `booth-pr-audit.yml` ran the identical suite green on the identical commit.
  Nobody investigated, because Booth is the job that gets read. The cause was
  the actions/checkout default of `fetch-depth: 1`: the tests here that read
  real git history skip without it (sixteen when this was written; at
  `3471df5` five, all in `tests/test_scout_preflight.py` -- four under
  `needs_history` and the one below), and one — `test_scout_preflight.py`'s
  exit-code test — built its fixture from the last three non-merge commits,
  found one, manufactured nothing, and failed on its own empty fixture. Both
  workflows now set `fetch-depth: 0` and that test skips instead of failing.
  **A red check you have learned to ignore is worse than no check.** When two
  jobs disagree, the difference is in the workflow files, not the tests.
- **A green checkmark on a Booth run means Booth posted a report, not that the
  report was favourable.** The workflow exits 0 whenever the audit completes.
  The verdict is in the comment text. PR #45's third audit was green in Actions
  and read NEEDS HUMAN REVIEW with four discrepancies.
  **AND THE STRONGER FORM, 2026-09-21: a green checkmark can mean Booth posted
  NOTHING AT ALL.** PR #80's first run reported Success and left no comment.
  The workflow asserts nothing about its own deliverable, so a run that
  produces no report is indistinguishable in the Checks tab from one that
  produces a clean one — the reassuring direction, silently.
  **The tell was the duration, not the absence.** It ran 3m55s against a range
  of 5m14s to 13m11s across the previous 24 runs, and the body asked for a
  full corpus run that takes about four minutes on its own, so it cannot have
  done the work. The Actions run list shows durations without signing in, and
  comparing against that range is the cheapest way to tell "audited and quiet"
  from "did not audit". Re-running the same commit, description and workflow
  produced a full 14-claim audit, so nothing about the PR caused it; the logs
  were never read, so the cause is still unknown and the usage theory is a
  theory. The durable point is not the cause: **the one thing that workflow
  exists to produce is the one thing it does not check it produced.**
  Now it does: the job's last step runs `src/agents/booth_report_posted.py`, which
  fails unless a bot comment posted during THIS run carries a verdict block
  naming the commit this run checked out. Consequence worth knowing: a PR
  that edits `booth-pr-audit.yml` itself now goes RED rather than green,
  because the action skips on it and nothing gets posted -- that is the
  check telling the truth, not a regression.
  **Its first live run caught the real thing.** PR #84's audit on
  2026-09-23 ran Booth for 5m08s, the action exited 0, and no comment was
  posted. The step failed the job, which would have shown green a day
  earlier. The duration was inside the old 5-13 minute "normal" range, so
  the duration tell from #80 would NOT have caught it. That tell was a
  heuristic, and this check is the actual control.
- **The `edited` trigger on `booth-pr-audit.yml` fires for the PR description
  only, and its `if:` guard additionally requires `github.event.changes.body`.**
  Editing a *comment* in the thread raises `issue_comment`, which that workflow
  does not listen to — so nothing starts and nothing explains why. If an audit
  seems not to fire after an edit, check whether the edit went into the
  description box at the top or a comment below it.
- **A document can point at a file that has never existed, for months.**
  `METHODOLOGY.md` was cited by the README's fifth line and two `src/`
  docstrings; `git log --all --diff-filter=A -- METHODOLOGY.md` returns nothing.
  `src/research/tune_qb_shrink_k.py` had already noticed and written it down, which fixed
  nothing, because a note is not a check. `tests/test_readme_accuracy.py` is now
  the check.
- **THE AUDITOR PRODUCES UNTRACEABLE FIGURES TOO, AND NOTHING AUDITS THE
  AUDIT.** #79's report was thorough and correct — 0 discrepancies, every
  command re-executed — and inside the claim it was confirming it wrote that
  `test_every_anchor_still_matches_exactly_once` passes for "204 parametrized
  cases (`204 passed`)". It is 203, on that commit, with 38 case files; the
  whole module is 619 tests, so 204 is not a wider-scope figure either. It is
  the untraceable-number defect this repository built Booth to catch,
  committed by Booth, in the sentence doing the catching. The conclusion was
  still right, which is exactly why it is easy to pass along.
  **A Booth report is evidence, not an oracle: check the figures inside it
  the way it checks the figures inside a PR body.** Two of the last two
  audits have now needed that — this one, and the header/block mismatch
  below — and neither was caught by any mechanical check on the report.
- **A GUARD CAN PRESCRIBE A REMEDY ITS OWN CODE REJECTS, AND THE READER WILL
  TRY THE REMEDY.** `check_visual_claims_have_artifacts` fails with "attach
  it, or state it as a process note rather than proof". There is no
  process-note path in the function: it passes on no keyword, or on an
  attachment, and nothing else. A body that did exactly what the message asked
  failed anyway on 2026-09-21. This is the "comment claims more than the code
  delivers" family with the claim moved into the failure message, which is
  worse, because a failure message is read at the moment someone is looking
  for the fix and is trusted more than a comment. **Whatever remedy a
  message names must be a branch in the function, or the message must not
  name it.**
  The same check failed for a second reason worth separating. `VISUAL_CLAIM_RE`
  matched the word "screenshot" **inside the disclaimer**, so disclosing
  honestly is what tripped it; and it does not match "rendered ... and read on
  screen", so deleting the word made the same body pass as "no visual claim
  made" while the claim was still there. Too narrow and too wide at once —
  the `p*` glob shape — and the reassuring direction is the silent one. A
  keyword matcher that gates on wording will eventually grade the disclaimer
  instead of the claim.
  *(Both halves fixed 2026-09-22, in `tests/test_guard_gaps.py`. The check
  now judges a sentence: one starting "Process note", or with a negation
  before the visual phrase, is a disclosure, and the regex also catches "on
  screen". A negation AFTER the phrase is not treated as a disclosure, except
  in the form "not attached", because "checked on screen that it does not
  overflow" is a claim. That boundary is a judgement, and it is written down
  so nobody has to guess it.)*
- **A guard whose rule names a forbidden string will match its own docstring.**
  Third occurrence this session. Exclude the file that states the rule, and say
  so in a comment — the alternative is describing the banned string obliquely
  enough to dodge your own regex, which damages the rule to protect the checker.
- **`git reset --hard` and `git checkout --` have destroyed in-progress edits
  three times.** Before any restore, check what is uncommitted; prefer
  re-applying a known edit over reverting a whole file. When mutation-testing a
  file that holds uncommitted work, restore from a byte-level backup taken in
  the script, never from git.
- **A guard wired into one of several paths reads as a guard that is present.**
  A churn pruner stopped the workflows committing their own build timestamps.
  It ran in only one of the two workflows that regenerated, and this file's
  prose said merely that it "prevents" the churn — which is what stopped anyone
  checking coverage. Both ran it after that, enforced by a test asserting that
  *any* workflow regenerating and committing those artifacts pruned between the
  two steps, so a third would inherit the guard instead of quietly missing it.
  The durable shape: prose names a protection but never its coverage, and the
  gap is invisible from the description alone. Ask which paths, and prefer a
  test that enumerates them over a sentence that asserts them.
  *(Both the pruner and that test were deleted in Stage 8c phase 2 — untracking
  index.html removed the churn entirely, so the guard had nothing left to
  guard. `tests/test_workflows_do_not_commit_build_output.py` now asserts the
  stronger invariant that no workflow commits those paths at all. The lesson
  above is kept because it is about prose and coverage, not about that file.)*
- **A zero-line binary diff is not automatically churn.** An auto-commit
  showing `dist/picks_2026_week1.pdf | Bin 3802 -> 3802 bytes, 0 insertions,
  0 deletions` looks exactly like the timestamp churn above, and on 2026-09-07
  I nearly reported the guard as broken on that basis. It was not.
  The pruner deliberately did NOT normalise the "generated
  `<date>`" line printed inside the picks PDF, because that is visible content
  on a page someone prints — a rebuild on a different day is a REAL change and
  should commit. The byte count is identical because a date string is the same
  length either way. Its docstring says all of this. Read what a normaliser
  deliberately excludes before concluding it failed; the symptom of "working
  as designed" and "broken" are byte-identical here.
- **A date recalled is a date invented. `git log` is three seconds away.**
  Writing the churn guard into `weekly-update.yml` on 2026-09-07, I annotated it
  "same guard the other workflow has run since 2026-08" — from memory, into
  a permanent code comment, in the same PR whose other half exists to correct an
  unverified inherited claim. It was 2026-09-04. The same wrong date went into
  two sentences of this file and into the commit message. Booth caught all three;
  `git log --format="%h %ad %s" --date=short -- <path>` confirmed it in one call.
  Provenance claims — when something landed, how long a file has said a thing,
  which commit introduced a behaviour — feel like recall and are actually
  queries. The tell is the phrasing: "since", "has always", "was originally".
  Any sentence carrying one is a claim that must be looked up before it ships,
  and note that a claim about what *this file* has said is dated by this file's
  own history (created 2026-09-05), not by the history of the thing described.
- **A number in prose is a claim, and prose has no test.** One habit produced
  four wrong figures on 2026-09-07, in four distinct ways. They are worth
  separating, because only one of them looks like carelessness:
  1. *Recalled, never measured.* "The guard has run since 2026-08" — it was
     2026-09-04. Written from memory into a permanent code comment, inside the
     PR whose other half existed to correct an unverified inherited claim.
  2. *A conclusion reported as a search result.* Correcting that date, I
     searched the two paths I already had in mind, found nothing further, and
     wrote "corrected everywhere". Booth found a third occurrence in a
     docstring, in a file the same branch had just added.
  3. *A judgement wearing the precision of a count.* "72 of the 73 matches
     were real history" — which ones count as history is editorial, and the
     phrasing left an auditor no way to tell which was excluded. Name the
     exception; never publish a subtraction.
  4. *Measured, and still unreproducible.* "The Playoff Odds page is 979
     characters" came from a real slice — that page's `id=` attribute to the
     next page's `id=`, a span running past the closing `</section>`. The
     element is 953; the visible text is 585. Booth measured six plausible
     ways and got none of them, correctly.

  Only the two that reached a re-runnable check were caught before shipping.
  Commit messages have no such check and cannot be corrected without
  invalidating the Booth reports written against those SHAs, so the discipline
  has to happen before the commit, not after.

  **A count of something that is IN THE REPOSITORY is a query, and counting it
  by eye off your own draft is the cheapest version of this mistake.** PR #77's
  body said five `ACCEPTED_CLOSE` entries read "Not traced". There are six;
  `grep -c "'Not traced" tests/test_dashboard_charts.py` says so in two
  seconds, and Booth reported it as the audit's single discrepancy. It then
  propagated into `docs/context.md`, the session memory and the Progress tab
  before anyone checked — and the Progress-tab entry wrote "five" directly
  above a list of six items, so the sentence contradicted itself on the page.
  There was no rebase, no wider command, no moved base: the number was simply
  never run. When the thing being counted lives in the repo, the command
  belongs beside the figure for the same reason a suite count does.

  **The rule.** A figure ships with the command that produced it, and a
  completeness claim cites a repo-wide search rather than the paths you
  happened to think of. A number whose method is unstated is unfalsifiable by
  anyone but its author — the same defect as not measuring at all.

  **The self-referential case.** A count of something its own sentence is part
  of must name the commit it was taken at. `git grep -n "2026-08"` returned 73
  matches across 12 files at `f482f4f`; every one is a real historical date
  except the line in this file quoting the mistake. A live figure written here
  would be wrong the moment it landed, because this paragraph contains the
  string.

  **None of it was catchable by a test.** All four are claims *about* the code
  rather than behaviour *of* it, and the suite was green throughout. Two
  independent Booth runs reached the docstring finding separately. That is the
  clearest evidence yet that Booth does something a suite structurally cannot,
  rather than agreeing with what it reads.
- `backtest()` calls `dropna(subset=features)`, so different feature sets can
  silently evaluate different game sets. Any paired comparison must verify the
  row sets match rather than assume it (`bootstrap_brier_gap.py` does, and
  `compare_pandas_versions.py` checks it before reading any metric).
- `home_margin` exists in the feature table for ATS work and must never enter a
  feature list — it is the scoreline being predicted.
- **Booth's sandbox has main's CLAUDE.md, not the PR's -- ON PURPOSE.**
  EXPLAINED 2026-09-23 from #94's Run Booth log: the Claude Code action
  prints "Restoring .claude, .mcp.json, .claude.json, ... CLAUDE.md,
  CLAUDE.local.md ... from origin/main (PR head is untrusted)". It swaps in
  main's copy of every file that could steer the agent, so a PR cannot
  rewrite its own auditor's instructions. So a PR that edits CLAUDE.md is
  always audited with main's CLAUDE.md on disk, and must be checked with
  `git show HEAD:CLAUDE.md`, which is what Booth's reports on this have
  done. The
  entry below was written before the cause was known and is kept as the
  record of how it looked from inside.
  ORIGINAL ENTRY -- **Booth's audit sandbox can check out a file one commit
  behind its own HEAD.**
  Flagged in three separate audits (PRs #28, #29 and #80), so it is the
  environment rather than a one-off. `git status` shows `CLAUDE.md` modified, the on-disk
  md5 matches `HEAD~1`, and `git reflog` records no second checkout — the
  working tree is simply not what HEAD says it is. Booth handled it correctly
  every time, verifying against the commit object (`git show HEAD:CLAUDE.md`,
  `git grep <rev>`) and saying so in the report. Consequence for a reader: a
  plain `git grep` run in that sandbox can disagree with a claim that is true
  of the commit. This is NOT a regression and NOT something a PR caused; do not
  spend a session chasing it. Verify against revisions, not the working tree,
  whenever the two could differ.
- **The Claude Code action refuses to run when a PR's copy of its workflow file
  differs from `main`'s.** It skips with a *success* status and a validation
  message, which looks like nothing happened. This is a security control, not a
  bug. Consequence: after changing `booth-pr-audit.yml` on `main`, any open PR
  must merge `main` in before Booth will audit it, and "re-run the job" does not
  help, because a re-run replays the original workflow definition.
  **NO LONGER TRUE SINCE #176 (2026-09-28).** The refusal belonged to the
  path where the action fetched the Claude app's token over OIDC. Handed
  `GITHUB_TOKEN`, it ran on #176, a PR editing its own workflow, and posted
  as `github-actions[bot]`. So a PR can now change Booth's prompt and be
  audited by the change; Stage 23 item 6 makes preflight demand a
  human-review line on any such PR.
- **The mutation runner's restore does not survive the process being killed.**
  It restores in a `finally`, which covers exceptions but not a hard kill. The
  Desktop Commander bridge cuts a command off at ~60 seconds and a full corpus
  run takes longer, so a run started in the foreground gets killed partway and
  leaves whatever case was in flight applied to the working tree. On
  2026-09-07 that left `src/agents/scout_preflight.py` mutated and the next suite run
  reported 8 unrelated failures. Two rules: run the corpus as
  `python tests/mutation/runner.py > <file> 2>&1` and read the file afterwards,
  never in the foreground; and after ANY interrupted mutation run, check
  `git status` before believing a test result. A `git checkout -- <one file>`
  is the right repair once the diff is confirmed to be only the mutation.
  **SECOND VARIANT, found by Booth on itself on #81: nothing else may read
  the working tree while the corpus is running.** It started the runner in
  the background and ran the full suite alongside it, and the suite caught a
  file mid-swap — `its anchor matches 0 time(s)` for the case in flight, plus
  four unrelated failures in a module the runner had not touched. Nothing was
  interrupted and the restore worked; `git status` was clean afterwards. The
  first variant is a runner that died and left a mutation applied, and the
  repair is to restore. This one leaves nothing to repair and produces a red
  suite whose failures point at innocent files, which is the more expensive
  shape because there is no residue to find afterwards. Backgrounding the
  runner is still right; running anything else against the tree while it
  works is not. Booth wrote its own error into the report rather than
  re-running quietly, which is the only reason it is recorded here.
- **Anything under a Booth fixture tree must be excluded from pytest
  collection.** `tests/booth_fixtures/conftest.py` sets
  `collect_ignore_glob = ['*']` for exactly this. A fixture is a deliberately
  bad PR: the moment one seeds a genuinely failing test, a collected fixture
  fails the real suite. It bit in a subtler form first — pytest imported a
  fixture's `test_guard.py`, created a `__pycache__` beside it, and the
  loader's tree walk then read a `.pyc` as UTF-8 and failed five fixture tests
  for a reason unrelated to anything they assert. It reproduced ONLY in the
  full suite; in isolation nothing collected the file and everything passed.
  A failure that appears only alongside everything else is the expensive kind,
  so the loader skips generated directories independently of the conftest.
- **Mutation cases live in `tests/mutation/cases/*.json` and run via
  `python tests/mutation/runner.py`.** Do not write a throwaway mutation
  script: every PR before #27 did, threw it away, and left a mutation table
  nobody could replay. Booth said so on PR #26. Add a case, run the id, quote
  the command. `tests/test_mutation_corpus.py` keeps the anchors from rotting
  on every ordinary suite run, and proves the runner can still report failure.
  A case must name the test it expects to be caught by; a mutation caught by
  a *different* guard is reported WRONG-GUARD, because the intended guard is
  then still untested.
- A guard whose comment claims more than its code delivers has now appeared
  **five** times: the leak test that flagged a `dropna` subset, the "superseded
  figures" check that banned its own honest disclosure, the "quotes the
  reproduced figures" check that passed a half-revert, the changelog date guard
  that was never reached because an ordering guard fired first, and
  `compare_pandas_versions.py` asserting determinism in its verdict text without
  checking it. **Mutation-test every new guard**, and check WHICH assertion
  caught the mutation — if it is not the one you intended, the intended guard is
  still untested.
  **Sixth, 2026-09-21, and it is not a guard:** `matchupColors`' comment said
  the push separates close pairs "while keeping each team's real hue (so it
  still reads as that team)". Measured, it renders Cincinnati's `#FB4F14` as
  `#C43E10`. So the shape is not confined to guards — any comment stating what
  the code achieves is the same liability, and a comment about COLOUR is
  cheaper to check than most: run the values.
  **A near-seventh the same day, caught before shipping and worth more than
  the six:** a test asserting a stored spread is a plain JSON number cannot
  fail, because `numpy.float64` subclasses `float` and `json.dump` serialises
  both. It was deleted rather than shipped, and `tests/test_line_snapshot.py`
  records why so nobody adds it back. **Before writing a guard, ask what input
  would make it go red.** If you cannot name one, it is decoration in the
  place a reader looks for protection.
- **A stale `.pyc` makes a mutation harness lie.** Several mutations preserve
  file size (`2.4` → `2.5`, `2026` → `2126`), and bytecode invalidation keys on
  size plus a one-second-granularity mtime. Written milliseconds apart, Python
  reuses the previous case's bytecode, and mutations report CAUGHT while showing
  the *previous* case's failure message. Clear `__pycache__` and run with `-B`
  in any mutation script.
- **A silent `return {}` on a missing file hid a broken page for months.** The
  Team Deep-Dive page rendered empty for all 32 teams because the history file
  was in the wrong directory and the loader said nothing. Every missing-input
  branch must say something.
- **Graded prediction files store `1`/`0`, not `true`/`false`.** A `=== true`
  comparison against them is quietly false. Normalise at the boundary and keep
  null as null, so "not graded yet" cannot collapse into "wrong".
- **A screenshot that is not attached is not evidence.** Booth marked the same
  visual claim UNVERIFIABLE three times across one PR because the images existed
  only in the working session. Attach them, or state the claim as a process
  note rather than proof.
- **Changing only a URL fragment does not reload the page.** A share link pasted
  into a tab that already has the dashboard open runs no init code; it needs a
  `hashchange` listener. Test a receive path as a genuine second visit, not as a
  fresh page load.
- **A regex anchored on a bare class name also matches the CSS that defines
  it.** `tests/test_dashboard_charts.py` matched `srs-bar-track(?P<cls>[^"]*)"`,
  which hit the *stylesheet* rule declaring the class and then hopped forward
  into the first real bar — one phantom "bar" whose class list was a wall of CSS
  (containing the word `diverging`, so it passed) and whose `left:` had been
  read off a different element entirely. The count guard beside it asserted
  `len(bars) >= 3` and was satisfied by that phantom for as long as it existed.
  Deleting the Playoff Odds page dropped the count to 2 and only then exposed
  it. Two durable lessons: anchor markup matchers on `class="`, not on the class
  name; and **a count assertion validates the number of matches, not their
  identity** — a matcher can drift onto the wrong thing and still count high.
- **Deleting the only input that reaches a branch silently untests that
  branch.** The zero-line rule has two halves — a left-anchored magnitude bar
  must NOT wear `.diverging`, a signed bar must. Playoff Odds was the only
  left-anchored bar on the dashboard, so removing that page left the first half
  unreachable with every test still green. The fix, and the pattern to reuse:
  state the rule as a plain function, then check it twice — once over whatever
  the page really contains, once over a parametrized table of synthetic inputs
  that keeps both branches alive regardless of what the markup holds this week.
  **When deleting a page, ask what it was the last example of.**
- **A mutation case's `tests` must name exactly ONE pytest path.** Two paths
  with a space between them load fine, reach pytest as a single nonexistent
  filename, and pytest exits non-zero having reported no failures — which the
  runner reads as "the suite went red but the named guard passed" and prints
  WRONG-GUARD. The verdict blames a guard that is perfectly healthy and the
  obvious next move is to go and edit it. `tests/mutation/corpus.py` now refuses
  it at load time with a sentence naming the actual mistake. For a second test
  file, give that individual case its own `tests` key.
- **Adding a way to sort a table can make an existing column start lying.** The
  Power Ratings `#` was the row's index in the current sort. That was harmless
  while net rating was effectively the only sort anyone used, and the comment
  beside it already claimed the number was the team's "real league position" —
  true only by accident. The first click on the new Playoff Odds header printed
  **"#1 Cincinnati" next to a negative net rating, on a page titled Power
  Ratings**. Found by rendering the page and clicking the new control, not by
  reading the diff. The rank is now computed once in Python from the net order
  and travels with the team. Durable form: **a new control does not only add
  behaviour, it reaches states the old code was never asked about** — after
  adding one, exercise the page through it and re-read every neighbouring
  claim, in prose and in cells, that was only ever true in the default state.
- **This dashboard has TWO navigations, and deleting a page from one leaves a
  dead tab in the other.** The desktop sidebar (`.nav-btn`) and the mobile
  bottom-nav (`.bnav-btn`) and its "more" sheet (`.bnav-more-item`).
  `.bnav-item` never existed -- `git log --all -S bnav-item` returns nothing. PR #40 deleted the
  Playoff Odds page and its sidebar button and shipped to main with the mobile
  tab still there, opening a blank screen on a phone. The desktop render looked
  perfect and every test passed. `test_every_nav_on_the_page_agrees_on_which_pages_exist`
  now asserts that every `data-page` target has a matching `<section>`, stated
  as a set relation so the next deletion is covered without anyone remembering
  this. **Deleting a page means deleting every control that reaches it — grep
  `data-page`, do not grep the nav you happen to be looking at.**
- **A guard that reads the source FILE counts commented-out markup as present.**
  Two of the strongest new guards — the ones asserting the build record had
  survived a merge — both SURVIVED their mutations: one because wrapping the
  whole grid in `<!--` left the regex matches intact, the other because the
  title it searched for also appears in an unrelated nav label, so
  `title in page` stayed true with the card renamed away. Strip comments and
  match the ELEMENT you mean, not a substring of the file. Both were caught by
  mutation testing and by nothing else, which is the argument for the harness.
- **A plan in this file is a hypothesis about code, and this one was wrong.**
  The Stage 7.5 entry asserted the Roadmap's Done list duplicated the Changelog.
  Checking took one script and found ~3 of 16 overlapping; the rest existed
  nowhere else. Two earlier inherited claims in this file were also wrong (the
  SOS "defect", the Team Deep-Dive "Done" status). From `0d6c8e1` this sentence
  listed a third, the "no PR-body-edit tool" line -- but nothing in the repo
  records what that correction was, and the line still verifies today, so the
  listing was the unsupported claim, not the line.
  **Before executing a deletion this file plans, verify the premise
  the plan rests on, and record the correction beside the original.**
- **A PR description is a separate artifact from the code, and fixing one does
  not fix the other.** Booth flagged a wrong count in #44's description. The
  response was to correct the code comment and add a CLAUDE.md entry — both
  real improvements, neither of them the thing under audit. The next run said
  it plainly: *"Fixing a code comment does not fix a GitHub PR description;
  those are different artifacts, and only one of them was touched."* A
  description cannot be corrected by a commit, and there is **no MCP tool to
  edit one** — GitKraken exposes `pull_request_create`, not update. So a
  description fix is always a hand edit by Mark: give him the exact replacement
  text rather than a description of the change.
- **Booth reads the description ONCE, at a timestamp it records.** Its header
  says `Description read at: <time>`. Edit the description after that moment
  and the report is stale, not wrong — it will flag a discrepancy that is
  already fixed, and re-reading the same report looks like the fix failed. On
  #44 the read was 22:17:12, the post 22:25, and the edit landed between them.
  **Before treating a repeated finding as unresolved, compare that timestamp to
  when the description last changed.**
- **When one number moves for two different reasons, say which is which.**
  The plain-language allowlist went from nine entries to zero: eight were
  rewritten, and the ninth left because the guard's own matcher was fixed
  (`epa` had been matching inside "s*epa*rately" — it was never on the page).
  The writeup called it eight throughout, so the count silently credited a
  matcher fix as a copy rewrite. Booth caught it on PR #44. Both facts were
  known at the time and one was dropped in the summary, which is the specific
  way this goes wrong: **the miscount is not a slip in arithmetic, it is a
  cause that got left out of the sentence.**
- **THE RECURRING ONE: a real number from a command whose scope is not the
  sentence's scope.** Booth found this shape four times, three of them inside a
  single afternoon (2026-09-10), on three different PRs:

  | Where | Written | True |
  |---|---|---|
  | #51 claim 7 | "every measured element reports 0s" | 8 selectors measured; a 3,582-element sweep found 64 still animating |
  | #51 claim 17 | the three `--shadow-sm` / `--shadow-md` / `--shadow-lg` tokens "still used in ten places" | 9 token references; 10 `box-shadow` declarations |
  | #52 claim 5 | "seven pairs sit between 14.9 and 15.25" | nine — read by eye off a wider band printed for another purpose |
  | #54 claim 4 | the churn-guard test file "… its 31 tests still pass" | 3 — the 31 was a three-file run (3 + 20 + 8) |

  **Not one of these was invented.** Every number was real output from a real
  command. That is exactly why re-reading never catches them: the author
  remembers running the command and getting the figure, so it feels earned.
  What goes unchecked is the *attribution* — whether the command's scope is the
  sentence's scope — and attribution is invisible to the person who did it.
  Note also the direction of drift: the command is almost always **wider** than
  the sentence (three files quoted at one, a wide band quoted at a narrow one,
  eight selectors quoted as "every"), because the wider command was run first,
  for a different reason, and the sentence was written later.

  So the rule is not "be careful with numbers", which describes nothing you can
  do. It is: **write the command beside the number.** A one-file
  `pytest … -q --collect-only → 3` cannot be written next to "31" —
  the mismatch becomes self-evident at the moment of writing, which is the only
  moment it is cheap. Corollary, stated because it is the one that keeps
  failing: **never quote a count from a multi-file pytest run.** Collect each
  file on its own.

  `check_scoped_test_counts` in `src/agents/scout_preflight.py` closes the one variant
  that is mechanically decidable — a count attributed to a named test module is
  checked by collecting that module. `tests/test_scoped_count_guard.py` holds
  #54's failing sentence, so the guard cannot rot silently — re-anchored to
  that test file itself in Stage 8c phase 2, because the module #54 actually
  named was deleted and the checker deliberately passes counts for modules that
  do not exist (a body may describe a file a later phase adds). The other three
  variants have no general check and are governed by the rule above.
- **THE OTHER RECURRING ONE, and it is NOT the same defect: a number that was
  correct when written, falsified by the base moving underneath it.** Nobody
  mis-attributed anything and nobody edited the text. The world moved and the
  sentence stayed still. The entry above is an error at the moment of writing;
  this one is an error that arrives later, in a file nobody has touched.

  It happened five times on 2026-09-10/11 alone:

  | Where | Written | What moved |
  |---|---|---|
  | PR #56 body | `731 passed` | the branch rebased; 751 by audit time |
  | PR #60 commits 1-2 | `Suite: 751 passing` | rebased onto a base with ~23 more tests -> 774 |
  | PR #61 README | `18 cases` | PR #59 merged and added one -> 19 |
  | `.game-grid` comment | "stretching would pad the short ones" | true at a 205px spread, false at 20px |
  | `.shared-banner` comment | "Amber, not blue" | `--accent` had become a blue |

  The fix is not "be careful", which describes nothing you can do, and it is
  not documentation — this file already documented the first variant at length
  while PR #56 reproduced it four times the same afternoon. **The fix is that
  a number in prose must have something that recomputes it.** 2026-09-11 ran
  the experiment cleanly, by accident:

  - README's counts are guarded by `tests/test_readme_accuracy.py` -> the
    stale count failed loudly in CI within minutes of #59 merging.
  - This file's suite line is guarded by `src/agents/session_wrapup.py` -> caught.
  - The dE00 figures in the template's model-colour comment are guarded by a
    verifier plus its own mutation cases (PR #60) -> caught.
  - The `Suite:` trailers in commit messages are guarded by **nothing, and
    cannot be** -> they rotted silently and cost an audit to find.

  So, mechanically: **before writing a number, name the thing that will
  recompute it. If nothing can, do not write the number there.** A commit
  message is the clearest case — it cannot be corrected without rewriting its
  SHA, which invalidates every Booth report referencing it, so a count in one
  is unfixable by construction. Put verification numbers in the PR body, which
  `scout-preflight.yml` re-checks on `synchronize` precisely because a rebase
  can falsify them, and leave them out of commit messages.

  MECHANISED 2026-09-12, in `9c3e320`: `scout_preflight.py` has a
  `no count in a commit message` check (`COMMIT_SUITE_COUNT_RE`), guarded by
  `tests/test_preflight_count_honesty.py`. **But it matches suite-shaped
  counts only** -- `\b\d{2,}\s+(?:passed|passing)\b` -- so a count of anything
  else walks through. PR #68 put "147 individual cases" into a commit message
  that way and Booth caught it after the fact; the real figure was 151. A
  commit message is the one artifact that cannot be corrected without
  invalidating every Booth report against its SHA, so the narrowness is the
  live gap, not the absence of a check. *(Widened 2026-09-22 to any
  verification count, with up to two words between the number and the noun,
  so "147 individual cases" is caught.)*
- **A wrap-up check that greps this file for a literal string is disabled by
  rewording that string, and says the line is MISSING.** `session_wrapup.py`
  matches `Suite:\s*\*\*([0-9,]+)\s+passing\*\*`. Writing
  `Suite: **527 passing, 1 skipped**` — strictly more information — made it
  report "CLAUDE.md has no 'Suite: **N passing**' line to check", which reads
  like a deleted section, not an edited sentence. Any prose this file carries
  *for a tool* is an interface: extra detail goes outside the matched span.
- **The suite count is not a property of the code alone — one test skips while
  HEAD is ahead of `origin`.** A test in `tests/test_session_start.py` skips
  with "HEAD is not on a remote branch, so there is nothing to prove here", so the
  same tree reports `764 passed, 2 skipped` with a local commit sitting
  unpushed and `765 passed, 1 skipped` the moment it is pushed. The wrap-up
  gate then fails `suite count` against a `CLAUDE.md` line that is correct,
  and the obvious repair — editing the number down to match the run — is the
  wrong one: it makes the file false for every session that reads it from a
  clean checkout. **Push first, then run the suite, then quote it.** Both of
  that run's failures had this single cause, and `unpushed work` failing
  alongside `suite count` is the tell.
- **`session_wrapup.py` reports the PASSED count and says nothing about
  failures, so `a real run gives N` can mean a red suite.** Writing the entry
  above produced `764` a second time — not from the skip, but because its own
  first draft put a test path with a trailing colon-and-line-number inside
  backticks, which the path guard in `tests/test_claude_md_freshness.py` reads
  as a filename that does not exist, and a test went red. Same number, wholly
  different cause. **When `suite count` disagrees, run pytest yourself and read
  the whole summary line before touching the figure.** A line number belongs
  outside the backticks; only the bare path goes inside. The sentence you are
  reading was itself rewritten twice for exactly that reason.
- **`scout_preflight.py --base main` compares against LOCAL main, which goes
  stale the moment a PR is merged on GitHub.** Right after merging #41 it
  reported "2 commits on this branch, but the body never mentions 2 of them"
  and named a commit that was already on main — which reads exactly like the
  undisclosed-scope failure it exists to catch. The fix is
  `git fetch origin main:main`, not editing the PR body to explain a commit
  that is not actually in the diff. **Refresh local main before every
  pre-flight.**
- **The full mutation run outlives the 60-second Desktop Commander timeout.**
  The corpus takes several minutes -- 89 cases when this was written at
  `1e75803`, 151 at `3471df5`; `docs/context.md` carries the live count. The
  tool call returns "device did not respond" while the run continues, so:
  redirect to a file, poll for completion, read the file — and check
  `git status` before believing anything, because a killed runner skips the
  `finally` that restores the mutated file.
- **A PR comment is not the PR description, and a red check routed around is
  worse than one ignored.** #69 grew two commits after its body was written.
  A PR description cannot be edited from here, so the head move was documented
  in a *comment* -- and `scout_preflight.py`'s `scope disclosed` check reads
  the DESCRIPTION, as does Booth. The comment changed nothing, the `preflight`
  job went red in CI, and the next audit reported the undisclosed commit as a
  DISCREPANCY and reproduced the CI failure outside CI. Same family as the
  entry below about a code comment not fixing a description. The durable
  shape: **when a branch outgrows its body, the fix is exact replacement text
  for Mark, never a comment** -- and the body is where the risk lives, because
  every push after it is written can falsify it.
- **A PR body is an auditable surface whose size is a liability, not a
  virtue.** Four audits on #69 and the code was never once in question. All
  four findings were in the description: an undisclosed commit, then three
  suite figures where the check allows one, then a clause saying one file was
  touched by both sides of a merge when two were. Each cost a manual edit by
  the one person who can make it. A long, claim-dense description maximises
  exactly the thing that cannot be corrected in place. **Put the detail in the
  commit message and the code comments, which can be corrected or are audited
  differently; keep the description short and its checkable claims few.**
- **A guard whose FIXTURE fails reports as WRONG-GUARD with "Failures: none
  reported".** A mutation changed a function's signature; the fixture that
  extracted that function was anchored on its parameter list, so it failed at
  *setup*. pytest calls that an ERROR, the mutation runner reads failures, and
  the verdict blamed a perfectly healthy guard. Same shape as the tools here
  that read one number out of a multi-number summary and invent a cause for
  the difference. **A guard must fail on its own assertion, never by making
  its fixture unusable** -- anchor fixtures loosely, assert strictly.
- **A matcher anchored on a bare identifier finds whichever occurrence comes
  first, and every assertion after it is then about the wrong text.** Three
  times in one session: `lbx-chevron` found the CSS rule declaring the class
  and ran 50,000 characters to the next `</svg>`, sweeping up the very hex it
  was written to prove absent; `group.querySelectorAll('.pick-btn')` found
  `paintPickCard`'s loop, not the tap handler's;
  `btn.addEventListener('click', ()=>{` found the Week Board's filter handler.
  Each produced a confident, wrong failure message. The existing entry says to
  anchor on `class="` rather than a class name; the general form is stronger:
  **anchor on something that occurs once, and assert the capture is the size
  you expect before reading anything off it.**
- **`scout_preflight.py` read only the PASSED count too, so a RED suite was
  reported as a stale number. FIXED in `9c3e320` (`SUITE_BROKEN_RE`, and the
  subprocess encoding pinned). `session_wrapup.py` was fixed on 2026-09-22
  (`parse_summary`, which reads only the final summary line).** An entry above records this for
  `session_wrapup.py`; on 2026-09-12 it turned up in a second tool, where it is
  worse, because the message preflight prints is the PR #21 stale-figure text —
  "the body claims [876] passing but a real run at HEAD gives 875" — which
  names a cause that is not the cause and sends the reader to edit the PR body
  instead of to the red test. `run_test_suite` matches `(\d+) passed` and never
  looks at the failures. The trigger is worth knowing on its own:
  `test_it_prints_the_context_file_rather_than_pointing_at_it` in
  `tests/test_session_start.py` compares `session_start.py`'s piped stdout
  against `docs/context.md`, and every line it reported missing carried an em
  dash — so the suite is green run directly and red run as a subprocess of
  another Python process, which is exactly how preflight runs it. Two small
  fixes: fail on a non-zero failure count rather than reporting a total, and
  pin the encoding on that subprocess. **The general shape: a tool that reports
  one number out of a multi-number summary will invent a cause for the
  difference, and the invented cause is plausible enough to act on.**
- **I FOUND A DEFECT THAT WAS ALREADY GUARDED, AND NEARLY SHIPPED THE WRONG
  FIX INTO THIS FILE.** Worth more than the finding itself, so it is recorded
  as the correction it is. #60's fourth audit disagrees with itself: the prose
  header says "Confirmed: 13 ... Unverifiable: 2" while its `booth-verdict`
  block lists fourteen CONFIRMED and one UNVERIFIABLE, and the overall prose
  sides with the block. Real, and worth knowing. The first draft of this entry
  then said the counts had "nothing recomputing either" and prescribed "a check
  in the parser: assert the header tallies match the block." **Both halves were
  false.** `cross_check()` in `src/agents/booth_verdict.py` already does exactly that,
  `src/agents/collect_agent_log.py` already prefers the block over the prose and says
  so in its own module docstring, `tests/test_collect_agent_log.py` has
  `test_a_report_disagreeing_with_itself_is_counted`, and the log had already
  recorded this very audit with the two sentences spelled out:
  `"prose says Confirmed: 13, block has 14"` and
  `"prose says Unverifiable: 2, block has 1"`, under a `summary` field named
  `reports_disagreeing_with_themselves`. One `python -c` against
  `data/agent_log.json` would have found all of it, and did — after the entry
  was written.
  **Two lessons.** The narrow one: a self-disagreeing report is detected and
  TALLIED, not failed, so the only open question is whether it should stop an
  audit rather than be counted by one — a much smaller question than "build the
  check." The general one is this file's own rule, turned on its author:
  *an audit finding is a hypothesis, not a defect.* Before writing that
  something is unguarded, grep for the guard. The cost of not doing so is a
  permanent instruction, in the document every session reads cold, to build a
  thing that already exists.
- **NEVER QUOTE A MUTATION COUNT FROM AN `--id` GLOB. A glob looks like a
  scope and is not one.** #72's body said "42 mutations over the two affected
  files, 42 CAUGHT", from `runner.py --id "p*"`. The command was real and the
  42 were genuinely all caught. But the two files this PR touched hold
  **eleven** cases; the glob pulled in 38 from `picks_card`,
  `picks_surgical_update`, `plain_language`, `scout_preflight` and
  `preflight_count_honesty`, none of which the PR went near — and it MISSED
  seven of the eleven that mattered, because their ids happen not to start
  with `p` (`sort-comparator-...`, `rank-...`, `signed-bar-...`). Booth ran
  those seven itself, found them all CAUGHT, and confirmed the safety
  property while rejecting the sentence. It is the wider-command shape again,
  with a new and worse property: **the glob was simultaneously too wide and
  too narrow**, so the number was inflated by unrelated cases and the real
  coverage gap was invisible inside it. Case ids are chosen for readability,
  not as a namespace, so `p*` is not a selector for anything.
  **Quote the full corpus — one command, `python tests/mutation/runner.py`,
  whose scope is exactly "every case" — or name the ids and run them.** The
  full run is a few minutes in the background, which is cheaper than an audit
  cycle. This was the second mis-scoped figure in a PR body on 2026-09-15,
  the first being the entry below, which had already been written down before
  this one shipped: a trap entry is not a control either.
- **THE TWO RECURRING NUMBER TRAPS, COMBINED IN ONE SENTENCE — a numerator
  measured against a set that later grew, quoted against the set's final
  size.** #71's body said "five of the eight new tests failed before the
  template was touched". Booth restored the parent commit's template under
  the PR's test file and got **six of eight**; re-run here in a throwaway
  worktree, same answer. Both numbers were real. When the red run happened
  there were SEVEN guards and five were red; the eighth was written later,
  after the implementation, because a mutation walked through everything else
  in the file — and it would have been red too, which is exactly why Booth's
  six is the honest figure. The denominator moved after the numerator was
  measured, and the sentence took one from each moment.
  This is the intersection of the two traps above, and it is worth its own
  entry because neither one alone describes it. It is not the command being
  wider than the sentence: the command was correct when run. It is not the
  base moving underneath a finished claim either: nothing rebased, and the
  set that changed was the author's own, inside the same session. **A
  test-driven red count is measured at a moment, and adding a guard later
  invalidates it silently, because the later guard is indistinguishable in
  the final diff from one written first.** So: name the count with the
  moment — "seven guards went in first, five red; an eighth followed the
  implementation" — or re-run the red pass against the final set before
  quoting a fraction of it. A fraction whose denominator is "the new tests"
  is a claim about the diff; a fraction whose numerator came from a run is a
  claim about a point in time, and the two are only the same if nothing was
  added in between.
  Note what this cost and did not cost: the code was right, the guards were
  right, and the only wrong thing was a sentence in the one artifact that
  cannot be corrected without a human. Booth caught it on substance after
  every mechanical check had passed, which is the argument for the audit in
  one line.
  **Third variant, same day, and the worst of the three: a BEFORE/AFTER TABLE
  whose two columns were measured under different conditions.** #73's table
  was headed "at a 430x900 viewport" and claimed `.game-card` went 351 to 398.
  It did not. 351 is the card at **375px** and 398 is the card at **430px**,
  on the same unfixed build -- the card is the viewport minus the page
  gutters and never depended on the fix at all. Booth could not reproduce the
  row and gave the mechanism: `.game-grid` is `repeat(auto-fit,
  minmax(340px,1fr))`, one column at either width. A two-column table is the
  highest-risk artifact this repo produces, because the columns are measured
  minutes apart, the header states one condition for both, and a row that
  moved for an unrelated reason looks exactly like a row that moved for the
  reason the table is about. **Measure both columns in the same session and
  in the same call, or record the condition per row.**
  **And a rendered figure that is a sum of text widths is not portable.** #73
  also claimed the unfixed page's `scrollWidth` was 533; two independent Booth
  runs measured 537, and Booth argued that agreeing twice made 533 simply
  wrong. It is subtler than that: both its runs share one environment, and the
  figure decomposes as the sort control's x-position plus its button width plus
  the phantom select's 160 — verified here, `191 + 183 + 160`, where every term
  but the 160 is text measured in a webfont that another machine may not
  resolve. Windows gives 533, that sandbox gives 537, and neither is wrong. So
  for a rendered claim, **quote the decomposition and the invariant, not the
  total**: "the hidden select adds its full 160px past the control" is true
  everywhere, and "`scrollWidth` is 533" is true on one machine on one day.
  The corollary for reading an audit: two runs in one sandbox are two samples
  of one condition, not two independent confirmations.
  One testing fact fell out of #73's third audit and is worth keeping, because
  the obvious method gives a confidently wrong answer: **a `position:fixed;
  left:0; right:0` element only tracks document overflow under MOBILE viewport
  emulation.** Booth first measured `.bottom-nav` at a plain desktop viewport
  and got 430 on both builds while `scrollWidth` read 537 and 430 -- which
  looks like the claim being false. With Playwright's `is_mobile`/`has_touch`
  on, it read 537 and 430, tracking exactly. Any future claim about a phone's
  shrink-to-fit needs mobile emulation, or it cannot be reproduced at all. Three mis-scoped
  figures in one day, each caught by Booth and none by any mechanical check,
  is the argument for `scout_preflight.py` learning to check them: it already
  verifies a claimed suite count against a real run, and a claimed figure with
  no command beside it is the same shape.
- **A breakage that is predicted in writing still happens, because the remedy
  was a human step and nothing enforced it.** `docs/context.md` said, in bold,
  that merging #69 would put 31 files under a README claiming 30 and turn
  `tests/test_readme_accuracy.py` red on `main` — and asked for the bump to
  ride with the merge. #69 was merged from the GitHub UI on 2026-09-15 without
  it, and `main` was red for exactly one commit until `976d0a3`. Nobody
  misunderstood anything: the prediction was correct, read, and unactionable at
  the moment it mattered, because a merge button does not carry a file edit
  with it. The durable shape: **if the remedy for a known breakage is "remember
  to do two things at once", it will eventually be done as one.** Either put
  the second thing on the branch before it merges, where the merge carries it,
  or accept the red and fix forward — but do not write the pairing into a
  document and count it as a control. Note what DID work: the guard fired
  immediately and named both numbers, so the window was one commit wide rather
  than a month. A cheap number in prose plus a test that recomputes it is the
  pattern behaving exactly as designed.
- **A GUARD THAT NAMES ITS SUBJECT IS SCOPED TO THE INSTANCE THAT PROMPTED IT,
  AND THE SECOND INSTANCE WALKS PAST IT.** This is the sharpened form of the
  "wired into one of several paths" entry above, and it is worth its own
  because the guard here was written FOR this exact failure mode and still
  missed it. `tests/test_generated_data_reaches_the_page.py` exists because a
  GITHUB_TOKEN push cannot trigger another workflow and the collector's output
  therefore never reached the page. It encoded that as `DASHBOARD_INPUTS =
  ('data/agent_log.json',)` and `COLLECTOR = collect-agent-log.yml` — the one
  file and the one workflow in front of it at the time. "Weekly update" writes
  `predictions/**`, `results/**` and `data/**` with the same token, was never
  in `deploy-pages.yml`'s `workflow_run` list, and was invisible to every
  assertion in that file. On 2026-09-15 it graded the first real week at 11:05
  UTC and the published page served 04:30 UTC data — no Week 2 in either week
  control — until a build was dispatched by hand. Nothing failed. Fixed in #74
  by enumerating the writers and reading the watched path set out of the
  builder, so the builder stays the single source of truth.
  The file's own docstring had written the trap down as a virtue: *"the check
  is on the chain, not on either end of it."* There were two chains. **When a
  guard names a file or a workflow, ask what class that name is an instance
  of, and enumerate the class instead** — the constant is the tell, not the
  logic around it.
- **AN ASSERTION OVER A LIST SOME SCAN PRODUCES NEEDS A TEST THAT THE SCAN
  FOUND ANYTHING.** Discovered while fixing the entry above, which is the point
  of recording it. The widened guard computes "every workflow that writes a
  dashboard input" and asserts each is bridged. The first draft's path parser
  stripped quotes before the leading `-` of a YAML list item, so `- 'src/**'`
  yielded the root `'src`, nothing ever intersected, and the scan returned an
  empty list — over which the bridging assertion passed, cleanly, proving
  nothing. It would have shipped green and re-created the original defect one
  level up. The vacuity test named the two workflows known to write and failed
  instead, which is the only reason the parser bug was found at all.
  **Any assertion of the form "every X must Y" needs a companion asserting
  that the search for X is not returning nothing**, and the companion has to
  name specifics the scan must find. `rebuild-bridge-writer-scan-goes-blind`
  in the corpus is that case. Note the asymmetry that makes this expensive:
  a broken scan fails OPEN and looks like a pass, while a broken assertion
  fails closed and gets fixed the same minute.
- **A SWEEP OVER LIVE DATA ANSWERS FOR TODAY'S DATA, AND "NOTHING FOUND"
  LOOKS IDENTICAL TO "NEVER HAPPENS."** Tracing the six untraced
  `ACCEPTED_CLOSE` pairs meant asking which colours are ever on screen at
  once. The first sweep was clean, complete, and said `--series-d` appears on
  no page at all — so three pairs could "never meet". Every part of that was
  false. The Season Accuracy trend chart short-circuits below two graded
  weeks, and in September there is one; its My Picks series is computed from
  `localStorage`, which a fresh browser profile does not have. The sweep was
  measuring a page that structurally could not draw the thing being looked
  for. This is the same family as the webfont entry above — an environment
  missing a precondition finds nothing and the absence reads as a checked
  result — but the precondition here is **the date**, which no amount of
  re-running fixes and which nothing in the output mentions. The tell is
  available before the sweep: ask what has to be TRUE for the thing you are
  looking for to render, and check each of those separately. What the
  verifier does now is seed the state and refuse to report unless the chart
  actually drew. Note the second-order fact that fell out of it and is worth
  more than the trace: the chart's legend renders all four series swatches
  regardless of whether the picks line has data, so the pair goes from
  unreachable to on-screen-for-every-visitor the moment a second week grades.
  A "cannot happen" that expires on a known date is not a cannot-happen.
- **SCOPE A CO-OCCURRENCE QUESTION TO THE SCREEN, NOT TO THE COMPONENT YOU
  WERE THINKING ABOUT.** The same sweep walked `section.page.active` — the
  page body — because the question was phrased as "which page paints this".
  The sidebar, the header and the bottom nav are on screen on every page, and
  the active nav button and the brand mark both wear `--accent`. Restricted
  to the body, the sweep reported that `--accent` and `--series-d` never meet;
  widened to `body`, they meet on Season Accuracy. Both runs were correct
  about what they measured. This is the wider-command trap inverted — a
  command NARROWER than the sentence — and it is the more dangerous direction,
  because a narrow scan produces the reassuring answer. Ask what the reader
  can see, then pick the selector.
- **A selector that matches nothing is the cheapest way to get a confident
  wrong answer, and it happened twice in one afternoon.** The first sweep
  queried `section.page-section.active`; the class is `.page`. An intermediate
  run mutated the page's data after a reload and never re-rendered, so the
  page scanned empty. Both returned tidy "NO PAGE" verdicts for pairs that
  genuinely co-occur. Neither was caught by reading the code; both were caught
  by a vacuity guard written before the run — one that printed the section
  classes it did find, one that asserted the chart had drawn. **Write the
  vacuity guard before the first run, not after the first surprise**, because
  the run without one does not look like a failure.
- **Desktop Commander refuses to overwrite a file when no `mode` is given,
  and a command chained after it runs on the OLD file.** `write_file` on an
  existing path without `mode: 'rewrite'` returns "Write rejected" and
  changes nothing. Twice on 2026-09-30 the next call went ahead regardless:
  a commit took a stale `.commit-msg.txt` (the branch was re-pushed), and a
  conflict resolver ran its previous version and resolved nothing. **Pass
  `mode` on every write to a path that may exist, and read the write's
  result before the call that uses the file.** The same day's other
  surprise: this checkout is CRLF, so a regex over conflict markers written
  for `\n` matches nothing; match `\r?\n`.
- **A document that names a file the pipeline deletes turns `main` red the
  moment the pipeline runs.** `docs/context.md` named the week 4 preview
  while asking for it to be checked; the lock deleted it as designed
  (#237), and the path guard in `tests/test_workflow_docs.py` failed on
  `main` with no commit by anyone. Found only because 3(b)'s suite ran
  after the lock. **Describe a file the pipeline will delete in words, not
  as a backticked path**, and run the suite on `main` after any scheduled
  run that writes or deletes tracked files before building on it.
