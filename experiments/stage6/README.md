# Stage 6 — new data sources, pre-registered

`registry.json` is the plan for Stage 6: every question it will ask, the rule that decides
each one, and one budget for the whole stage. It was committed before any Next Gen Stats
data was loaded. `results/` will hold one file per answer.

## The questions

Next Gen Stats first, in order, each only if the one before it allows:

- **N1, a screen.** Do four Next Gen Stats passing numbers (completion over expected, time
  to throw, aggressiveness, intended air yards) predict a quarterback's next game better
  than his recent EPA plus the completion-over-expected column play-by-play already has?
  Fitted on 2017–2021, scored on 2022–2023. It spends no slot. If it fails, Stage 6 asks
  nothing more of Next Gen Stats.
- **N2.** Model A plus a Next Gen Stats quarterback feature, against Model A as it ships.
- **N3.** The same feature against one built from play-by-play CPOE instead. Only run if
  N2 is accepted, because a gain that the data we already load can deliver is not a
  reason to add a source.
- **A1.** Whether last week's Next Gen Stats rows are published before the Tuesday run.
  Checked only if N2 and N3 are both accepted: a feature the live pipeline cannot feed
  would make the page describe a better model than the one making the picks.

Rushing and receiving Next Gen Stats are deferred with the reason written down.

Referees and personnel, registered 2026-09-28, before any referee or penalty value was
read:

- **R1, a screen.** Do referees flag home and away teams differently in a way that
  lasts? Each game's penalty yards against the away team minus those against the home
  team, averaged per referee over 2016–2020 and again over 2021–2023, correlated across
  referees with enough games in both. It spends no slot. If the interval does not sit
  above zero, Stage 6 asks nothing more of referees. It reads nothing from 2024 on.
- **R2.** Model A plus the referee's earlier home edge, shrunk toward the league average,
  against Model A as it ships. Only if R1 passes.
- **A2.** Whether the referee is named in the schedule before the Thursday lock. Checked
  only if R2 is accepted.
- **P1, personnel groupings: deferred.** No mechanism that reaches a result beyond what
  the ratings already measure, and recent-season data has not been checked.

The expectation, written before any data: R1 fails.

## The budget

Five confirmatory slots for all of Stage 6, so each confirmatory interval is 99% rather
than 95%. Next Gen Stats can spend at most two (N2 and N3), referees at most one (R2).
Personnel groupings, if ever registered, go into the same file under the same budget;
`budget_m` does not change when they are.

## What keeps this honest

`tests/test_stage6_registry.py` checks that every result was registered in an earlier
commit with the same wording, that every stored label is the one its numbers give, that
a question whose precondition failed has no result, that the budget is not overspent,
and that nothing touches the 2026 season.

## Results (2026-09-26)

Registered in `60d6729`. `results/` holds one file per answer; the figures below are
checked against it by `tests/test_stage6_published_numbers.py`.

| id | question | result | the number it rests on |
|---|---|---|---|
| N1 | Next Gen Stats vs play-by-play, next-game QB EPA | FAIL | candidate minus control MSE +0.00026 [−0.00036, +0.00090] |
| N2 | Next Gen Stats feature in Model A | not run: N1 failed | — |
| N3 | Next Gen Stats vs play-by-play CPOE in Model A | not run: N1 failed | — |
| A1 | published before the Tuesday run | not checked: nothing was accepted | — |
| N4 | rushing and receiving | DEFERRED | — |

**Next Gen Stats did not help.** Fitted on 2,632 quarterback games from 2017–2021 and
scored on 1,101 from 2022–2023, adding the four Next Gen Stats numbers made the
predictions slightly worse, not better: weighted mean squared error 0.08028 against
0.08001 without them. The 95% interval runs from better to worse, so there is no real
difference either way, and the registered rule needs a clear improvement. None of
Stage 6's five slots were spent.

**Play-by-play CPOE added nothing either** (control minus base +0.0000044), which is not
a registered test but is worth knowing: a quarterback's recent EPA per dropback already
carries what completion percentage over expected says about his next game.

What this does not say: that Next Gen Stats is useless. It says these four passing
numbers, averaged the way the model averages everything else, do not predict next week
beyond what the model already knows. That is the question that was registered.
