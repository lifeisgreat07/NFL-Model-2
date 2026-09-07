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
  confirm it catches it. See the traps section — this has bitten repeatedly, and
  the mutation harness itself has lied twice.
- **Render it and look at it.** Three separate bugs on 2026-09-06 were invisible
  in the code and obvious in a screenshot. A UI change is not verified until
  somebody has looked at it.

## Current state (update this when it changes)

Model v2.4. `TRAIN_SEASONS` 2020-2025, `BACKTEST_SEASONS` 2022-2025,
`QB_SHRINK_K = 8`, `RIDGE_ALPHA = 15.0`, `RECENCY_HALF_LIFE = 16`.
Canonical `BACKTEST_ACCURACY` moves only on a deliberate re-run.

Suite: **174 passing** on `main`.

**Stage 2 is complete** — PRs #21, #22, #23 and #24, all merged. Next up is
Stage 3.

**Stage numbers are frozen from here.** They were renumbered twice in two days,
"Stage 8" meant three different things in three days, and it caused real
confusion in both this file and the Progress tab. A finished stage is now
recorded as finished and its number retired; nothing is renumbered again. If you
find a reference to "Stage 4 - evaluation honesty" or "Stage 5 - deploy Booth",
it predates 2026-09-06.

### Finished, and why it matters

Evaluation honesty is complete. The reliability diagram (PR #13) put Wilson
intervals and the Murphy decomposition on Model Lab. The paired bootstrap
(PR #15) then killed its own headline: Model B vs the market is INCONCLUSIVE
on all four metrics, and the panel says so. It confirmed two real findings
instead - Model B genuinely beats Model A on proper scoring rules, and the
market genuinely beats Model A - both stated with intervals for the first
time. ATS evaluation (PR #16) asked the betting question the project had
never asked and answered it negatively: 51.61%, CI [48.58%, 54.63%], which
contains 50% and does not reach the 52.38% break-even. Pick cards now carry
their own band's historical record (PR #18). The low-confidence finding was
re-derived after Booth flagged it unverifiable (PR #19) and it holds.

Booth is deployed and validated (PR #16-18). Its first real audit re-ran the
suite itself, performed the mutation itself rather than trusting the PR's
description of it, and found two genuine defects: a missing pytest install in
its own harness, and a CONFIRMED FINDING on the live dashboard with no script
behind it. A verifier catching the project breaking its own VERIFICATION.md
rule on its first outing is the strongest evidence this whole apparatus works.

**Stage 2 (2026-09-06, PRs #21-#24) corrected more than it built.** Four of its
seven items turned out not to be the item as written:

- **SOS was never broken.** The design audit recorded "an em-dash for all 32
  teams" and queued the column for removal or population. The computation was
  correct; the 2026 season had not started, and strength of schedule is defined
  over opponents actually played. Acting on the audit would have deleted a
  working feature for being audited in September. What was actually missing was
  any way to tell a legitimate blank from a broken pipeline.
- **The Team Deep-Dive page had never worked.** `load_team_history()` reads
  `data/team_history.json`; the file sat in `src/`. The missing-file branch
  returned `{}` in silence, so the live public page showed "No team history data
  available yet" for all 32 teams while the roadmap listed it as Done.
- **nfl_data_py is a real fallback**, verified by executing it rather than
  assuming: it imports, all three loaders work, every required column is there,
  and it agrees with nflreadpy exactly on 2025 week 10. So the pandas 1.x pin
  buys a working revert path.
- **The pandas 2.x unlock is not free.** Pre-declared hypothesis - log loss,
  Brier and AUC agree to four decimals across the major version - REFUTED. AUC
  moves up to 0.00125, 25x this project's own noise threshold, with both
  environments proven deterministic and scoring the same 1087 games. "Market
  alone", the one model with no EPA aggregation, is bit-identical; everything
  built on EPA features moves, which localises it to float aggregation over
  ~48k plays a season. Decision recorded in `requirements.txt`: keep the pin,
  revisit when something actually needs pandas 2.x, and regenerate every
  published figure as part of that work rather than discovering the shift after.

Also shipped in Stage 2: the Net Rating bar has a zero line and a printed
domain; the Changelog page is generated from `config.VERSION_HISTORY` rather
than a hand-maintained comment; picks are shareable by link, with a schedule
fingerprint that refuses a mismatched link instead of silently attaching picks
to the wrong fixtures.

### Stage 1 - Recurring status checks (first every session, don't dwell)

Injury/roster data is CLOSED, not blocked - settled on VALUE, not
availability, so stop re-checking nflverse for it. Ensemble contingency is
blocked solely on another independently-useful model existing. ESPN QBR stops
at 2023, quick re-check only. Public betting % has no free source; reverse
line movement is blocked downstream of it. Line-movement accumulation is
confirmed working and needs many more weeks before a real predictive test -
do not force one on a small sample. Closing-line backtest stays deferred on
that same accumulation.

### Stage 2 - Deferred UX & repo hygiene  <- COMPLETE (2026-09-06)

Shipped as PRs #21-#24. See "Finished, and why it matters" above; the four
corrections it produced are worth reading before starting anything that
assumes an audit finding is accurate.

### Stage 3 - Agent development  <- NEXT

Booth regression suite of deliberately-bad PRs it must catch; prompt-injection
resistance test; Scout pre-flight enforcing VERIFICATION.md before any PR
opens; structured agent decision log rendered as a dashboard page; inter-agent
disagreement protocol, currently undefined; Booth cost and latency
instrumentation; "Archivist" role regenerating the handoff from real repo state
- this file is the manual version of that.

Two additions from Stage 2's experience with Booth. It caught a **scope**
discrepancy no test could have - a PR whose description covered one of three
bundled features - and it repeatedly marked screenshot claims UNVERIFIABLE
because none were attached. Both belong in the regression suite: a
deliberately under-described PR it must flag, and a `VERIFICATION.md` rule that
a visual claim without an attached artifact does not count as evidence.

### Stage 4 - Automation & monitoring

Data-quality checks on every weekly run; play-by-play cache layer; alerts on
upstream nflverse schema changes; auto-open a PR when check_drift.py detects
real drift; nightly canary against the last completed week, which would have
caught the nflreadpy offseason crash days early; automated weekly summary;
reproducibility audit and expanded leak-free coverage. Also the alert and
communication layer for Booth, now that autonomous operation is confirmed.

Add: a **build-output smoke check**. The Team Deep-Dive page rendered empty for
months because a missing file returned `{}` quietly. A check that every page's
data payload is non-empty after a build would have caught it the same day.

### Stage 5 - Model depth, real hypotheses only

Residual analysis FIRST, since it tells you which of the rest are worth
attempting. Then market-implied probability calibration as a Model B feature;
per-team learned home-field advantage; rest and travel; weather and wind for
outdoor games; situational splits; multi-season QB priors; injury-adjusted QB
ratings, indefinitely parked with the injury data closed; learned blend weight
between Models A and B - if an ensemble doesn't beat both, that's a publishable
REJECT.

### Stage 6 - New data sources

Next Gen Stats via nflreadpy, the most promising untapped source already in the
stack; participation/personnel grouping; referee crew assignments, cheap and
testable; multi-book line dispersion, accumulation-gated under Stage 1 rather
than a new build. Each item needs a stated hypothesis BEFORE the data is
pulled, or it is fishing.

### Stage 7 - Portfolio polish

README rewrite for a cold technical reader; architecture diagram; case study of
the QB rating leak; public "lessons learned" page; write-up of the Booth
regression suite and injection test. Add a case study of Booth's first audit -
a verifier that caught a flaw in its own harness and an unreproduced claim on
the live dashboard is a better story than the feature it was auditing. Add a
second: the Stage 2 corrections, where four of seven queued items turned out to
be misdiagnosed, including a page that had never worked.

NOTE ON ORDER: this sits before the visual stages by explicit instruction, but
anything in it that shows the dashboard - screenshots, the architecture
diagram's UI layer, the lessons-learned page's framing - will be redone once
Stages 8-10 land. The text-only items (README, QB-leak case study, Booth case
study) are safe to do here; hold the visual ones.

## The visual overhaul (Stages 8-10)

Read this before starting any of the three. The brief is not "fix the audit
findings".

The 2026-09-06 audit scored the dashboard **15/40** and produced a list of real
defects: 21 font sizes, 31 spacing values with 63% off a 4px grid, seven
transition durations, no `prefers-reduced-motion` block, amber meaning five
different things. Every one of those is worth fixing. But they are all
**corrective** — fixing the entire list produces a dashboard that is clean,
consistent and unobjectionable. It does not produce one that makes someone stop
and look.

The stated goal is the second thing: **someone opens this dashboard and says
"that is amazing"**. That needs a visual point of view — a deliberate answer to
"what does this thing look like, and why" — that the tokens then serve. A
spacing scale with no concept behind it is just tidier arbitrary numbers.

So Stage 8 starts with the concept, and Stages 9 and 10 execute against it.
Treat the audit list as the floor, not the goal.

One live tension: everything built in Stages 2-7 uses hardcoded pixel values,
because the scales do not exist yet. That is deliberate and accepted — the
ordering was chosen so carried-over work ships first — but it means Stage 8's
job is bigger than the audit's counts suggest. Reuse an existing class before
inventing values; every new one is something Stage 8 has to unpick.

### Skills to use, and what each is for

These are available and should be used deliberately rather than mentioned.

- **`design`** (design canvas) — multi-artboard visual design published as an
  editable artifact. This is the right tool for the concept work at the top of
  Stage 8: explore two or three genuinely different directions as artboards
  before committing anything to code. Cheap to throw away, which is the point.
- **`artifact-design`** — design fundamentals; load before building any
  artifact, including the canvas above.
- **`dataviz`** — the chart method: form heuristic, the four colour jobs, mark
  specs, the hover/interaction layer, and the anti-pattern catalog. Its
  validator already produced this project's `--series` tokens
  (`scripts/validate_palette.js`, OKLab dE, CVD simulation, contrast). Every
  new colour in Stage 9 goes through it, in both themes. Its anti-patterns file
  is a checklist for Stage 10's charts.
- **`dashboard-design-audit`** — the 8-category scored audit that produced the
  15/40. Re-run it at the END of each visual stage and record the score. Three
  scores across three stages is a measurable claim about improvement rather
  than an assertion that things look better.
- **`design:design-critique`** — a second opinion on a direction before it is
  built out. Use it on the Stage 8 concept, not on the finished thing.
- **`design:accessibility-review`** — pairs with the Stage 9 focus/keyboard
  pass; contrast and CVD are already covered by the dataviz validator.
- **`artifact-diagramming`** — for Stage 7's architecture diagram, not these.

### Stage 8 - Design system foundations

**First, the concept.** Before any token changes: decide what this dashboard
looks like. It is a football analytics product that is honest about
uncertainty, publishes its own failures, and is read by technical hiring
managers. That is a real brief and it has a visual answer — the current page is
a competent dark dashboard with amber accents and no particular opinion.
Explore directions on a `design` canvas, get a `design:design-critique` pass,
pick one, and write the decision down here before writing CSS. Everything below
serves the chosen direction.

**Then the foundations**, which are the audit's list and are still all true:
a spacing scale replacing 31 ad-hoc values, 63% of which sit off a 4px grid; a
type scale replacing 21 distinct font sizes including seven half-pixel ones;
tabular figures across every numeric surface, currently used once in a
table-heavy dashboard; radius tokens replacing 8 values despite `--radius`
already existing; a motion system of two durations and one easing replacing
seven durations, plus a `prefers-reduced-motion` block which does not exist at
all; an elevation pass so the six shadow tokens are actually used.

Do the concept first. Tokens chosen to serve a direction are a design system;
tokens chosen to reduce a count are a tidier mess.

### Stage 9 - Colour, components & interaction

**A point of view on colour**, not only the removal of ambiguity. The
corrective work: retire the 33 hardcoded team-brand hex values driving
probability bars in favour of `--series` tokens — `teamColor()` falls back to a
hardcoded dark `--chalk-dim`, so it is wrong in light mode, and red-vs-blue
bars read as bad-vs-good rather than as two teams. Disambiguate amber, which
currently means brand, active nav, sorted column, flagged state and series-b at
once.

Beyond that: the Net Rating bar was deliberately left amber in Stage 2 with a
note saying sign-encoding belongs here. A diverging pair with a neutral
midpoint is the `dataviz` answer; run it through the validator in both themes
rather than picking by eye. Decide what confidence looks like, what a flagged
game looks like, and what "the model was wrong" looks like — the dashboard
currently says all three in the same amber.

Also: one button component with real variants and states; a focus and keyboard
pass paired with `design:accessibility-review`; unify the two `.game-card`
render paths.

### Stage 10 - Layout, tables & responsiveness

**The moments that make someone stop.** A dashboard that is merely consistent
is invisible. Decide where this one is allowed to be striking — an entry
moment, a hero number, a chart that is genuinely worth looking at — and build
those deliberately. The reliability diagram and the Net Rating table are the
strongest candidates; both are currently rendered as competently as possible
and no more.

**The corrective list**, all still true: fix the duplicate "Model Output"
sidebar group label so the nav's own headings mean something; a shared
page-header component across all 13 pages (Changelog was added in Stage 2);
a table system with sticky headers, scroll-edge affordance and consistent row
hover; a mobile pass covering bottom-nav clearance so the last row is not
covered, the ratings table clipping mid-column at 430px, and real breakpoints
beyond the three that exist; move the onboarding banner below the h1 where it
stops outranking the page title; empty, error and loading states across all
pages — the SOS note and the shared-picks banner from Stage 2 are the first two
and should fold into whatever system this produces.

**One known data-viz defect to fix here**: the Playoff Odds bars are normalised
to the highest team's odds rather than to 0-100%, so a league leader at 40%
renders as a full-width bar reading as near-certainty. Same family as the
missing zero line — a scale that is not what the reader assumes. Found during
Stage 2 and deliberately left for this stage.

Finish with a `dashboard-design-audit` re-run and record the score against the
starting 15/40.

## Environment and workflow

- Real clone lives on the user's Windows PC `markys` at `E:\NFL-Model-2`
  (E: drive deliberately — C: is short on space). Desktop Commander and
  GitKraken MCP plugins are available there; run tests and heavy backtests on
  that machine, not in the cloud sandbox, which has no nflverse network access.
- The cloud sandbox clone is scratch. It cannot push — the repo is not in the
  session's authorised set. Commits and pushes happen on `markys`.
- **Playwright lives in the cloud sandbox, not on `markys`.** For screenshots:
  regenerate `index.html` on `markys`, stage it into the sandbox, and drive
  Chromium there. This is the only practical way to actually look at the page.
- The full backtest takes ~42 seconds. It is not the expensive step people
  assume; run it when a question needs it.
- Production-code changes go through a PR the user reviews. Pure
  dashboard/documentation changes may go straight to main.
- **One item, one PR.** Booth flagged a PR bundling three undisclosed features:
  a reviewer approving on the description alone approves more than they think.
  If a branch grows past its title, either split it or rewrite the description.
- **`.github/` is write-protected against remote tooling.** Workflow edits must
  be made by the user in GitHub's web editor; walk them through it step by step.
- No `gh` CLI and no PR-body-edit tool. A PR description can be corrected only
  by the user in the web UI, so get the description right when opening it.
- `cmd` mangles multi-line `python -c` strings, and **PowerShell has no
  heredocs** — `git commit -F <file>` with a written message file, and script
  files instead of inline `-c`, are the reliable forms.

## Traps that have actually bitten

- **`git reset --hard` and `git checkout --` have destroyed in-progress edits
  three times.** Before any restore, check what is uncommitted; prefer
  re-applying a known edit over reverting a whole file. When mutation-testing a
  file that holds uncommitted work, restore from a byte-level backup taken in
  the script, never from git.
- The dashboard workflow used to commit its own build timestamps —
  `src/prune_build_churn.py` prevents it. Run it after regenerating locally.
  **But it is wired into only one of the two workflows that regenerate.**
  `generate-dashboard.yml` runs it before committing; `weekly-update.yml`
  regenerates the dashboard and commits `index.html dist/**` with no prune
  step at all. So the guard this file has described since 2026-08 as simply
  "preventing" the churn covers one path and not the other. It only bites when
  a weekly run produces no real data change — the offseason state — which is
  exactly when nobody is watching. One line to fix, in `.github/`, so it needs
  a web-editor edit.
- **A zero-line binary diff is not automatically churn.** An auto-commit
  showing `dist/picks_2026_week1.pdf | Bin 3802 -> 3802 bytes, 0 insertions,
  0 deletions` looks exactly like the timestamp churn above, and on 2026-09-07
  I nearly reported the guard as broken on that basis. It was not.
  `prune_build_churn.py` deliberately does NOT normalise the "generated
  `<date>`" line printed inside the picks PDF, because that is visible content
  on a page someone prints — a rebuild on a different day is a REAL change and
  should commit. The byte count is identical because a date string is the same
  length either way. Its docstring says all of this. Read what a normaliser
  deliberately excludes before concluding it failed; the symptom of "working
  as designed" and "broken" are byte-identical here.
- `backtest()` calls `dropna(subset=features)`, so different feature sets can
  silently evaluate different game sets. Any paired comparison must verify the
  row sets match rather than assume it (`bootstrap_brier_gap.py` does, and
  `compare_pandas_versions.py` checks it before reading any metric).
- `home_margin` exists in the feature table for ATS work and must never enter a
  feature list — it is the scoreline being predicted.
- **The Claude Code action refuses to run when a PR's copy of its workflow file
  differs from `main`'s.** It skips with a *success* status and a validation
  message, which looks like nothing happened. This is a security control, not a
  bug. Consequence: after changing `booth-pr-audit.yml` on `main`, any open PR
  must merge `main` in before Booth will audit it, and "re-run the job" does not
  help, because a re-run replays the original workflow definition.
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
