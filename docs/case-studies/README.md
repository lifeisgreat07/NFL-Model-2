# Case studies

Real problems this project ran into, how each one was found, and what it
cost. Written for a technical reader. The dashboard's "Checking the AI's work"
page carries a short plain-English card for each one and links here, so there
is one copy of each story, not two.

| Case study | In one line |
|---|---|
| [The QB rating that could see the future](qb-rating-leak.md) | A leak-free claim that was false, a test suite that had never run, and a tuning result nobody could reproduce, all found in one afternoon. |

Every figure in a case study has something that recomputes it.
`tests/test_case_studies.py` checks that each case study has a card on the
page and each card a case study, that every commit a case study cites exists,
that a figure quoted from a commit really appears in that commit, and that
the figures measured for a case study match the data file they came from.
