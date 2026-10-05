# NHL data: what exists, and the go/no-go (Stage 51)

Read-only checks from the local Windows machine on 2026-10-05, saved with
their scripts in the session archive (`nhl_probe.py` to `nhl_probe4.py`). The same reads from GitHub's own runners are item 1's
probe workflow, still to run; until it has run, every "works" below means
"works from a home connection", which the NBA's stats site has shown is not
the same thing.

## Verdict: GO, Model A and Model B

Schedule, results, play-by-play, starting goalies (after the fact), team
identity and a live market all come from the league's own public API, with
no key. History goes back further than the NFL's. Model A can be built on
it alone. The league's odds feed is live only, but **ESPN's public API holds
moneylines for every NHL game from 2020-21**, which gives Model B the NFL's
split at no cost (section 3). Mark ruled out paid data on 2026-10-05.

## 1. Schedule, results, play-by-play: `api-web.nhle.com/v1`

| What | Endpoint | Checked |
|---|---|---|
| A week's schedule | `/schedule/<date>` | 2026-10-06 to 10-12: 9, 3, 10, 4, 14, 3, 3 games |
| A team's season | `/club-schedule-season/<team>/<season>` | Toronto: 82 games every full season 2005-06 to 2025-26; 48 (2012-13 lockout), 70 (2019-20), 56 (2020-21), 84 in 2026-27 |
| Play-by-play | `/gamecenter/<id>/play-by-play` | One mid-season Toronto game per season, 2005-06 to 2025-26 |
| Box score | `/gamecenter/<id>/boxscore` | Goalies with a `starter` flag and time on ice |
| Outcome | schedule `gameOutcome.lastPeriodType` | `REG`, `OT`, `SO` |

**History depth.** Shot coordinates start in **2009-10**: 0 of 57 to 88
shots carry x/y from 2005-06 to 2008-09, and every shot carries them from
2009-10 on. Before that the play-by-play has the goalie in net but no
location. So shot-quality features can use 2009-10 onward, which is 16 full
seasons before this one. That is more than the NFL model's six training
seasons.

**Start times are UTC** (`startTimeUTC`), with the venue's time zone beside
them. That is cleaner than the NFL's Eastern-time strings, and it fits the
interface's `start_utc` as it is.

**States.** `gameState` takes `FUT`, `LIVE`, `OFF` and `FINAL`, and
`gameScheduleState` takes `OK` (seen) plus a postponed or cancelled value
(not seen in 2020-22 for four teams; to confirm on a real postponement).
Stage 55 maps these onto `GameStatus`, and a test pins the mapping.

## 2. Fallback: SportsDataverse `fastRhockey-nhl-data`

Updated 2026-10-05 08:04 UTC. Parquet files in the repository itself, not
in releases: `nhl/pbp/`, `nhl/schedules/`, `nhl/goalie_box/`, `nhl/team_box/`,
`nhl/rosters/` and more. The fallback is **not yet checked** the way
`nfl_data_py` was (both loaders agreeing exactly on one week). That check is
Stage 55 item 1, and until it has run the fallback is a candidate, not a
verified revert path.

## 3. The market (Model B)

**Live: the league's own feed.** `/partner-game/US/now` (DraftKings) and
`/partner-game/CA/now` (FanDuel) return today's games with a two-way
moneyline, a three-way moneyline, the puck line and the total. It is only
"now": a past date returns 404. So the feed is a live source, and the
pipeline has to record it itself (as `data/line_history/` does for the NFL)
to build any history.

**Historical: ESPN's public API** (free, no key). On 2026-10-05 Mark ruled
out paid data and chose the Kaggle datasets; the one with betting lines
names ESPN's public API as its source, so the source itself is used and
Kaggle kept as the last resort:
`sports.core.api.espn.com/v2/sports/hockey/leagues/nhl/events/<id>/competitions/<id>/odds`.
Sampled one date per season:

| Season | Games with a moneyline | Lines | Sportsbook |
|---|---|---|---|
| 2012-13, 2015-16, 2018-19 | 0 of 8, 11, 10 | none | |
| 2020-21 (2021-02-15) | 10 of 11 | one line per game | Bet365 |
| 2021-22, 2022-23 | 3 of 3, 12 of 12 | one line per game | Bet365 |
| 2023-24 | 6 of 6 | open and close | Bet365 |
| 2024-25 | 5 of 5 | open and close | ESPN BET |
| 2025-26, 2026-27 | 5 of 5, 6 of 6, 5 of 5 | open and close | DraftKings |

**Checked over every game, 2026-10-05** (scripts and output in the session
archive: `nhl_market_collect.py`, `nhl_market_check.py`,
`nhl_market_conversion.py`). Stage 56 re-derives these figures inside the
repository, with a test tying each to its file, before any is published.

*Coverage.* A moneyline for 867 of 868 completed regular-season games in
2020-21, 1311 of 1314 in 2021-22, 1312 of 1315 in 2022-23, 1314 of 1315 in
2023-24, 1319 of 1319 in 2024-25 and 1312 of 1312 in 2025-26.

*It is two different markets.* Through 2023-24 (Bet365, briefly Betfair)
ESPN's line is the **three-way regulation market** (home, away, draw after
60 minutes). The two sides' implied probabilities sum to a median of 0.83,
the draw being the missing share. From 2024-25 (ESPN BET, then DraftKings)
it is the **two-way moneyline**, overtime included, at a median overround
of 4%. The league's live feed carries both.

*Accuracy, against the free archive's two-way close.* A two-way probability
is fitted from the three-way one on 2020-21 and 2021-22, on the logit scale
(intercept 0.003, slope 0.824). Then it is tested on the archive's last
season, 2022-23 (319 games to November 27, where the archive stops). There it
is a median 1.1 points from the archive's closing probability, 3.0 at the
95th percentile, and scores the same log loss (0.6677 against the archive's
0.6686). The favourite is the same in all but 3 to 4% of games, which are
close calls. 2024-25 onward has no free independent archive to check
against. There, the checks are internal: the close equals the reported line
in 1281 of 1319 and 1261 of 1312 games, and the overround is a sane 4%.

*Usefulness, as a forecast of who wins.* The market's log loss against the
home-win base rate (lower is better): 0.652 vs 0.691 (2020-21), 0.640 vs
0.691, 0.652 vs 0.692, 0.656 vs 0.690, 0.658 vs 0.686, and 0.682 vs 0.692 in
2025-26. That last season is close to a coin flip for the market too: not
swapped sides (swapping makes it 0.74), but a season of unusual parity. Every
season beats the base rate, by less than the NFL's market does. Hockey is the
less predictable sport.

**Decision (Claude, under Mark's delegation, 2026-10-05).** Model B's
market input is the two-way home-win probability: native from 2024-25,
converted from the three-way line before that by the fit above. Validation
2022-23 and 2023-24 (converted), held-out 2024-25 and 2025-26 (native), as
for the NFL. The registration states that training and held-out seasons
come from different instruments, and the drift check treats the 2024-25
switch as a known break. The free archive (2007-08 to November 2022) stays
the checked reference. The Kaggle sets that cite ESPN are not needed.

## 4. Starting goalies and injuries

- **After the fact:** every box score flags exactly one starting goalie per
  team: 40 of 40 team-games in each of 2007, 2010, 2015, 2020 and 2024 (20
  Boston games each). So the backtest can use the actual starter, as the NFL
  backtest uses the actual quarterback.
- **Before the game:** the league publishes no projected starter. Daily
  Faceoff's starting-goalie page labels each goalie `Confirmed` or `Likely`
  and carries machine-readable data in the page (`homeGoalieName`,
  `homeNewsStrengthName`). This is the NHL's version of the QB override, and
  it carries the same gap the NFL has: the backtest knows the starter, the
  live pick only knows the projection. The goalie routine (Stage 58 item 3)
  reads it on game mornings and opens a PR. Fallback: the last game's
  starter, with a note, exactly as the NFL does.
- **Injuries:** SportsDataverse's `espn_nhl_injuries` release
  (`injuries_2027.parquet`, updated 2026-10-04). Context only, as the NFL's
  injury data turned out to be.

## 5. Team identity across seasons

The league's stats API keeps franchises (40) apart from team names (62):

- Atlanta Thrashers (ATL) and Winnipeg Jets (WPG): franchise 35 (moved 2011).
- Phoenix Coyotes (PHX) and Arizona Coyotes (ARI): franchise 28 (renamed 2014).
- **Utah (UTA) is franchise 40, not 28.** The league treats Utah as a new
  franchise, although Arizona's roster moved there in 2024. Whether team
  strength carries from ARI to UTA is a modelling decision. It goes in the
  Stage 56 registration, not here.
- Vegas (VGK) from 2017-18, Seattle (SEA) from 2021-22: no history before
  their first season.

Standings at each April 1 show 30 teams in 2010-11, 31 from 2017-18, 32
from 2021-22.

## Still to do in Stage 51

1. The probe workflow: the same reads from GitHub's runners (`.github/workflows/nhl-data-probe.yml` and `src/sports/nhl/data_probe.py`, read-only).
2. A postponed or cancelled game's `gameScheduleState`, read from a real one.
