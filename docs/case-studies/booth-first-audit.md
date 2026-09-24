# The verifier's first week

**In one paragraph.** Booth is this project's second agent. It doesn't write
code. It re-runs what the first agent, Scout, claims in a pull request and
reports which claims hold. Its first attempt, on 2026-09-05, posted nothing:
it ran out of turns mid-audit. Its first real report, on PR #18, found a
flaw nobody had asked it to look for: the workflow Booth ran in was itself
breaking the project's reproducibility rule. It also refused to confirm a
"confirmed finding" on the live dashboard that had no script and no data
behind it. The finding survived when
it was rebuilt from scratch. The pattern it exposed, a number nobody can
re-run, is what Booth has been catching ever since.

## What Booth is

Scout does the work: research, code, the pull request and its description.
A description is a list of claims: "the suite passes", "this number came from
that file", "this commit does only this". Booth is a GitHub Action that starts
on every pull request with no memory of how the work was done. It re-executes
each claim and posts a report marking every claim CONFIRMED, DISCREPANCY or
UNVERIFIABLE. It doesn't read the description and agree with it. It runs the
commands.

## The run that posted nothing

The first workflow capped Booth at 30 turns. The first run reached 30 turns
in 3m47s, against a 20-minute timeout, and was killed mid-audit with nothing
posted (`2617375`). The cap had been picked for cost before anyone knew what an
audit costs, and it was strangling the feature. It went to 120, and the
prompt gained an instruction to post a partial report rather than none.

That failure came back twice more in other forms. On 2026-09-21 a run showed
green in Actions and posted nothing, and on 2026-09-22 the workflow was taught
to fail any run that posts no report (`d00f96a`). On 2026-09-23 two audits of
#94 ended early with nothing posted. The likeliest reading of the log was
that Booth had stopped to wait for a background job, and in this setup a
stopped agent is a finished one. #95 told it so, and the first audit after
#95 posted its report. **A verifier that can fail silently needs
its own check that it produced anything**, and this one needed three.

## The first report

PR #18 added a "track record at this confidence" line to each game card on
the Week Board. Booth's report confirmed most of it, with a few things worth
noticing:

- **It verified the substance when it couldn't verify the method.** The PR
  said a headless browser had checked every card on that week's board.
  Booth had no browser. So it pulled the shipped JavaScript functions out of
  the built page, ran them under Node against the week's real games, and
  recomputed every card from `data/calibration.json`. None disagreed. It
  marked the browser claim itself UNVERIFIABLE and said why.
- **It found a flaw in its own harness.** The Booth workflow installed only
  `requirements.txt`, which has never contained pytest. So every audit began
  by installing whatever pytest was current, and nothing recorded which
  version checked which pull request (`40feabc`). That is the project's
  reproducibility rule broken inside the tool that exists to enforce it. The
  harness now pins its own test dependencies in `requirements-dev.txt`.
- **It refused to confirm a number it couldn't reproduce.** The PR's
  motivation quoted a CONFIRMED FINDING from Model Lab: when Model A's
  probability is near a coin flip, it is right far less often than the
  betting market. Booth looked for the script or data file behind the
  figures and found none, so it marked the claim UNVERIFIABLE, not
  CONFIRMED. It also noted that the claim didn't affect the new code.

## What happened to the finding

A search of the repository found those numbers in exactly two places: the
dashboard template and the page built from it (`639e09a`). No script
produced them. The band they described wasn't one of the calibration file's
bins, so they couldn't even be read off an existing file. A CONFIRMED FINDING
on the live page had nothing behind it.

The next PR, #19, rebuilt it from scratch as a committed script,
`src/verify_low_confidence_finding.py`. It holds:

| | Published | Re-derived |
|---|---|---|
| Model A accuracy | 52.50 | 52.48 |
| Market accuracy | 64.40 | 64.14 |
| Gap | -11.95 | -11.66 |
| 95% interval | [-18.37, -5.53] | [-18.37, -5.25] |

The direction, the size and the interval excluding zero all survived. The
page now shows the re-derived figures, names the script that produces them,
and keeps the old figures in the Model Lab row as history.

Surviving was luck. The QB shrinkage retune of 2026-08-24 had been carried
the same way, a published result with nothing to re-run, and when someone
finally re-ran it, it didn't hold (see the
[QB rating leak case study](qb-rating-leak.md)). Neither had been checked
when it was published. One of them happened to be right.

## What it became

- **Scout pre-flight** (`dce655d`, the next day) checks a description against
  the repository before Booth sees it. Today it checks suite counts, whether
  every commit is mentioned, and counts quoted from a wider command than the
  sentence claims. It catches the mechanical failures so that Booth's time
  goes on substance.
- **Reports that say what they checked.** Every report now names the commit
  it audited and when it read the description (`15e0836`). Before that, a
  report about a description that had since been edited read as if it were
  about the current one.
- **A record on the page.** Every report now ends in a machine-readable verdict
  block, and "Checking the AI's work" counts them live instead of retelling
  three hand-picked incidents.
- **The same catch, on 2026-09-24.** Booth's audit of #96, the pull request
  that added the first case study, re-ran the table that case study was
  built around and couldn't reproduce its exact figures. It was right to flag
  it. The case study now says what is known about how far those numbers
  travel.

## Lessons

1. **Make the verifier re-execute, not read.** Every useful thing in that
   first report came from running something. Nothing came from judging the
   prose.
2. **UNVERIFIABLE is a result.** The most valuable line in the first report
   was a refusal to confirm. A verifier that rounds "couldn't check" up to
   "fine" is worse than none.
3. **Check the checker's own setup.** The pytest gap sat in the one workflow
   whose whole job was reproducibility, and it took an audit running into it
   to find it.
4. **A verifier that fails silently needs a check of its own.** Its first
   run posted nothing, and runs that posted nothing turned up twice more in
   the next three weeks. Closing that took three separate fixes, one of them
   a check that fails any run that ends without a report.
