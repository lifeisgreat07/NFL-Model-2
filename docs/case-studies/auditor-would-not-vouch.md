# When the auditor would not vouch

On the night of 2026-11-04 to 2026-11-05 the building agent merged pull
requests one at a time under a fixed rule. Booth, the checking agent, had to
say SAFE TO MERGE with no discrepancy, about the commit that was the pull
request's head, with every other check green. Three times Booth did not say
SAFE, and nothing it found was wrong. Each time it was saying that a claim
could not be checked, or could not be checked by Booth. This is what each one
was and what was done about it.

## A total it could not reproduce (#619)

The description of #619 (Stage 92 item 9, head `abf592a4`) said the full
suite passed on Windows: 12104 tests. Booth confirmed four of the five
claims. For the fifth it ran the suite on its Linux runner, leaving out
`tests/test_mutation_corpus.py`, the corpus file whose seven thousand
per-case checks take most of the time, and got 4777 passed. A filter it tried
on the corpus file selected nothing, so it could not show that the rest made
up 12104. It marked the total UNVERIFIABLE, found no discrepancy, and
returned NEEDS HUMAN REVIEW.

The rule did not allow a merge, and asking Booth again for a different answer
would have been shopping for a verdict. What changed was the claim. The
description gained one line: of the 12104, the corpus file collects 7327 and
the rest of the suite 4777, each from `pytest --co`, which takes seconds. The
edit started a new audit. Booth counted the collection, confirmed all six
claims, and returned SAFE TO MERGE. Every description since carries that line.

## Its own workflow (#582)

#582 changed `.github/workflows/booth-pr-audit.yml`, the workflow Booth
itself runs in. Booth returned NEEDS HUMAN REVIEW. An auditor that approves
the rules it is audited under is not independent of them, whatever the
change, so the pull request stays open for a person. The same reasoning
shaped another change that night. Moving every workflow's install onto a
lock file with hashes (Stage 88 item 3) left Booth's own install out, for a
pull request of its own that a person reviews.

## A report that disagreed with itself (#611)

`src/agents/booth_report_posted.py` fails the audit job when a report's
counts in prose differ from its machine-readable verdict block. On #611 it
did that twice. The description had paragraphs that made no claim ("what
the tests cannot show", a process note), and the two halves of Booth's report
came out with different counts. The paragraphs left the description, Booth's
next report agreed with itself, and it said SAFE TO MERGE.

## What it taught

"Could not check" is a finding, not noise. Each time, the remedy was to make
the claim checkable by someone who starts cold, or to send the decision to a
person, never to ask the same question until the answer changed.
