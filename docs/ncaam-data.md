# Men's college basketball data: what exists (Stage 103)

What the March Madness bracket (Stage 103) can be built from, measured before any NCAAM model, rating or registration
exists. Read from a home connection on 2026-11-13; the collector (#726) reads the same scoreboard from GitHub's
runners every day.

## 1. Source

ESPN's men's college scoreboard, `site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard`,
one day at a time, from two boards:

- `groups=50`, Division I: every game between two Division I clubs, about 5,900 to 6,300 finals a season.
- `groups=100`, the NCAA tournament: its games. The Division I board left two of 2017's First Four games out (Mount
  St. Mary's v New Orleans and Kansas State v Wake Forest, 14 March 2017); the tournament board has them. The
  collector reads both and keeps each game once.

No paid source is used. hoopR's men's college data (the sportsdataverse) is the candidate checked fallback, as the
stage says; it is not read yet.

## 2. History depth

`python -m src.sports.ncaam.collector --from <day> --to <day>`, season by season from 1 November to 10 April:

| Season | Finals | NCAA tournament games |
|---|---|---|
| 2014-15 | 5,932 | 67 |
| 2015-16 | 5,951 | 67 |
| 2016-17 | 5,966 | 67 |
| 2017-18 | 6,003 | 67 |
| 2018-19 | 6,049 | 67 |
| 2019-20 | 5,767 | 0 |
| 2020-21 | 4,285 | 66 |
| 2021-22 | 5,976 | 67 |
| 2022-23 | 6,228 | 67 |
| 2023-24 | 6,243 | 67 |
| 2024-25 | 6,292 | 67 |
| 2025-26 | 6,300 | 67 |

2019-20 stops on 11 March 2020 and has no tournament. 2020-21 is short (late start, many games cancelled) and its
tournament has 66 games: VCU v Oregon was declared a no-contest. `season` is the year a season starts.

## 3. Seeds

ESPN's scoreboard has no seed field, but in an NCAA tournament game (`tournamentId` 22) each club's
`curatedRank.current` is its seed. Checked for every tournament game of 2015 to 2026 by
`python -m src.sports.ncaam.seeds 2014 2025`, which writes `seeds_<season>.csv` and stops on any failure:

- every seed is 1 to 16;
- every round-of-64 pair adds up to 17, and a finished tournament names exactly 32 such games (31 in 2021). The
  round of 64 was called the "2nd Round" until 2015 and the "1st Round" from 2016;
- every club has one seed across all its games.

All 736 tournament games of 2015 to 2026 pass. One side was filled: in a First Four game, which pairs two equal seeds, ESPN leaves LIU Brooklyn unranked (99), so it takes its opponent's 16 (401025856 (2018); `filled` names the side).

## 4. Not known yet

- Whether hoopR's college data can be read from a runner, and how well it agrees with ESPN (the checked fallback).
- A free archive of past tournament moneylines, for a market comparison.
- When ESPN's tournament board shows the new bracket's seeds on Selection Sunday, before any game: the live bracket
  needs them then.
