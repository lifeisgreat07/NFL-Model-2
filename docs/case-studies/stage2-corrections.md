# When the to-do list was wrong

**In one paragraph.** Stage 2, finished on 2026-09-06, was seven queued
items: small features, a bug, and two open questions about dependencies.
Two of the items were wrong about the thing they described. The strength of
schedule column was "broken" only because the season hadn't started, and
acting on it would have deleted a working feature. The Team Deep-Dive page,
listed as done, had never worked at all. The plan later summed Stage 2 up as
"four of seven queued items misdiagnosed". That count doesn't hold up
either, which is part of the story. The
same shape kept turning up in later stages, and the rule that came out of it
is the one this project leans on most: a queued finding is a hypothesis, not
a defect.

## The seven items

The plan for Stage 2 (PRs #21 to #24) listed: a game drill-down on Team
Deep-Dive; a shareable picks link; a changelog page generated from the
model's version history; whether the old data library, nfl_data_py, was a
real fallback or dead weight, tied to whether moving to pandas 2 would change
the numbers; a zero line and scale for the Net Rating bar; "remove or
populate" the strength of schedule (SOS) column; and a bug, Booth's workflow
not installing pytest.

The share link, the changelog page, the Net Rating bar and the pytest fix
went as planned. So did the drill-down, except that building it exposed that
the page under it had never worked. What follows is the two findings that
were wrong, and the one open question whose two answers were not the
convenient ones.

## Two that were wrong

**The SOS column was never broken.** A design audit that day recorded it
as an em-dash for all 32 teams and queued it to be removed or filled in
(`9e4ec47`). The code was right. Strength of schedule is an average over
opponents already played, and the 2026 season hadn't started. The
playoff-odds file showed games_played 0 and games_remaining 272. Removing
the column would have deleted a working feature for being audited in
September.

What was missing was a way to tell the two states apart: a blank that means
"no games yet" and a blank that means "the pipeline broke" looked identical.
The page now says which one it is, and a test checks the case that would
actually be a failure, a team with games played and no SOS.

**The Team Deep-Dive page had never worked.** The roadmap listed it as done,
and the drill-down item was written on the assumption that it was.
Its loader read `data/team_history.json`, but the file had sat in `src/`
since it was uploaded. When the file was missing, the loader returned an
empty result and said nothing, so every build published a page reading "No
team history" for every team (`5e52457`). Nobody noticed, because nothing
failed. Building the planned drill-down on top of it is what exposed it. The
file moved to where the loader looks, and the missing-file branch now warns
instead of going quiet.

## A question, not a diagnosis

**nfl_data_py was a real fallback.** The item asked whether it was "a real
fallback or cruft". Nothing had ever run it. Running it showed that it
imports, all three loaders work, every column the project uses is there, and
on 2025 week 10 it agrees with the current library exactly (`f71e39c`).

**Moving to pandas 2 is not free.** The hypothesis was stated before the
runs: log loss, Brier and AUC agree to four decimals across the two versions.
It was refuted. Both setups proved deterministic on repeat runs, and AUC
still moved by up to 0.00125, 25x that threshold (`f71e39c`). The one model
that uses no play-by-play aggregation came out bit-identical, which pins the
cause to float arithmetic over play-level data. The decision was to keep
pandas 1 until something needs pandas 2.

Both answers mattered, but nothing here was misdiagnosed. It was an honest
question, and the answers were the less convenient ones. When Stage 2
closed, the plan rolled everything above into one line: "four of seven queued
items were misdiagnosed" (`69c3b18`). Counted against the list, the four findings came
from three items, and two of the four were answers to that open question,
not wrong diagnoses. The line went into the document that now carries this
project's warnings about unchecked counts, and it sat there unchecked.

## It kept happening

- **The Roadmap page (#41).** The plan said its "Done" list duplicated the
  changelog and could be deleted. Checked before deleting: the changelog held
  model versions; the Done list held 16 mostly-PRODUCT milestones, and only
  about 3 overlap (`0d6c8e1`). Following the plan would have deleted the only
  record of most of what had been built, with every test green. The content
  moved instead.
- **The filter buttons (#68).** A button on the Week Board stayed highlighted
  after being tapped on a phone, and the plan filed it as a focus state to
  fix in a later accessibility pass. It wasn't focus and it wasn't touch: the
  click handler selected every element wearing a shared style class, and six
  of the nine it picked up weren't filters (`8d46f82`). It reproduced with a
  plain scripted click.

## Lessons

1. **A queued finding is a hypothesis.** Read the code and render the page
   before doing the work the finding implies.
2. **Check the measurement and the explanation separately.** The SOS column
   really was blank, and the Done list really did overlap the changelog a
   little. What was wrong in each case was the "so", the reason attached to
   the observation, and that is the half nobody had checked.
3. **Silence is the most expensive failure.** The Team Deep-Dive page
   shipped empty, and stayed empty, because a missing file produced a quiet
   empty result. A loud error would have been found the day it happened.
4. **Before deleting what a plan says is redundant, prove it is redundant.**
   A deletion that loses content leaves no failing test behind.
