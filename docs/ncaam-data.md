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

No paid source is used. hoopR's men's college data (the sportsdataverse) is the checked fallback (section 4).

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

## 4. The checked fallback: hoopR (read 2026-11-15, from a home connection)

hoopR's men's college schedule file (`raw.githubusercontent.com/sportsdataverse/hoopR-mbb-data`, one parquet file a
season, named by the year the season ends) was compared with the stored history by ESPN event id:

- ten of the twelve seasons have every stored final in hoopR's file; 2015-16 has 5,893 of 5,951 (99.0%) and
  2016-17 5,960 of 5,966;
- wherever a game is in both, both scores are equal except three games of 2021-22 (one or two points apart, the
  same winner);
- every NCAA tournament game is in hoopR's file except two of 2017's First Four (400946453 and 400946444);
- hoopR gives LIU Brooklyn a different team id (112358) from the stored history's 6446, and seven other clubs
  likewise in one to three games each, so the check compares event ids and scores, not club ids.

The probe's scripts are in the session archive; the registered check itself is written with the backtest.

hoopR mirrors ESPN: this guards against a dropped or garbled game, not against ESPN itself. Not yet known: whether
the file can be read from a GitHub runner.

## 5. A market archive: ESPN's odds feed (read 2026-11-15)

`sports.core.api.espn.com/v2/sports/basketball/leagues/mens-college-basketball/events/<id>/competitions/<id>/odds`
lists providers for all 736 tournament games of 2015 to 2026. Only which providers are listed and whether each
carries a two-way moneyline was read; no price was set against a result.

- 37 provider names. Three are live feeds (their names say so). Seven are models or aggregates, not books:
  teamrankings, numberfire, accuscore, consensus, Opening, Fantasy911.com and Sportradar Internal Odds(ISE). The
  other 27 are books; the registration lists both sets.
- Under the registered rule (books only, an implied sum of 1.00 to 1.20) every game of the 2021 to 2026 tournaments
  has a price, as have 315 of the 335 games of 2015 to 2019 (51 of 67 in 2015, 63 of 67 in 2018).
- A closing price exists from the 2023 tournament (63 of its 67 games, then every game); before it, only the listed
  price. The 2025 and 2026 tournaments list one book for most games. 29 book prices of the 2021 tournament have an
  implied sum outside 1.00 to 1.20 and are not used; each of its games keeps at least three books.

The feed was then read once for the 2021 to 2026 tournaments (`python -m src.sports.ncaam.market 2020 2025`,
2026-11-16) and stored as read, every provider included, in `data/ncaam/history/market_<season>.csv`. The
registration's rules are applied when a file is read, so every one of the 401 games has a market.

## 6. Not known yet

- Whether hoopR's file and ESPN's odds feed can be read from a runner.
- When ESPN's tournament board shows the new bracket's seeds on Selection Sunday, before any game: the live bracket
  needs them then.
- Whether a game the board lists before it is played carries both clubs' seeds (`curatedRank`) as a played one
  does, and how it lists the side a First Four game will fill. The lock (`python -m src.sports.ncaam.bracket lock`)
  reads the field from the First Four's and the first round's boards on that assumption, leaving out a side whose
  club id is not a number; it is to be dry-run on the boards the Sunday the bracket is out, before the lock.
- Which regions meet in the Final Four: the scoreboard does not say before those games, so the lock is given them.
