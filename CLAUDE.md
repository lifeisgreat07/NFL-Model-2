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

Model v2.4. `TRAIN_SEASONS` 2020–2025, `BACKTEST_SEASONS` 2022–2025,
`QB_SHRINK_K = 8`, `RIDGE_ALPHA = 15.0`, `RECENCY_HALF_LIFE = 16`.
Canonical `BACKTEST_ACCURACY` moves only on a deliberate re-run.

Stage 1–2 — Foundations, cleanup, calibration data; done. Injury/availability
data investigated and CLOSED on value, not availability; snap-count dependency
removed from the live path; requirements pinned; `.gitattributes` added after
real PDF corruption on a Windows checkout; `calibration.py` written.

Stage 3 — Calibration & evaluation depth; nearly done. Reliability diagram with
Wilson intervals and the Murphy decomposition (PR #13); chart-palette defect
found and fixed with a validator-backed test (PR #13); build-churn fix (PR #14);
paired bootstrap, which killed the Model-B-vs-market lead and confirmed two new
findings (PR #15); ATS evaluation, no edge (in flight). Remaining: confidence
intervals on the picks display. Deferred: closing-line backtest, still gated on
line-history accumulation.

Stage 4 — Deploy Booth & agent development; next. API key as a repo secret,
Claude GitHub App, `booth-pr-audit.yml`, a real test PR proving the verifier
catches something; then Booth regression suite, prompt-injection test, Scout
pre-flight, decision log, disagreement protocol, cost instrumentation, Archivist.

Stages 5–7 — Automation & monitoring; model depth & new data sources; v3.0
dashboard visual overhaul & portfolio polish. **Coarse — these need re-expanding
into concrete items before starting.** Their original detail was lost in the
2026-09-04 compaction.

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
