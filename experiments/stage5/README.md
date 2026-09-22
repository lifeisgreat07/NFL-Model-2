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
