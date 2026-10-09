"""Names vulture reports as unused that are kept on purpose (Stage 48 item
18, tests/test_dead_code.py).

Vulture finds unused code by name, so each name here counts as used
wherever it appears. Every entry says why it stays; an entry with no reason
is dead code with an excuse. This file is read by vulture, never imported.
"""
_ = None  # vulture's whitelist idiom: attribute uses of a stand-in object

# The multi-sport contract (src/core/sport.py, Stage 50). These are the
# fields and methods every sport module must provide; the NHL and NBA fill
# them, and the NFL will when Stage 52 moves it behind the interface. A
# Protocol's members are read by whoever implements it, not by the core.
_.former
_.ties_possible
_.overtime
_.points_win
_.points_ot_loss
_.points_tie
_.regular_season_games
_.teams_in_playoffs
_.slate_label
_.key_player_role
_.team_colours
_.SportModule
_.display
_.lock_rule
_.scheduled_runs_utc
_.key_players

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
