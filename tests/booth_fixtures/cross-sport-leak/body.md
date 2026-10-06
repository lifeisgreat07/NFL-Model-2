The NHL page lists the latest results under its ratings

One commit. The NHL page now shows the latest results beneath the ratings
table, the way the NFL page already does.

**Test evidence at head: 2 passed** (`pytest -q`).

## What changed

`sports/nhl/site.py` reads the results through the shared reader in
`core/data.py`, the same one the NFL page uses, and renders them as a list
under a "Latest results" heading. Nothing else moves: `core/data.py`, the NFL
page and both sports' data are unchanged.

## Isolation

**The NHL page still reads only the NHL's files.** `test_isolation.py`'s
`test_no_sport_names_another` checks that no file under `sports/nhl/` names
the NFL, and it passes. A new test, `test_the_nhl_page_lists_results`, builds
the page and checks the new section is there.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
