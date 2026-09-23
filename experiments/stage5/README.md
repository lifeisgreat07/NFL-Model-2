# Stage 5 — model experiments, pre-registered

`registry.json` is the whole plan: every question Stage 5 will ask, the rule that decides
each one, and the budget that sets how strict that rule is. The file was committed and
pushed before any of its questions were answered. `results/` holds one file per answer.

## How to read a result

Each `results/<id>.json` records:

- the registry entry it answered, copied word for word;
- the commit it was run at;
- the numbers: log loss, Brier and accuracy for both sides, and the paired-bootstrap
  interval on the log-loss difference;
- the label, which `src/stage5_eval.py` computes from those numbers.

A negative difference favours the candidate.

The screen runs on the validation seasons (2022–2023). A candidate only reaches the
confirmation seasons (2024–2025) if its validation log loss is lower. Every candidate that
reaches confirmation spends one of the family's ten slots, whether it passes or not. That
is why each confirmatory interval is 99.5% rather than 95%.

## What keeps this honest

`tests/test_stage5_registry.py` checks four things:

- every result was registered in an **earlier commit** with the same wording;
- every label matches what its own numbers give;
- the budget is not overspent;
- nothing touches the 2026 season, which is the forward test for anything accepted.

## Running it

```
python src/stage5_run.py build      # feature table + parity check against production
python src/stage5_run.py run H1     # answer one registered question
```

`build` refuses to save unless the harness's copy of the published feature table matches
`weekly_update.build_historical_features` row for row.

## Results (first pass, 2026-09-22)

Registered in `54a6744`. Answers were committed after it. Differences are candidate minus incumbent
log loss on the seasons shown, so negative favours the candidate. The interval is 99.5% on
confirmation and 95% on the validation screen. Each file in `results/` has the rest.

| id | question | label | validation diff | confirmation diff [99.5% interval] |
|---|---|---|---|---|
| Q0 | published backtest's in-game QB vs the announced starter (2022–25) | NO MEASURABLE GAP | — | Model A −0.0020 [−0.0099, +0.0060] |
| H1 | announced starter instead of last week's QB | INCONCLUSIVE | −0.0142 | −0.0109 [−0.0319, +0.0096] |
| H2 | moneyline instead of spread | NOT ADVANCED | +0.0029 | — |
| H3 | add success-rate ratings | INCONCLUSIVE | −0.0002 | +0.0000 [−0.0007, +0.0007] |
| H4 | down-weight decided-game plays | NOT ADVANCED | +0.0002 | — |
| H5 | separate pass and rush ratings | NOT ADVANCED | +0.0001 | — |
| H6 | early downs only | NOT ADVANCED | +0.0016 | — |
| H7 | state-space (Kalman) ratings | NOT ADVANCED | +0.0007 | — |
| H8 | rest advantage | INCONCLUSIVE | −0.0014 | +0.0021 [−0.0041, +0.0085] |
| H9 | weather and wind | DEFERRED | — | — |
| H10 | learned blend of Model A and the market | INCONCLUSIVE | −0.0033 | +0.0005 [−0.0056, +0.0060] |
| H11 | every accepted change together | not run: nothing was accepted | — | — |

Four of the ten confirmatory slots are spent: H1, H3, H8 and H10.

**Nothing was accepted.** Six rating and feature ideas moved log loss by less than 0.003 on
validation, and none survived confirmation. The ridge ratings are close to what this data can
support at this sample size. Two of these were the ones expected to matter:

- **H7 (the Kalman filter) did not beat ridge.** Its fitted between-season carry-over
  (`kalman_fit.json`, `rho`) is 0.45,
  meaning just under half of a team's strength carries into the next season. That is interesting
  on its own, but it didn't improve predictions.
- **H10 (the blend) is the publishable null the Stage 5 plan asked for.** Learning how much to
  trust Model A next to the market does no better than Model B's plain regression.

**The one real signal is H1, and it's about the live pipeline, not the model.**
`residuals.json` (descriptive, no interval) shows where it comes from. In 262 of the 1,087 games,
last week's quarterback was not the announced starter for at least one side. On those games the
live Model A's mean log loss is 0.696, against 0.654 with the announced starter. On the other 825
games the two are 0.654 and 0.651. The mechanism is where H1 says it is. The confirmation interval
still contains zero at the 99.5% level the budget requires, so the label is INCONCLUSIVE, and it
stays that way.

**What Q0 means for the published figures.** The backtest the dashboard publishes scores each game
with the quarterback who took the most dropbacks *in that game*. Across 2022–2025 that scores
almost exactly the same as using the announced starter (Q0). So the published Model A figures
describe a model that knows the real starter before kickoff. The live pipeline doesn't know that:
it uses last week's quarterback, and on the same games its log loss is 0.664, not 0.650
(`residuals.json`, all games). That gap is a comparison between two scoring methods, not a
registered test. It still means the page describes a better model than the one making the weekly
picks.

The forward test runs after the 2026 season. With nothing accepted, the only thing it could score
is whatever the live pipeline is changed to do about H1.
