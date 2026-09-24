# Lessons learned

What this project learned about building software with AI agents, taken
from what actually went wrong here. Each lesson says where it came from.
The [case studies](case-studies/README.md) tell the longer stories, and
`CLAUDE.md`'s trap list holds the full record, written for the next working
session rather than for a reader.

## Checking claims

1. **Re-run the claim; don't review the description of it.** Scout, the agent
   doing the work, sometimes states something false with full confidence:
   that a test passed, that a pull request wasn't merged, that a number came
   from a file. Asking an agent to double-check itself doesn't help, because
   the same failure can produce a confident re-confirmation. What worked
   every time was a second agent, Booth, re-executing each claim.
   *From: `VERIFICATION.md`; [The verifier's first week](case-studies/booth-first-audit.md).*

2. **"Couldn't check" is a result, not a pass.** Booth's most useful early
   line was marking a published finding UNVERIFIABLE because nothing in the
   repository produced it. A checker that rounds "couldn't check" up to
   "fine" is worse than none.
   *From: [The verifier's first week](case-studies/booth-first-audit.md).*

3. **The checker's reports are evidence, not an oracle.** Booth has put
   miscounted figures into its own reports, including in the sentence doing
   the catching. Read the numbers in a verification report the way it reads
   the numbers in a pull request.
   *From: `CLAUDE.md`, "the auditor produces untraceable figures too".*

## Numbers

4. **A figure ships with the command that produced it.** Almost every wrong
   number here came from a real command. What went wrong was the scope: a
   count from three test files quoted as one, a wide band quoted as a narrow
   one. Writing the command next to the number makes the mismatch visible
   while it is still cheap to fix.
   *From: `CLAUDE.md`, "a real number from a command whose scope is not the sentence's scope".*

5. **A number in prose needs something that recomputes it.** Numbers that
   were right when written went wrong when the code moved underneath them.
   The ones with a test tied to their source were caught within minutes.
   The ones with nothing behind them stayed wrong until someone happened to
   look.
   *From: `CLAUDE.md`, "a number that was correct when written, falsified by the base moving".*

6. **Some results don't travel between machines.** The same code and data
   can disagree by a game or two out of about 1,100 between computers, while
   proper scoring rules agree to four decimals. So accuracy can't carry a
   result here, and a published table says where it was run.
   *From: `CLAUDE.md`, "Accuracy cannot carry a result"; [The QB rating that could see the future](case-studies/qb-rating-leak.md).*

## Tests and guards

7. **Break every new guard on purpose, and check which test caught it.** A
   guard whose comment promises more than its code delivers turned up again
   and again. The fix is a committed mutation corpus: each case breaks the
   code in one known way and names the test that must catch it. A break
   caught by the wrong test still leaves the intended one untested.
   *From: `CLAUDE.md`, "a guard whose comment claims more than its code delivers"; `tests/mutation/`.*

8. **If today's data can't reach a guard's failure branch, feed it made-up
   data that can.** Guards that only ran over the real data passed while
   checking nothing, because nothing in the data could make them fail. The
   rule now runs twice: once over the real data and once over a synthetic
   case built to fail.
   *From: `CLAUDE.md`, "an allowlist that covers everything makes its own interesting branch unreachable".*

9. **Built and tested is not the same as run.** A component was written,
   tested and mutation-covered, and nothing ever called it. The Booth
   regression suite sat complete for seventeen days before it scored Booth
   once, and that first run found two problems in the suite. Both looked
   finished from inside the test suite.
   *From: [Testing the tester](case-studies/booth-regression-suite.md).*

## Failure modes

10. **Silence is the most expensive failure.** A missing file that returned
    an empty result kept a page blank until someone built on top of it. A Booth run
    that posted nothing showed a green checkmark. Every missing input should
    say something, and every job should check that it produced what it
    exists to produce.
    *From: [When the to-do list was wrong](case-studies/stage2-corrections.md); [The verifier's first week](case-studies/booth-first-audit.md).*

11. **A queued problem is a guess.** On one early to-do list, one item
    described its problem wrongly and another was built on a page that had
    never worked. Acting on the first would have deleted a working feature. Check the "so" in a finding, the reason attached to the
    observation, before doing the work it implies.
    *From: [When the to-do list was wrong](case-studies/stage2-corrections.md).*

12. **Render it and look at it.** Several interface bugs were invisible in
    the code and obvious on screen. A missing webfont can do more than shift
    a measurement: one layout bug disappeared entirely in the narrower
    fallback font.
    *From: `CLAUDE.md`, "Render it and look at it" and "a missing webfont does not shift a measurement".*

## Method

13. **State the question before looking at the data.** The model
    experiments were written down, with the rule that would decide each one,
    before any answers came in. None of the ten was accepted, and a result
    like that is only believable when the questions came first.
    *From: `experiments/stage5/registry.json`; `CLAUDE.md`, "Stage 5 accepted nothing".*
