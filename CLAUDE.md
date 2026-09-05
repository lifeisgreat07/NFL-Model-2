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

The ten-stage plan below is the canonical roadmap. It was written before the
2026-09-04 compaction, lost with it, and recovered from the user's own chat
scrollback on 2026-09-05. Status notes are current as of that date. Keep this
list here, not in chat.

Stage 1 - Quick status checks (recurring, first every session, don't dwell)
Injury/roster data (CLOSED 2026-09-04, and note this is a change from
"blocked": the data question was settled on VALUE, not availability -- a QB is
Out in only 6.9% of team-weeks and `qb_change_diff` already covers it, so stop
re-checking nflverse for it); ensemble contingency (still blocked, now solely on
another independently-useful model existing); ESPN QBR (source abandoned, stops
at 2023 -- quick re-check only); public betting % (blocked, no free accessible
source -- quick re-check only); line-movement accumulation (CONFIRMED WORKING
end-to-end; needs many more weeks before a real predictive test, do not force
one on a small sample); reverse line movement (blocked downstream of public
betting %, not independently actionable).

Stage 2 - Deferred dashboard UX
Print/PDF view of the week's picks (DONE); Team Deep-Dive game drill-down
(remaining); shareable picks link (remaining).

Stage 3 - Repo hygiene & reproducibility quick wins
Pin `requirements.txt` (DONE); remove `ol_continuity` dead code (DONE, but
NARROWED -- it turned out not to be dead: `backtest.py` uses it for
"[reference only]" rows and four leak-free tests cover it, so it was removed
from the live weekly path only); `run-backtest.yml` workflow_dispatch (DONE,
plus `pip freeze` provenance); auto-generated changelog page from `config.py`
(remaining); resolve whether `nfl_data_py` is a real fallback or cruft
(remaining -- tied to the queued pandas 2.x/3.x unlock experiment, which must be
judged on log loss/Brier/AUC, never accuracy).

Stage 4 - Evaluation honesty (methodological gate -- do before Stages 8-9)
Calibration curve and reliability diagram (DONE, PR #13); against-the-spread
evaluation with real CIs (DONE, PR #16 -- 51.61%, CI [48.58%, 54.63%], no edge,
does not clear the 52.38% break-even); backtest against the closing line
(DEFERRED, gated on line-history accumulation); confidence-interval display on
picks (REMAINING -- the last item in this stage); isotonic/Platt recalibration
only if warranted (CLOSED -- already REJECTED on Model Lab, and the reliability
diagram shows no material miscalibration, so the condition is not met). Also
landed here unplanned: the paired bootstrap (PR #15), which killed the
Model-B-vs-market lead and confirmed two new findings, and the build-churn fix
(PR #14).

Stage 5 - Deploy Booth for real  <- NEXT
`ANTHROPIC_API_KEY` repo secret; install the Claude GitHub App; upload
`booth-pr-audit.yml` (remember `.github/` is write-protected against remote
tooling, so this needs a web-editor walkthrough); open a real test PR and
confirm Booth actually fires, re-executes and posts a genuine report -- not just
that the workflow runs green; build the alert/communication system once
autonomous operation is confirmed.

Stage 6 - Agent development
Booth regression suite of deliberately-bad PRs it must catch; prompt-injection
resistance test; Scout pre-flight check enforcing `VERIFICATION.md` before any
PR opens; structured agent decision log rendered as a dashboard page;
inter-agent disagreement protocol (currently undefined); Booth cost and latency
instrumentation; "Archivist" role regenerating the handoff from real repo state
(note: this file is the manual version of that).

Stage 7 - Automation & monitoring
Data-quality checks on every weekly run; play-by-play cache layer; alerts on
upstream nflverse schema changes; auto-open a PR when `check_drift.py` detects
real drift; nightly canary against the last completed week (would have caught
the `nflreadpy` offseason crash days early); automated weekly summary report;
reproducibility audit and expanded leak-free coverage.

Stage 8 - Model depth, real hypotheses only
Residual analysis FIRST, since it tells you which of the rest are worth
attempting; market-implied probability calibration as a Model B feature;
per-team learned home-field advantage; rest and travel features; weather and
wind for outdoor games; situational splits; multi-season QB priors;
injury-adjusted QB ratings (gated on Stage 1's injury data, which is now closed,
so treat as indefinitely parked); learned blend weight between Models A and B
(if an ensemble doesn't beat both, that's a publishable REJECT).

Stage 9 - New data sources
Next Gen Stats via nflreadpy (most promising untapped source already in the
stack); participation/personnel grouping; referee crew assignments (cheap, real,
testable); multi-book line dispersion as an uncertainty signal (infrastructure
exists, so this is accumulation-gated analysis under Stage 1, not a new build).
Each item needs a stated hypothesis BEFORE the data is pulled, or it is fishing.

Stage 10 - Portfolio polish
README rewrite for a cold technical reader; architecture diagram; written case
study of the QB rating leak; public "lessons learned" page; dedicated write-up
of the Booth regression suite and injection test (if Stage 6 works, that is the
most employer-relevant material in the project).

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
