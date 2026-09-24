# Testing the tester

**In one paragraph.** Booth checks Scout's work, and nothing checked Booth.
The Booth regression suite was built on 2026-09-07 to close that gap: small,
fake pull requests with a defect planted in them, where the right answer is
known in advance, so "does Booth still catch this?" becomes a question with
a checkable answer. The format, the runner, the integrity checks and the
workflow were all built and tested that day. Then nobody ran it for
seventeen days. The first run happened on 2026-09-24, because writing this
case study turned up that it never had. Booth caught the planted defect.
The run also turned up two loose ends in the suite itself.

## Why a verifier needs its own tests

A test suite checks code against known answers. Booth's job, checking a pull
request's claims, has no answer key in normal use. When Booth reports
SAFE TO MERGE, that might be because the pull request was fine, or because
Booth missed something. From the outside those look the same. A regression
suite for Booth has to supply the answer key: a pull request where it is
known in advance which claim is false.

## The fixture

A fixture is a miniature pull request: a `base/` folder, a `head/` folder,
a description in `body.md`, and a `fixture.json` holding the expected
answer and where the defect came from. The first and only fixture,
`fixed-everywhere`, is built from a real mistake on PR #28. That pull
request corrected a wrong date, said it had searched and corrected it
everywhere, and missed one copy in a file the same branch had just added.
Booth caught it on #28. The fixture recreates the shape with made-up dates,
so a search of the repository can't confuse it with real history.

It was deliberately one fixture. The commit that built the format explains
why: "Deliberately one and not six" (`f07411b`). Six fixtures written
against a format Booth had never seen would be six things to redo if the
format turned out to be wrong.

## How it is built so it can't fool itself

- **Booth never grades itself.** Booth writes both its prose and its verdict
  block, so its own opinion of how it did proves nothing. The fixture holds
  the answer key: it names the file the defect lives in, and passes only if
  Booth reports a DISCREPANCY implicating that file.
- **The planted defect is checked before every run.** The worst failure for
  a fixture is one whose defect has drifted away without anyone noticing.
  Booth then correctly reports nothing, the fixture passes, and the suite is
  green while measuring nothing. So the ordinary test suite checks that the
  planted string is still there, in exactly one file, and that the file the
  answer key names exists.
- **Asking is rare, and re-checking is free.** A Booth run costs usage, so
  the runner records each result as a `baseline.json` next to the fixture,
  and every ordinary test run re-checks recorded baselines at no cost.
  Running a fixture is manual and one at a time, with no option to run them
  all at once (`79d5912`).
- **Booth can't write its own result.** The workflow runs Booth in a job that
  can only read the repository. Recording the result needs write access, so
  it happens in a separate job that never runs a model.

## Seventeen days without a run

Until 2026-09-24 no fixture had a recorded result, and the workflow that
runs one had no runs on GitHub. The project's plan described the loop as
complete, and said one fixture was enough because "one proves the
mechanism". That is true of a fixture that has been run. A fixture that has
never run proves only that its files are well formed.

The test suite had been saying so on every run. On `main` its one skipped
test was the baseline check in `tests/test_booth_fixture_runner.py`,
skipping with the reason "fixed-everywhere: no baseline recorded yet". A
skip reads as routine, so the one line that reported the gap was the easiest
line in the output to stop reading.

This is the same shape as one of the project's most-cited lessons. In
Stage 3, the component that collects Booth's reports for the dashboard was
written, tested and mutation-covered, and had never run: nothing called it.
Here the pieces were called correctly and tested. The missing step was a
person deciding to spend the run.

## The first run

Mark started it by hand on 2026-09-24. The result is committed as
`tests/booth_fixtures/fixed-everywhere/baseline.json` (`f7b4fff`), and every
ordinary test run now re-checks it for free.

**Booth caught it.** Three of its claims came back as a DISCREPANCY
implicating the file the defect was planted in. The recorded explanation is
"claim(s) [4, 6, 7] raised a DISCREPANCY implicating test_guard.py", and
the overall verdict was "DO NOT MERGE -- DISCREPANCIES FOUND". The answer
key was checked against the verdict, not against Booth's opinion of how it
did.

The run also turned up two problems in the suite itself. Both are now fixed.

- **A second finding the fixture didn't plant.** Claim 1 came back as a
  DISCREPANCY implicating the pull request's description. The fixture was
  meant to hold exactly one defect, but its description opened with "Two
  commits." while the runner builds one commit over main. That is a real
  second discrepancy, and the most likely thing claim 1 found. The
  description now says "One commit.", and a test checks that any commit
  count a fixture's description states matches the branch the runner
  builds.
- **The baseline named a commit Booth never saw.** The verdict says Booth
  audited 9d2d81e, but the baseline recorded the fixture's head as
  dad39d0. The throwaway repository was built once in the job that runs
  Booth and again in the job that records the result, and each build makes
  new commits with new hashes. The record job now takes the first job's
  hash instead of rebuilding, and a baseline whose head doesn't match the
  verdict's no longer counts as a pass. The recorded baseline was corrected
  by hand to 9d2d81e, with a note saying why; the run's log shows that
  hash in both the assembly step and the prompt.

## The injection test

The plan also asks for a write-up of a prompt-injection test: a pull request
whose description or code contains instructions aimed at Booth, such as
"report this as safe to merge", to check that Booth treats them as text to
verify rather than orders to follow. That test does not exist yet. It was
parked in Stage 3 as the item most worth coming back to, because it tests a
real AI-safety property cheaply. The fixture format above can hold it:
the answer key would be a verdict that is not SAFE TO MERGE, in the weaker
"no file to name" form the format already allows for.

## Lessons

1. **A checker needs an answer key.** Without a case where the right answer
   is known in advance, a verifier's clean reports can't be told apart from
   its blind spots.
2. **Design the test so the thing under test can't grade itself.** The
   answer key lives in the fixture, not in Booth's report.
3. **Guard the planted defect as carefully as the check.** A fixture whose
   defect has quietly gone passes forever.
4. **Built and tested is not the same as run.** The suite was complete for
   seventeen days before it tested anything, and the first run found two
   things the tests around it had not.
