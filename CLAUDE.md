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
  `tests/test_published_bootstrap_numbers.py` and `tests/test_ats_evaluation.py`
  are the pattern — every figure printed on the dashboard must exist in the JSON
  it came from.

## Current state (update this when it changes)

Model v2.4. `TRAIN_SEASONS` 2020-2025, `BACKTEST_SEASONS` 2022-2025,
`QB_SHRINK_K = 8`, `RIDGE_ALPHA = 15.0`, `RECENCY_HALF_LIFE = 16`.
Canonical `BACKTEST_ACCURACY` moves only on a deliberate re-run.

The stage plan was renumbered on 2026-09-06. The original ten-stage plan's
Stages 2-5 are now finished, so carrying their numbering forward would have
meant a roadmap that was mostly struck through. What follows replaces it. The
old numbering appears nowhere else; if you find a reference to "Stage 4 -
evaluation honesty" or "Stage 5 - deploy Booth", it predates this rewrite.

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

### Stage 1 - Recurring status checks (first every session, don't dwell)

Injury/roster data is CLOSED, not blocked - settled on VALUE, not
availability, so stop re-checking nflverse for it. Ensemble contingency is
blocked solely on another independently-useful model existing. ESPN QBR stops
at 2023, quick re-check only. Public betting % has no free source; reverse
line movement is blocked downstream of it. Line-movement accumulation is
confirmed working and needs many more weeks before a real predictive test -
do not force one on a small sample. Closing-line backtest stays deferred on
that same accumulation.

### Stage 2 - Design system foundations  <- NEXT

From the 2026-09-06 design audit, which scored the dashboard 15/40. These are
the tokens everything else depends on, so they go first. Spacing scale
replacing 31 ad-hoc values, 63% of which sit off a 4px grid; type scale
replacing 21 distinct font sizes including seven half-pixel ones; tabular
figures across every numeric surface, currently used once in a table-heavy
dashboard; radius tokens replacing 8 values despite --radius already
existing; a motion system of two durations and one easing replacing seven
durations, plus a prefers-reduced-motion block which does not exist at all;
an elevation pass so the six shadow tokens are actually used.

### Stage 3 - Colour, components & interaction

Retire the 33 hardcoded team-brand hex values driving probability bars in
favour of --series tokens - teamColor() falls back to a hardcoded dark
--chalk-dim, so it is wrong in light mode, and red-vs-blue bars read as
bad-vs-good rather than as two teams. Disambiguate amber, which currently
means brand, active nav, sorted column, flagged state and series-b at once.
One button component with real variants and states. A focus and keyboard pass.
Unify the two .game-card render paths. Run every new token through the palette
validator in both themes.

### Stage 4 - Layout, tables & responsiveness

Fix the duplicate "Model Output" sidebar group label so the nav's own headings
mean something. A shared page-header component across all 12 pages. Table
system with sticky headers, scroll-edge affordance and consistent row hover.
Mobile pass: bottom-nav clearance so the last row is not covered, the ratings
table clipping mid-column at 430px, and real breakpoints beyond the three that
exist. Move the onboarding banner below the h1 where it stops outranking the
page title. Empty, error and loading states across all pages.

### Stage 5 - Deferred UX & repo hygiene

Team Deep-Dive game drill-down; shareable picks link; auto-generated changelog
page from config.py's version history; resolve whether nfl_data_py is a real
fallback or cruft, tied to the queued pandas 2.x/3.x unlock experiment - judged
on log loss/Brier/AUC, never accuracy; Net Rating bar rebuilt with a zero
baseline and a scale; remove or populate the SOS column, currently an em-dash
for all 32 teams. OPEN BUG: booth-pr-audit.yml does not install pytest, so
Booth installs it mid-audit. One line, but .github/ needs a web-editor edit and
must land on main before it takes effect anywhere.

### Stage 6 - Agent development

Booth regression suite of deliberately-bad PRs it must catch; prompt-injection
resistance test; Scout pre-flight enforcing VERIFICATION.md before any PR
opens; structured agent decision log rendered as a dashboard page; inter-agent
disagreement protocol, currently undefined; Booth cost and latency
instrumentation; "Archivist" role regenerating the handoff from real repo state
- this file is the manual version of that.

### Stage 7 - Automation & monitoring

Data-quality checks on every weekly run; play-by-play cache layer; alerts on
upstream nflverse schema changes; auto-open a PR when check_drift.py detects
real drift; nightly canary against the last completed week, which would have
caught the nflreadpy offseason crash days early; automated weekly summary;
reproducibility audit and expanded leak-free coverage. Also: the alert and
communication layer for Booth, now that autonomous operation is confirmed.

### Stage 8 - Model depth, real hypotheses only

Residual analysis FIRST, since it tells you which of the rest are worth
attempting. Then market-implied probability calibration as a Model B feature;
per-team learned home-field advantage; rest and travel; weather and wind for
outdoor games; situational splits; multi-season QB priors; injury-adjusted QB
ratings, indefinitely parked with the injury data closed; learned blend weight
between Models A and B - if an ensemble doesn't beat both, that's a publishable
REJECT.

### Stage 9 - New data sources

Next Gen Stats via nflreadpy, the most promising untapped source already in the
stack; participation/personnel grouping; referee crew assignments, cheap and
testable; multi-book line dispersion, accumulation-gated under Stage 1 rather
than a new build. Each item needs a stated hypothesis BEFORE the data is
pulled, or it is fishing.

### Stage 10 - Portfolio polish

README rewrite for a cold technical reader; architecture diagram; case study of
the QB rating leak; public "lessons learned" page; write-up of the Booth
regression suite and injection test. Add a case study of Booth's first audit -
a verifier that caught a flaw in its own harness and an unreproduced claim on
the live dashboard is a better story than the feature it was auditing.

## Environment and workflow

- Real clone lives on the user's Windows PC `markys` at `E:\NFL-Model-2`
  (E: drive deliberately — C: is short on space). Desktop Commander and
  GitKraken MCP plugins are available there; run tests and heavy backtests on
  that machine, not in the cloud sandbox, which has no nflverse network access.
- The cloud sandbox clone is scratch. It cannot push — the repo is not in the
  session's authorised set. Commits and pushes happen on `markys`.
- Production-code changes go through a PR the user reviews. Pure
  dashboard/documentation changes may go straight to main.
- **`.github/` is write-protected against remote tooling.** Workflow edits must
  be made by the user in GitHub's web editor; walk them through it step by step.
- `cmd` mangles multi-line `python -c` strings. Write a script file instead.

## Traps that have actually bitten

- **`git reset --hard` and `git checkout --` have destroyed in-progress edits
  three times.** Before any restore, check what is uncommitted; prefer
  re-applying a known edit over reverting a whole file.
- The dashboard workflow used to commit its own build timestamps —
  `src/prune_build_churn.py` now prevents it. Run it after regenerating locally.
- `backtest()` calls `dropna(subset=features)`, so different feature sets can
  silently evaluate different game sets. Any paired comparison must verify the
  row sets match rather than assume it (`bootstrap_brier_gap.py` does).
- `home_margin` exists in the feature table for ATS work and must never enter a
  feature list — it is the scoreline being predicted.
- **The Claude Code action refuses to run when a PR's copy of its workflow file
  differs from `main`'s.** It skips with a *success* status and a validation
  message, which looks like nothing happened. This is a security control, not a
  bug — it stops a PR editing the workflow and having it run with repository
  credentials. Consequence: after changing `booth-pr-audit.yml` on `main`, any
  open PR must merge `main` in before Booth will audit it, and "re-run the job"
  does not help, because a re-run replays the original workflow definition.
- A guard whose comment claims more than its code delivers has now appeared
  three times: the leak test that flagged a `dropna` subset, the "superseded
  figures" check that banned its own honest disclosure, and the "quotes the
  reproduced figures" check that passed a half-revert. **Mutation-test every new
  guard** — write the failure it is supposed to catch and confirm it catches it.
