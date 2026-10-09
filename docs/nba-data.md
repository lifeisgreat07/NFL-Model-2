# NBA data: what exists, and the go/no-go (Stage 61, the NBA's Stage 51)

Read-only checks from the local Windows machine on 2026-10-05, saved with
their scripts in the session archive (`nba_probe0.py` to `nba_probe2.py`,
`nba_market_collect.py`, `nba_market_check.py`). The same reads from
GitHub's runners are `.github/workflows/nba-data-probe.yml`
(`src/sports/nba/data_probe.py`); until it has run there, every "works"
below means "works from a home connection".

## Verdict: GO for the history and the backtest; the live run is Mark's call

**History and backtest: GO, on ESPN's public API, read from the local
machine.** It is free and needs no key, and it answers for everything the
NFL's workflow needs:

- schedule and results;
- a box score with the figures possessions are built from, and every
  player's minutes;
- a pre-game moneyline for nearly every game since 2015-16, except
  2017-18 (756 of 1231; section 3);
- an injury report.

SportsDataverse's `hoopR-nba-data` mirrors ESPN's box scores back to 2002.
It also adds a consensus closing spread from The Odds API, which is what
the market is checked against. Mark ruled out paid data on 2026-10-05.

**The live run cannot use ESPN.** ESPN refuses GitHub's runners (#131,
docs/stage-history.md), and Mark ruled out routing around that. The
league's own feeds refuse too:

- `cdn.nba.com` returns 403 from the local machine (with or without browser
  headers) and from a cloud fetcher;
- `stats.nba.com` times out.

That leaves `hoopR-nba-data`. It is a GitHub repository, so a runner can
read it. It is updated daily at about 11:40 and 12:00 UTC, more often in
the playoffs, and its schedule and box scores are enough for the live
run's ratings and grading. **Nothing found gives a runner a pre-game NBA
price or an injury report**, so a live Model B has no market to read, and
Model A's availability term (section 4) has no list of who is out. The
choices, for Mark:

- a job on the local machine that reads ESPN's price and injury report
  before each lock and commits them for the runner to use, so both models
  run live as registered (the machine must be on at those times);
- no live NBA picks this season, with the models judged in the backtest
  alone;
- a paid feed, already ruled out.

Until he chooses, there are no live NBA picks; the history and the
backtest go ahead.

**Superseded (2026-10-09).** A second probe from a runner (#357) found
ESPN's odds and injury report answering GitHub's runners after all, and
Kalshi's game markets too. Mark said GO: both models live from opening
night, 2026-10-20, Model B priced by ESPN's odds with Kalshi as the named
fallback and "no price" rather than a silent switch
(`experiments/nba/stage65/registry.json`, Stage 65). The nightly canary
reads each of those sources and says when one stops answering.

## 1. Schedule, results and box scores: ESPN

| What | Endpoint | Checked |
|---|---|---|
| A day's games | `site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates=<yyyymmdd>` | Every date of 2016-17, 2019-20, 2022-23 and 2023-24 to 2025-26 (the market collection walks them) |
| A game's box score | `.../summary?event=<id>` | Field-goal and free-throw attempts, offensive rebounds and turnovers for both teams |
| Injuries | `.../injuries` | Teams, each player with a status |

**Some finished games have an empty box score.** ESPN lists 161 games of
2015-16, 168 of 2016-17 and 172 of 2017-18, and six of 2020-21's play-in,
with no team figures and every player's minutes as `--` (2015-16's opening
night, Cleveland at Chicago, is the first). hoopR's `team_box` and
`player_box` hold all of them but two (one each in 2016-17 and 2017-18)
and none of the six play-in games, so the history reads those games from
hoopR, marks where each came from, and names the eight it cannot fill.

Start times are UTC (`date` ends in `Z`). The scoreboard carries every
game the league plays, so **the All-Star weekend's games come through as
teams** (`EAST`, `WEST`, `GIA`, `LEB`, `USA`, `WORLD`, `STARS`, `STRIPES`,
and in 2025 `CAN`, `CHK`, `KEN`, `SHQ`). **ESPN files them under the
regular season** (season type 2), so the season type alone does not keep
them out. The competition's own type does: `STD` for an ordinary game,
`ALLSTAR` for these, `CC` for the NBA Cup final (a real game at a neutral
site, which the league leaves out of the standings). Season types seen on
real dates: 1 preseason, 2 regular season, 3 playoffs, 5 play-in.

The playoff rounds carry their own competition types: `RD16` (first round),
`QTR`, `SEMI` and `FINAL`. A knockout game listed before its teams are
known (the NBA Cup's, the playoffs') has `TBD` for a team.

Read whole, along each season's calendar: 2024-25 has 1236 regular-season,
6 play-in and 84 playoff games, 5 of them postponed (Los Angeles, January
2025) and replayed under new ids; 2021-22 has 1241, 6 and 87, 11 of them
postponed. Each is 1230 played regular-season games plus the NBA Cup final
(from 2023-24) and the postponed listings. 2026-27, read on 2026-10-06,
has 1200 games with both teams known and 6 NBA Cup knockout games listed
with `TBD` teams, which are left out until the teams are known. The league
adds the season's other games in December, once the Cup's group stage is
decided.

States seen: `STATUS_SCHEDULED`, `STATUS_FINAL` and `STATUS_POSTPONED`
(2021-12-20, Orlando at Toronto, with the note "Makeup date March 4" and a
score of 0-0). The schedule module will map each state it knows and stop
on one it does not, as the NHL's does.

## 2. Fallback: SportsDataverse `hoopR-nba-data`

`nba/team_box/parquet/team_box_2002.parquet` to `team_box_2026.parquet`,
57 columns, the same box-score figures. **It is a mirror of ESPN, not an
independent source**: a check of one against the other guards against an
outage or a dropped game, not against ESPN being wrong. That is still the
check the NHL's history ran (Stage 56), and the NBA's will run it the same
way, at the same 99% floor.

## 3. The market (Model B)

**ESPN's moneyline**, at
`sports.core.api.espn.com/v2/sports/basketball/leagues/nba/events/<id>/competitions/<id>/odds`.
Unlike the NHL's, it is a two-way market in every season (basketball has no
draw), so no conversion is needed.

*Coverage* (games on ESPN's scoreboard with a moneyline, All-Star games
removed, collected 2026-10-05):

| Season | With a line | Sportsbook | Close as well as the line |
|---|---|---|---|
| 2015-16 | 1232 of 1232 | 5Dimes | no |
| 2016-17 | 1214 of 1233 | 5Dimes | no |
| 2017-18 | **756 of 1231** | CG Technology | no |
| 2018-19 | 1229 of 1230 | Caesars | no |
| 2019-20 | 974 of 974 | CG Technology, then Caesars | no |
| 2020-21 | 1112 of 1112 | Betfair, then Caesars | no |
| 2021-22 | 1235 of 1241 | Caesars | no |
| 2022-23 | 1231 of 1231 | Betfair | no |
| 2023-24 | 1232 of 1233 | Betfair | yes, 1231 |
| 2024-25 | 1235 of 1236 | ESPN BET | yes, 1231 |
| 2025-26 | 1228 of 1234 | ESPN BET, then DraftKings | yes, 1218 |

Where only one line is given, ESPN does not say whether it is the opening
or the closing price. The check below says it behaves like a closing one.
One 2023-24 row came from a provider named "ESPN Bet - Live Odds", an
in-game price. The history reader will drop any provider marked live, so no
price set after the start is ever used; the checks below leave them out too.

*Coverage in the history* (`data/nba/history/market_<season>.csv`, written by
`src/sports/nba/history.py`). The history reads ESPN's odds feed one game at
a time rather than the scoreboard, and finds a price for nearly every final
game the history holds, 2017-18 included:

| Season | Games | With a price | Closing price |
|---|---|---|---|
| 2015-16 | 1316 | 1316 | 0 |
| 2016-17 | 1308 | 1270 | 0 |
| 2017-18 | 1312 | 1311 | 0 |
| 2018-19 | 1313 | 1312 | 0 |
| 2019-20 | 1144 | 1143 | 0 |
| 2020-21 | 1165 | 1165 | 0 |
| 2021-22 | 1323 | 1323 | 0 |
| 2022-23 | 1320 | 1320 | 0 |
| 2023-24 | 1319 | 1319 | 1319 |
| 2024-25 | 1321 | 1321 | 1321 |
| 2025-26 | 1322 | 1322 | 1316 |

The 2016-17 gap is the 38 games whose only line came from a projection site
(numberfire, teamrankings), which is not a market. Games here include the
play-in and playoffs, which the scoreboard counts above did not.

*Accuracy, against an independent market.* hoopR's
`betting_lines/closing_lines_odds_api.parquet` holds The Odds API's
consensus closing spread for 7942 games, 2020-07 to 2026-06, keyed by
ESPN's game id. A spread from a consensus of books and a moneyline from
one book are different instruments from different sources. Over the
7213 games matched (2020-21 to 2025-26, the archive's whole span):

- the moneyline's favourite is the spread's favourite in 99.84% of
  games; the 11 disagreements are all close calls, none with a spread
  above 5 points;
- the moneyline's no-vig log-odds and the spread correlate at 0.992.

*Usefulness, as a forecast of who wins.* The no-vig moneyline's log loss
against the home-win base rate (lower is better), on the games with a
line: 0.571 vs 0.677 (2015-16), 0.612 vs 0.678, 0.627 vs 0.680, 0.594 vs
0.676, 0.605 vs 0.688 (2019-20), 0.617 vs 0.689, 0.608 vs 0.689, 0.624 vs
0.680, 0.582 vs 0.689, 0.582 vs 0.689 and 0.569 vs 0.687 (2025-26). 2017-18
has a line for only 756 games, so Model B trains on fewer that season.
The NBA is the most predictable of the three sports, and its market is
the sharpest forecast here.

**Decision (Claude, under Mark's delegation, 2026-10-05).** Model B's
market input is ESPN's no-vig two-way home-win probability, the closing
price where ESPN gives one. The NBA's registration (Stage 61) names the
seasons; the spread archive stays the checked reference.

## 4. Injuries and lineups

ESPN's injury report lists each team's injured players with a status
(`Out`, `Day-To-Day` and so on). The NBA has no single starter who decides
a game the way a quarterback or a goalie does, so the registration's
player term is a team's **availability**: the share of its expected
minutes that play. In the backtest, who played comes from the box score's
minutes; live, it would be everyone not listed `Out`, which is the
injury report a runner cannot read (the verdict above). The gap between
the two is the registration's measurement M2.

## 5. Team identity across seasons

ESPN's abbreviations are stable over every season collected here: 30
teams, the same codes in every season collected from 2016-17 to 2025-26 (`GS`, `NO`, `NY`, `SA`,
`UTAH`, `WSH` are ESPN's own spellings, not the league's). The last
relocation (Seattle to Oklahoma City, 2008) and the last renames (New
Jersey to Brooklyn, 2012; the Bobcats to the Hornets, 2014) are all before
any training season the registration will use.
