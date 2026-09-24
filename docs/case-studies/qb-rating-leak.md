# The QB rating that could see the future

**In one paragraph.** On 2026-08-31 a test written to prove the quarterback
ratings were leak-free failed. The ratings were shrunk toward a league average
computed over every season in the data, so a prediction for 2022 was quietly
using 2023-2025. The fix was one function. The same afternoon turned up two
worse problems: the repository's own leak-free test suite had never run a
single check, and a published tuning decision could not be reproduced. The
leak itself turned out to barely matter, which was measured on 2026-09-24,
and that is part of the story too.

## What leaked

A quarterback's rating is his recent EPA per dropback, blended toward the
league average so that a backup with 30 dropbacks is not rated like an MVP.
`QB_SHRINK_K` sets how hard the blend pulls.

The blend's anchor was one number, computed once, over the whole input:

```python
league_avg = df['qb_epa'].mean()        # every dropback, 2020-2025
...
return (n_eff * weighted_avg + QB_SHRINK_K * league_avg) / (n_eff + QB_SHRINK_K)
```

The QB's own plays were correctly cut off at the prediction week. The anchor
was not. In the backtest every rating was built from 2020-2025 data, so a
2022 week-5 rating was pulled toward an average that already included three
seasons that had not been played yet. The module's own docstring said
"leak-free".

The fix (`ec30887`) made the anchor "league average as of this week": a
running sum and count per week, so the average only ever sees plays before
the cutoff.

## How it was found

Not by reading the code. A test was written for the property the docstring
claimed: build a rating as of week 2, then change only week 2's plays to an
absurd value, and rebuild. If the rating moves, something after the cutoff is
reaching it.

It moved from -0.3995 to 95.87 (`ec30887`'s message records both). The first
commit (`6e676e0`) landed the test failing, with the message saying so, and
left the fix for a separate decision. That order matters: a test written
after the fix is fitted to the fix. A test that failed first shows it can.

## What else turned up that afternoon

**The existing leak-free suite had never worked.** `main` already had its own
`tests/test_leak_free.py`. Run rather than read, 4 of 5 of its tests failed
on an import error, because its path setup pointed at a directory that did not
exist, and the fifth skipped itself inside a `try/except` (`8a0899f`). It
looked like protection and had never checked anything. The two suites were
merged into the one that exists today.

**A published tuning decision could not be reproduced.** A week earlier,
2026-08-24, `QB_SHRINK_K` had been retuned from 8 to 96 and recorded on the
dashboard as ACCEPT. Nothing in the repository could reproduce its numbers.
Two changes since had altered what it was being compared against: a feature
was removed, and the backtest switched to refitting weekly. (The leak was
checked separately and was not the cause.) So a real script,
`src/tune_qb_shrink_k.py`, was committed and run: tune on 2022-2023 only,
confirm on 2024-2025. It picked k=128, and on the confirmation seasons the
paired bootstrap interval was [-1.65, +1.29] points of accuracy, which
includes zero (`a86c470`). Looked at across metrics, k=8 won 3 of 4
(`870f636`). So the constant went back to 8, the dashboard row changed from
ACCEPT to INCONCLUSIVE, and `src/config.py` keeps the whole history above
the constant rather than only its latest value.

## How much did the leak matter?

Nobody measured it at the time. The fix, the retune and the revert shipped in
one pull request (#5), so the leak's own effect was never separated out. The
Methodology page has called it "a real (small) leak" since `8a0899f`, with no
number behind the word.

`src/measure_qb_leak.py` separates it, on today's code. It loads the data
once and builds the feature table twice. The only difference is which
`trailing_rating` function the builder gets: today's, or the pre-fix one
copied exactly from `ec30887`'s parent. It refuses to report unless every
non-QB column is identical between the two tables and both runs score the
same games. Results are in `data/qb_leak_effect.json`, measured at `99eb38e`
over 1087 games, 2022-2025. Differences are leaky minus fixed, so a negative
number means the leak made the model look better than it was.

| | Model A (football only) | Model B (with the betting line) |
|---|---|---|
| Picks that change side | 3 | 1 |
| Largest change to one game's probability | 0.9 points | 0.4 points |
| Brier difference, 95% interval | -0.000080 [-0.000191, +0.000035] | +0.000012 [-0.000018, +0.000043] |
| Log loss difference, 95% interval | -0.000158 [-0.000405, +0.000098] | +0.000030 [-0.000039, +0.000100] |

**How far these figures travel.** The script has been run three times. This
table came from Windows, Python 3.11.9, with the library versions recorded in
the JSON's `provenance`. Booth re-ran it twice on Linux while auditing #96.
[The second re-run](https://github.com/lifeisgreat07/NFL-Model-2/pull/96#issuecomment-5818270878)
matched this table in every figure it shows.
[The first](https://github.com/lifeisgreat07/NFL-Model-2/pull/96#issuecomment-5817859494)
had one fewer pick changing side for each model and different last digits in
every score. Why is not known: that run came before the script recorded its
environment, so nothing says what was different about it. The verdict held in
all three runs. Read the pick counts and last digits as this run's, and the
verdict as the result.

Every interval includes zero. The leak nudged Model A's scores slightly in its
own favour and Model B's slightly against, and neither nudge can be told apart
from noise at this sample size. Accuracy is left out of the table on purpose:
a few games changing side out of 1087 is the size of move that already
separates two runs of the same code.

That is a reasonable result, and it does not make the fix unimportant. The
backtest's claim is that every prediction used only what was known at the
time. With the leak it was false, whatever it did to the numbers. The fix
restored the claim, and the measurement shows that on today's model the leak
does not measurably move the scores.

## What changed because of it

- The test that caught it is still in the suite:
  `test_qb_rating_cutoff_excludes_current_week` in `tests/test_leak_free.py`.
- `src/tune_qb_shrink_k.py` stayed committed, so the tuning can be re-run
  instead of trusted.
- Two days later `VERIFICATION.md` was committed (`ea965a6`), stating the rule
  that the suite not running was the clearest example of: a test file
  existing is not evidence it works. Existence and passing are separate claims.

## Lessons

1. **Test the property the code claims, by trying to break it.** "Leak-free"
   was in the docstring. Only a test that changed the future and watched for
   movement could check it.
2. **Run the safety net before trusting it.** The suite that had never run was
   more dangerous than having none, because it was in the place a reviewer
   looks for protection.
3. **Re-check an old result when what it was measured against changes.** The
   8-to-96 retune was reasonable when it was made. What went wrong is that
   nothing made anyone look at it again after the model changed under it.
4. **Measure the size of a fix separately from the fix.** "Small" stayed on
   the page for weeks with nothing behind it. It turned out to be true, but
   until it was measured it was a guess written as if it were a finding.
