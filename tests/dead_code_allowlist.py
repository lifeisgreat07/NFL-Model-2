"""Names vulture reports as unused that are kept on purpose (Stage 48 item
18, tests/test_dead_code.py).

Vulture finds unused code by name, so each name here counts as used
wherever it appears. Every entry says why it stays; an entry with no reason
is dead code with an excuse. This file is read by vulture, never imported.
"""
_ = None  # vulture's whitelist idiom: attribute uses of a stand-in object

# logging.Handler calls handleError itself (src/core/runlog.py).
_.handleError

# A read_text override must take the encoding argument its callers pass
# (src/core/template_parts.py), even though it reads a joined string.
_.encoding

# The five Model Lab decisions, the project's own vocabulary written down
# where the Model Lab is built (src/sports/nfl/model_lab.py); the page's
# LAB_DECISIONS mirrors it.
_.DECISIONS

# Former NHL abbreviations, the same franchise in the league's own records
# (src/sports/nhl/teams.py); data for the history reader, kept with the teams.
_.FORMER
