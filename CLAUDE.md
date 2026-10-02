# NFL-Model-2 — working context

Read this first, every session, and again after any context compaction. It exists
because a compaction on 2026-09-04 destroyed a 25-item staged plan that had been
written only into the chat. The transcript on disk begins at the compaction
summary; the original messages were not recoverable. Anything that matters
belongs in this file, not in the conversation.

## What this is

A live NFL prediction dashboard, and equally a **portfolio piece** meant to show
employers real AI/ML engineering rigour. Both purposes are load-bearing: work
that is overkill for predicting football can still be right if it demonstrates
the engineering. Public repo, so anything committed is read by strangers.

## Non-negotiable methodology

- Tune on **validation** seasons [2022, 2023]; confirm on held-out [2024, 2025].
- Close calls go to a **paired bootstrap**, 5,000 resamples. A result counts only
  when the 95% interval **excludes zero**. Otherwise it is INCONCLUSIVE, and the
  page says so.
- Decision labels: ACCEPT / REJECT / INCONCLUSIVE / DEFERRED / CONFIRMED FINDING.
  Every Model Lab row carries one.
- **Accuracy cannot carry a result at this sample size.** Confirmed finding: the
  same commit and dataset disagree by one to two games out of ~1087 between a
  Linux runner and Windows, while log loss, Brier and AUC agree to four decimals.
  Judge on proper scoring rules; treat any accuracy-only claim as suspect.
- No subgroup hunting. The 12-partition narrow-edge search already demonstrated
  what that produces on noise. New slicing needs its own pre-declared experiment.
- `VERIFICATION.md`: no claim about tests, repo state or reproducibility without
  re-executed evidence. Scout does the work; Booth verifies it independently.
- Published numbers must be tied to their data file by a test. Prose drifts;
  `tests/test_published_bootstrap_numbers.py`, `tests/test_version_history.py`
  and `tests/test_pandas_version_experiment.py` are the pattern — every figure
  printed on the page, or argued from in a comment, must exist in the artifact
  it came from.
- **Mutation-test every new guard.** Write the failure it is meant to catch and
  confirm it catches it. See `docs/traps.md` — this has bitten repeatedly, and
  the mutation harness itself has lied twice.
- **Render it and look at it.** Three separate bugs on 2026-09-06 were invisible
  in the code and obvious in a screenshot. A UI change is not verified until
  somebody has looked at it.

## Current state (update this when it changes)

Model v2.5 (`MODEL_VERSION` in `src/pipeline/config.py`). `TRAIN_SEASONS` 2020-2025, `BACKTEST_SEASONS` 2022-2025,
`QB_SHRINK_K = 8`, `RIDGE_ALPHA = 15.0`, `RECENCY_HALF_LIFE = 16`.
The drift check's baseline is the committed `data/calibration.json` (Stage 35;
it was a literal, `BACKTEST_ACCURACY`), and moves only on a deliberate re-run.

Suite: **5032 passing** (none skipped) — `python -B -m pytest -q -p no:cacheprovider` on `main` at
`2448ef4` (after #257), with HEAD level with origin, which is the order that makes the
figure reproducible: one test skips while HEAD is not on a remote branch, so
the same tree reports a different pair of numbers with work unpushed. Until
2026-09-24 `main` also carried a standing skip that was NOT that one: the
Booth fixture baseline check, skipping because no fixture had ever run. A
recorded baseline removed it, so `main` now reports no skips at all. Run it
before quoting
it — this line read 174 for about a day after it stopped being true, and a stale
figure here is the first thing a fresh session anchors on.

Keep the shape `Suite: **N passing**` exactly. `src/agents/session_wrapup.py` greps for
that literal, and rewording it to `**N passing, 1 skipped**` did not make the
check complain about the wording — it reported the line as *missing*, which
reads like a deleted section rather than an edited sentence.

**What runs unattended, and who owns what (settled 2026-09-24).** The
GitHub **Weekly update** workflow owns predictions, grading and the data
commit: Tuesday 11:00 and Thursday 11:00 UTC. Its commit triggers the Pages
rebuild. A run that holds the week (usually Tuesday) saves a labelled
preview to `predictions/preview/` (#204, Mark's "an update both on Tuesday
and Thursday"); only the locked picks are ever graded. Mark's Claude routine, **"Weekly QB override research"**
(`trig_01CG1y9jfmcNQXnu8Hc9SL5K`, Mon and Wed 22:00 UTC), only researches
starting-QB news and opens a PR with a sourced
`data/qb_overrides/<season>_week<N>.json`. It never runs the weekly
scripts, and it must never be given them back: two writers of saved picks
is two ways to break a lock. The routine was created through the HTTP API,
so **an agent cannot edit it**. `update_trigger` refuses; Mark edits it at
claude.ai/code/routines. README's "Automating this with Claude Code
Routines" section describes the same split.

**Since Stage 4, nothing unattended fails silently.** The **Nightly canary**
(06:00 UTC) runs the weekly data path and writes nothing. The Weekly update
runs the drift check and writes a run summary. A failed canary night, a
failed weekly run, a drift flag, a failed Booth audit and a failed nightly
mutation slice each open or comment on a GitHub issue (`src/pipeline/alerts.py`);
`tests/test_alerts.py` fails any scheduled workflow that does not. The Pages build refuses a page
whose data is missing (`src/pipeline/check_build.py`). Stage 4's section in
`docs/stage-history.md` keeps the decisions.

One habit from Stage 8 is worth keeping whatever you work on: every numeric
claim about colour or geometry was re-derived before being believed — contrast
by recomputing WCAG luminance from the hex values, colour-blind separation by
running the Machado 2009 matrices and CIEDE2000, layout by rendering in
headless Chromium and reading `getBoundingClientRect`. Five claims were false:
three of Fable's, and two of mine. Reading your own CSS back is not verification.

### Start here

**Current state now lives in `docs/context.md`. Read that first — it is
rewritten every session and this section is not.** `docs/index.md` maps where
everything is; `memory/` records what each session decided and why. This file
keeps what stays true for months: methodology, the findings that constrain
the work, the environment and the PR loop. The traps are in `docs/traps.md`;
every stage, finished or planned, is in `docs/stage-history.md`, and the
open ones are indexed under "Open stages" below.

**Which branches are open, and what each waits on, is in
`docs/context.md` — that file is rewritten every session and this one is not.**
Do not maintain a second list here; that duplication is what this split exists
to end. This paragraph carried a count of open branches until 2026-09-10, when
it was still claiming "no open branches at all" with one pushed and unmerged —
the duplication it warns against, in the sentence warning against it. Go read
`docs/context.md`.

Two habits that paid for themselves and should carry forward: build
the page and *click the thing you just added* before opening the PR (that is how
the `#`-column defect was found — it was invisible in the diff), and when
deleting a page, ask what it was the last example of before assuming the tests
still cover what they did yesterday.

**Stage numbers are frozen.** They were renumbered twice in two days and it
confused both this file and the Progress tab. A finished stage keeps its number
and is recorded as finished; nothing is renumbered again.

### Findings that still constrain the work

Conclusions, not history. Which PR produced what belongs in the Stage 7
write-ups; what matters here is what is now settled and must not be re-opened
casually.

- **Model B vs the market is INCONCLUSIVE** on all four metrics, stated with
  intervals. Two real findings did survive: Model B genuinely beats Model A on
  proper scoring rules, and the market genuinely beats Model A. The dashboard
  says all three.
- **Stage 5 accepted nothing (PR #84, 2026-09-22), and the rating engine is
  not the bottleneck.** Ten questions were pre-registered with a budget of
  ten confirmatory slots at 99.5%. Success rate, garbage-time weighting,
  pass/rush splits, early downs, rest, a Kalman filter and a learned
  A-plus-market blend all failed the validation screen or came back
  INCONCLUSIVE. Do not re-run any of them without a new registration and a
  stated reason why the answer would differ. **The one signal is about the
  pipeline, not the model.** The published backtest takes each game's QB
  from that game's own box score, which scores the same as the announced
  starter. The live pipeline uses LAST game's QB. On the roughly one game in
  four where those differ, live Model A's log loss is far worse, but
  switching was INCONCLUSIVE at 99.5% (H1). So the page describes a model
  with better QB information than the one making the picks. **Mark switched
  it on methodology grounds on 2026-09-22 (v2.5), as weekly refit was.** The
  order is a sourced override file, then the schedule's listed starter,
  then last game's QB with a note. The schedule is not enough on its own:
  on the day week 3 locked it still listed Dart and Daniels, both ruled out.
  The 2026 forward test scores this change.
- **There is no ATS edge.** 51.61%, CI [48.58%, 54.63%] — contains 50% and does
  not reach the 52.38% break-even. The betting question was asked properly and
  answered negatively. Do not re-open it without new data.
- **`nfl_data_py` is a verified fallback**, executed rather than assumed: it
  imports, all three loaders work, every required column is present, and it
  agrees with nflreadpy exactly on 2025 week 10. So the pandas 1.x pin buys a
  working revert path rather than a theoretical one.
- **The pandas 2.x unlock is not free.** Pre-declared hypothesis — log loss,
  Brier and AUC agree to four decimals across the major version — REFUTED. AUC
  moves up to 0.00125, 25x this project's own noise threshold, with both
  environments proven deterministic and scoring the same 1087 games. "Market
  alone", the one model with no EPA aggregation, is bit-identical; everything
  built on EPA features moves, which localises it to float aggregation over
  ~48k plays a season. Keep the pin; revisit only when something actually needs
  pandas 2.x, and regenerate every published figure as part of that work rather
  than discovering the shift afterwards.
- **THERE ARE TWO RULERS IN THIS REPOSITORY AND THEY ARE NOT INTERCHANGEABLE.**
  `tests/test_dashboard_charts.py` measures **OKLab distance x100**, with
  `CVD_TARGET = 8.0` and `NORMAL_FLOOR = 15.0`. `src/research/verify_model_colours.py`
  and `src/research/verify_matchup_cvd.py` measure **CIEDE2000**. The 8 and the 15 are
  OKLab numbers; quoting a CIEDE2000 figure against them compares two different
  objects, which is the failure this file's own `verify_model_colours` docstring
  was written to prevent — and the first version of this entry did exactly
  that, on 2026-09-16, and had to be rewritten. The two rulers genuinely
  disagree about ranking, not just scale: `--good` vs `--series-c` in light is
  4.3 OKLab and 12.7 CIEDE2000. **Say which metric, every time.**
- **The two closest token pairs are DECIDED, and the decision is recorded in
  `ACCEPTED_CLOSE` rather than here.** `--accent`/`--series-d` in light is
  1.26 under CVD against 15.08 normal; `--accent-strong`/`--series-a` in dark
  is 2.85 under CVD against 2.87 normal. Each is the closest pair in its own
  theme of 28, and both are closer than `--good`/`--warn`, which was already
  accepted. Mark accepted both on 2026-09-21 after seeing them rendered side
  by side in both themes under normal, protan and deutan vision.
  **What matters for future work is that they are opposite shapes and were
  filed together as one item, which hid it.** The first clears the normal
  floor and collapses only under deuteranopia. The second is 2.87 under
  NORMAL vision — not a colour-vision finding at all, a pair nobody can tell
  apart — and is tolerable only because the two tokens never reach one page.
  Two numbers in one queue entry are not one finding.
  **Superseded 2026-09-22 (Stage 9): `--accent-strong` is RETIRED.** Its one
  consumer was the Net Rating bar, which now wears neutral `--text-3`. So the
  second pair no longer exists, along with every other `ACCEPTED_CLOSE` entry
  naming that token, four in all. The first pair stands as accepted.
- **Each acceptance is pinned by the thing it actually rests on, not by the
  colour figures.** `--accent-strong`/`--series-a` rested on a page-disjointness
  that held only while neither token moved, and two consumer guards pinned it
  until the token was retired in Stage 9. The consumer-premise rules stay in
  `tests/test_dashboard_charts.py`, checked over synthetic templates, for the
  next verdict that rests on WHERE a token is used.
  `--accent`/`--series-d` rests on the series' shape and dash, so
  `test_every_series_carries_a_distinct_shape_and_picks_is_the_only_dashed_one`
  holds those. That last guard was written because grepping for an existing
  one found none *after* a draft entry had already cited it by name — the
  fifth time here that "surely something checks this" was wrong.
- **The Week Board's team-colour split bar is DECIDED AND KEPT.** Mark's
  call, 2026-09-21, after the alternatives were rendered side by side on real
  games in both themes and under protan and deutan simulation: a neutral
  two-step bar, an accent fill, no bar, and a hybrid keeping team colour
  except on colliding pairs. All four declined. The bars are wanted on the
  board as part of how the dashboard looks, and the measured cost is accepted
  knowingly — 60 of 496 distinct team pairs under CIEDE2000 15 (9 under 5,
  worst ARI/PHI 0.18), 103 of 992 as ordered matchups, and on the real week 2
  slate 3 of 16 games pushed with 1 still under the floor afterwards.
  **So `teamColor()`, `TEAM_COLOR`, `CONTRAST_THRESHOLD` and the `#8A93A8`
  fallback all stay, and that literal stays live.** Everything above about it
  being reachable only for an abbreviation outside the 32 remains true; what
  has changed is that it is no longer queued for removal. Do not re-open this
  as a colour defect. The one thing worth knowing if it is ever revisited:
  the push does not preserve team colour — it renders Cincinnati's `#FB4F14`
  as `#C43E10` — and `src/pipeline/dashboard_template.html`'s comment said otherwise
  until this decision corrected it.
- **`--good` vs `--warn` collapse under CVD (4.5 dark, 4.3 light) and that is
  NOT a defect.** Checked rather than assumed: the graded tag renders the word
  "Correct" or "Missed", and Team Deep-Dive's `mark()` renders the word
  "correct". Colour is redundant to text on both, which is exactly the
  secondary encoding the floor exists to require. A red/green pass-fail pair is
  the most obvious-looking colour-blindness defect there is, and this one was
  already handled — an audit finding is a hypothesis, not a defect.
- **`src/research/verify_model_colours.py` checks a hand-written table of two pairs.**
  That is why the `--accent`/`--series-d` and `--accent-strong`/`--series-a`
  collisions went unrecorded: the pairs in it are the ones that were in front
  of whoever wrote it. Same shape as the bridging guard #74 widened. Enumerate
  the class — every meaning-carrying token against every other, both themes,
  normal and CVD. Note what the existing chart guards do and do not cover:
  they gate series NEIGHBOURS (a-b, b-c, c-d) and `--series-d` against
  `--good`, so a-to-d and anything involving `--accent-strong` was never in
  scope.
- **Re-stepping `--accent` to clear 15 is impossible in light mode.** Searched
  the whole blue range 195-265 degrees per theme, requiring CIEDE2000 >= 15
  against all four series plus 4.5:1 on surface and 3:1 on background: dark has
  3,585 candidates, light has **zero**. (CIEDE2000, so re-run it in OKLab
  before acting on it — see the two-rulers entry above.) The plan recorded in
  the template comment, "re-stepping this token pair so it clears 15", cannot
  be executed as written, and that comment also defers the work to a "Stage 11"
  that has never existed.
- **An audit finding is a hypothesis, not a defect.** Four of Stage 2's seven
  queued items were not the item as written. SOS was computing correctly and
  the season had not started — acting on the audit would have deleted a working
  feature for being audited in September. The Team Deep-Dive page had never
  worked at all: a missing file returned `{}` in silence while the roadmap
  listed it Done. Read the code and render the page before believing a queued
  finding.
  **Sharpened 2026-09-20, after two more in one session: the dangerous queued
  item states a MEASUREMENT and a MECHANISM, and only the measurement ever
  gets checked.** `--accent`/`--series-d` really is 1.3 apart under CVD, and
  the story attached — that the pick tick collides with the My Picks series —
  was false, because those two never share a page. `.week-select`'s chevron
  really is a dark-theme grey baked into a data-URI, and the story — that it
  is therefore wrong in light mode — was false, because every element wearing
  that class is clipped to 1x1 in the rendered page. Both numbers survived
  scrutiny; both mechanisms died on first contact with the page, and the
  second had two guards and a mutation case defending its reasoning. The tell
  is grammatical: a queued item whose sentence turns on "so", "which means" or
  "and therefore" has a mechanism in it, and the mechanism is the half nobody
  measured. Check that clause before doing the work it implies.

## Open stages

The full text of every stage, finished or planned, is in
`docs/stage-history.md`. Numbers are frozen. What is next this week is in
`docs/context.md`.

- **Stage 20 - Testing with real people**: needs five real testers.
- **Stage 21 - Once the season has data**: not before week 5.
- **Stage 22 - Beyond 95**: comes out of Stage 20.
- **Stage 28 - After the forward test**: after the regular season.
- **Stages 30 to 34 - the 2026-09-29 re-audit (78/100)**: 30 regressions and
  residuals, 31 maintainability, 32 code quality, 33 architecture and model
  engineering, 34 front door. Order and rules at the top of that section.
- **Stage 35 - the 2026-09-30 third audit (83/100)**: its new fixes; the rest
  of its plan is the Stage 32 to 34 queue. Status and decisions in its section.

## Ending a session

Run this every time, before the session closes:

```
python -m src.agents.session_wrapup
```

A session ends when usage runs out or attention moves, not when the work
reaches a tidy boundary. Whatever is true at that moment is what the next
session inherits -- and it inherits it through this file, cold, with no memory
of the conversation that produced it. Every wrong fact here gets believed.

That is not hypothetical. This file said "Suite: 174 passing" for about a day
after it stopped being true (written `69c3b18` 2026-09-06 16:34, corrected
`b732ee0` 2026-09-07 13:52); the real number was 382. It is the first figure a
fresh session anchors on.

**What the script checks**, because these cannot be checked continuously --
six checks, in the order it prints them: which branch you are leaving behind
(informational, it cannot fail); a clean working tree; nothing committed but
unpushed; the suite count stated above against a real run; `docs/context.md`
stamped `Last updated:` today or tomorrow (tomorrow is a timezone, yesterday
is a file nobody rewrote); and a `memory/` file named for today. It exits
non-zero if any of the five that can fail do.

**What `tests/test_claude_md_freshness.py` checks**, free, on every commit:
that every repository path and every test name this file, `docs/traps.md`
and `docs/stage-history.md` mention still exists; that the stage headings
are unique and in order; that no stage section is written back into this
file; and that this file stays under 450 lines. A moved file
leaves a silently wrong pointer; a guard named here and absent from the suite
reads as protection that is present. Note it deliberately skips the stage
sections -- those name work that does not exist yet, and checking a plan the
same way you check a description is wrong.

**What neither can check, and matters most.** The script prints these as
prompts -- the wording below is `BY_HAND` in `src/agents/session_wrapup.py`:

- Does `docs/context.md` name the single next action, not a list of five?
- Is every PR opened this session either merged, or in `docs/context.md`
  with its number and what it is waiting on?
- Did anything surprise you today? A trap entry is cheap now and expensive
  to reconstruct later. Prefer the durable shape over the story.
- Did any decision get made that a future session would otherwise
  re-litigate? Record the decision AND the reasoning, or it gets re-opened.
- Are the stage sections still in the order work will actually happen?
- Is the Progress tab consistent with CLAUDE.md?

**Then re-read this file as if you had never seen it.** Not skimmed -- read.
Ask of each paragraph whether it changes a decision. If it only records what
happened, it belongs in `docs/stage-history.md` or `memory/` instead. This document is read
under compaction pressure, so its length is a cost paid on every session.

## Environment and workflow

- The real clone lives on Mark's Windows PC (the local Windows machine; its
  name and the clone's path are in the gitignored `CLAUDE.local.md` at the
  clone's root, with the session archive's location). Desktop Commander and
  GitKraken MCP plugins are available there; run tests and heavy backtests on
  that machine. **Booth's audit runner is NOT the cloud sandbox, and it does
  reach nflverse**: on #100, #102 and #106 it loaded live play-by-play, and
  on #106 it re-ran the whole reproducibility audit. On #107 it still wrote
  "no nflverse network access, per CLAUDE.md", quoting the old wording of
  this line instead of testing it. Test network access before claiming it
  is missing, in either place.
- **Commits on the local Windows machine use the noreply address** (repo-local `user.email`
  = `317783519+lifeisgreat07@users.noreply.github.com`, set 2026-09-29,
  Stage 29). History before that date carries the personal address and is
  deliberately not rewritten.
- **If Desktop Commander's tools vanish mid-session** while
  `get_device_info` lists `desktop-commander` as announced, `RefreshMcpTools`
  brings them back (2026-09-24). GitKraken stayed connected throughout.
- The cloud sandbox clone is scratch. It cannot push — the repo is not in the
  session's authorised set. Commits and pushes happen on the local Windows machine.
- **Playwright lives in the cloud sandbox, not on the local Windows machine.** For screenshots:
  regenerate `index.html` on the local Windows machine, stage it into the sandbox, and drive
  Chromium there. This is the only practical way to actually look at the page.
- The full backtest takes ~42 seconds. It is not the expensive step people
  assume; run it when a question needs it.
- Production-code changes go through a PR the user reviews. Pure
  dashboard/documentation changes may go straight to main.
- **One item, one PR.** Booth flagged a PR bundling three undisclosed features:
  a reviewer approving on the description alone approves more than they think.
  If a branch grows past its title, either split it or rewrite the description.
- **`.github/` is writable from the local Windows machine.** Editing a workflow and pushing it to
  a feature branch both work, tested rather than assumed. Not verified: pushing
  `.github/` straight to `main`. The restriction that IS real is the Claude Code
  action's own, listed in `docs/traps.md`.
  General lesson, and the second stale belief this file carried: an inherited
  "you can't do X" with no recorded test behind it is a hypothesis. Spend the
  thirty seconds testing it before building a manual process around it.
- No `gh` CLI on the local Windows machine, and no PR-body-edit tool in the MCP set: GitKraken
  exposes `pull_request_create`, not update. (`gh` does exist inside the
  Actions runners -- Booth's workflow calls `gh pr view` and `gh pr comment`
  -- but nothing in the repo edits a PR body with it.) A PR description can
  be corrected only by the user in the web UI, so get the description right
  when opening it.
- **The file bridge will not write `.github/` or `.git/`.** `device_commit_files`
  rejects both as protected paths. For a workflow change, commit a `git diff`
  of it to the repo root as a scratch `.patch`, `git apply` it on the local Windows machine,
  delete the patch, and compare `git hash-object` on both sides. Commit
  messages go through the gitignored `.commit-msg.txt`, not `.git/`.
- **The file bridge and the mutation corpus have traps of their own**: a
  binary corrupted in transit, a write that reports success and keeps the
  old content, a full corpus run of over an hour that must not share the
  checkout. Read "Environment traps" in `docs/traps.md` before moving a
  file or starting a run.
- `cmd` mangles multi-line `python -c` strings, and **PowerShell has no
  heredocs** — `git commit -F <file>` with a written message file, and script
  files instead of inline `-c`, are the reliable forms.
- **To actually LOOK at the built dashboard, serve it over localhost.** Neither
  browser available here will open a `file://` URL, and GitHub Pages serves
  `main`, so a branch's page appeared unviewable — which cost PR #46 and PR #47
  an honest "nobody has looked at this" disclosure each. The fix is one line,
  and both the shell and the browser pane run on the same machine:

      Start-Process -WindowStyle Hidden python -ArgumentList "-m","http.server","8765"

  then open localhost:8765/index.html in the browser pane (not backticked: the
  freshness guard reads a backticked path ending in .html as a repo file and is
  right to). Regenerate, reload, look. The
  first thing it caught was a new empty state rendering as two paragraphs of
  centred prose. Stop it with `Get-Process python | Stop-Process` when done.
  Note the screenshot tool here does not write image files, so a visual check
  is still a **process note**, never attached evidence — Booth is right to mark
  an unattached screenshot UNVERIFIABLE.

- **The PR loop, as run on 2026-09-26 (#108, #109).** Mark allows merging only when
  he says so in the session's opening prompt, and only on Booth's SAFE TO MERGE with
  no discrepancies. The mechanics, all on the local Windows machine:
  1. Branch from fresh `main` (`git pull --ff-only`, `git checkout -b <branch>`).
  2. Commit (message from a file; read `git log -1` after), push, then run the full
     suite and quote it; run each new mutation case with `--id` and check
     `git status` is clean afterwards.
  3. Write the PR body to a file and run `python -B -m src.agents.scout_preflight <body>
     --base main` after `git fetch origin main:main`. The scope check wants each
     commit's short SHA or subject named in the body.
  4. Open the PR with GitKraken's `pull_request_create`.
  5. Read Booth without `gh`: the repo is public, so
     `https://api.github.com/repos/lifeisgreat07/NFL-Model-2/issues/<N>/comments`
     and `.../actions/runs?head_sha=<sha>` need no token (Python `urllib` on
     the local Windows machine; the cloud sandbox's proxy refuses this repo). An audit takes about
     5 to 10 minutes. Wait for the "Booth PR audit" run to finish, not just the
     comment, and read every claim, not only the verdict.
  6. Merge locally so the history matches earlier merges: `git checkout main`,
     `git pull --ff-only`, `git merge --no-ff <branch> -m "Merge pull request #<N>
     from lifeisgreat07/<branch>" -m "<PR title>"`, `git push origin main`, then
     `git push origin --delete <branch>` and `git branch -d <branch>`. GitHub marks
     the PR merged within a minute. **Since 2026-09-26 this runs as one script
     that stops at the first failed step** (see the chained-merge trap in `docs/traps.md`):
     the message comes from a file, and the branch is deleted only after the
     GitHub API reports the PR merged. A push can be refused because the audit-log
     collector committed in between; `git pull --rebase origin main` and push again.
  7. Documentation-only changes (CLAUDE.md, `docs/`, `memory/`) go straight to
     `main`, no PR.
  An UNVERIFIABLE claim that is expected (a draft never committed, a machine Booth
  cannot reach) does not block a merge; a DISCREPANCY always does, and is fixed with
  a new commit, never an amend.
