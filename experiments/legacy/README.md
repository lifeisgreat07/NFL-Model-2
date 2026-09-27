# The Model Lab's rows from before Stage 18

`rows.json` holds the 46 rows the Model Lab page carried before Stage 18, moved
here once, on 2026-09-27, from the table in `src/dashboard_template.html`. The
experiment, result and label fields are the page's own HTML, character for
character. They predate pre-registration and have no result files of their own,
so this is the record for them.

Two fields are new. `decision` maps each label onto the project's five
decisions (ACCEPT, REJECT, INCONCLUSIVE, DEFERRED, CONFIRMED FINDING). `leakage`
marks the one result that was invalidated by leakage. The label a row was first
given stays beside its decision, so the mapping can be checked:

| label on the page | decision | why |
|---|---|---|
| REMOVED (was live) | REJECT | accepted once, then beaten by leaving the feature out |
| LEAKAGE -- INVALIDATED | DEFERRED, with the leakage flag | the result is void, and a clean test waits on data that does not exist yet |
| DIAGNOSED | INCONCLUSIVE | an accuracy gap on 25 games, with no interval |
| NO PATTERN | INCONCLUSIVE | no interval was computed |
| NOT A NEW FINDING | INCONCLUSIVE | no interval was computed |
| REJECT — NO ATS EDGE | REJECT | the interval contains 50% and misses break-even |

Nothing new is added here. From Stage 5 on, every answer is a file in
`experiments/<stage>/results/`, and `src/model_lab.py` reads those directly.
`tests/test_model_lab.py` checks the move and the mapping.
