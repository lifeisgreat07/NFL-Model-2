"""The files MLB's pages read that are not the schedule or the standings (Stage 100 item 2).

`ratings_json` is the Power Ratings page's file, `results/mlb/ratings_<season>.json`. MLB's daily run (Stage 101)
writes it from the ratings it fits for the day's picks, as the NHL's daily run writes its own
(`src/sports/nhl/page_inputs.py`); it is defined here, beside the page, so the page reads a shape that exists.

- `clubs`: each club's run rating, `src/sports/mlb/ratings.py`'s ridge fit, best first: how many runs a game
  better than an average club.
- `starters`: every pitcher with at least `MIN_STARTS` starts this season, by his rate (runs allowed per 27 outs,
  recency-weighted and shrunk toward the league by `K_outs`), best first, with his club (that of his latest start),
  his starts and the outs his rate weighs. A pitcher with fewer starts is still rated in the picks; he is left off
  the page because a list of 400 arms is not a ranking anyone reads.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from src.sports.mlb import ratings

MIN_STARTS = 3


def ratings_json(rated: ratings.DayRatings, k: float, starts: Iterable[tuple[str, str, str]],
                 outs: Mapping[str, float], names: Mapping[str, str], as_of: str) -> dict[str, Any]:
    """`starts` is this season's (pitcher, club, day) for every final game's two starters before `as_of`;
    `outs` each pitcher's weighted outs; `names` the Stats API's names by person id."""
    latest: dict[str, tuple[str, str]] = {}
    count: dict[str, int] = {}
    for pitcher, club, day in starts:
        p = str(pitcher)
        count[p] = count.get(p, 0) + 1
        if p not in latest or day >= latest[p][0]:
            latest[p] = (day, str(club))
    clubs = [{'team': c, 'runs': round(r, 4)} for c, r in sorted(rated.runs.items(), key=lambda cr: (-cr[1], cr[0]))]
    listed = sorted((p for p, n in count.items() if n >= MIN_STARTS), key=lambda p: (rated.starter(p), p))
    starters = [{'player_id': p, 'name': names.get(p), 'club': latest[p][1], 'starts': count[p],
                 'rate': round(rated.starter(p), 4), 'outs': round(float(outs.get(p, 0.0)), 1)} for p in listed]
    return {'as_of': as_of, 'league_rate': round(rated.league_rate, 4), 'K_outs': k, 'min_starts': MIN_STARTS,
            'clubs': clubs, 'starters': starters}
