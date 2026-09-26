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

## The budget

Five confirmatory slots for all of Stage 6, so each confirmatory interval is 99% rather
than 95%. Next Gen Stats can spend at most two (N2 and N3). Referee crews and personnel
groupings are added to the same file later, under the same budget; `budget_m` does not
change when they are.

## What keeps this honest

`tests/test_stage6_registry.py` checks that every result was registered in an earlier
commit with the same wording, that every stored label is the one its numbers give, that
a question whose precondition failed has no result, that the budget is not overspent,
and that nothing touches the 2026 season.
