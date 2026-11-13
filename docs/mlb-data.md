# MLB data: what exists, and the go/no-go (Stage 97)

Read-only checks from the local Windows machine on 2026-11-11, with their scripts in the session archive
(`mlb_probe0.py` to `mlb_probe4.py`). The same reads from GitHub's runners are
`.github/workflows/mlb-data-probe.yml` (`src/sports/mlb/data_probe.py`); until it has run there, every "works" below
means "works from a home connection". On 2026-11-12 the probe ran on a runner in #711: every required Stats API read answered in shape, and so did Retrosheet's 2025 game log, ESPN's scoreboard and a past ESPN moneyline, and Kalshi's MLB markets; DraftKings and Polymarket were unreachable.

## Verdict

**GO for the history, the backtest and a live run on GitHub's runners.** The MLB Stats API is the primary for schedule, results, probable pitchers and box scores, read from a runner (#711); Retrosheet's game logs are the checked fallback for history (section 2). ESPN's pre-game moneyline gives Model B a market from 2013 (section 3), read from a runner too. Open before the live run: when the probable pitchers are published (section 4, measured in spring training).

## 1. Sources

- **MLB Stats API** (`statsapi.mlb.com/api/v1`), free and keyless: the schedule with each game's `gamePk`, UTC start,
  official date, clubs, state, doubleheader flag and game number; probable pitchers (`hydrate=probablePitcher`); box
  scores with every pitcher who appeared; the clubs by season. The likely primary.
- **Retrosheet game logs** (`retrosheet.org/gamelogs/gl<season>.zip`), one line a game back to the nineteenth century.
  The likely fallback for history. A season's log is posted some weeks after the World Series: on 2026-11-11 the 2026
  log was a 404 and 2025's was there.
- **ESPN** scoreboard and pre-game moneylines (`sports.core.api.espn.com`), as the NHL's and the NBA's backtests used.
- Live prices: Kalshi's MLB game markets and Polymarket answered from the local machine; DraftKings answered 403.

## 2. History depth, and the two sources agreeing

The Stats API lists every regular season's schedule back to at least 2005 (2,457 games that year). Its finals and
Retrosheet's game log were compared game by game (date, game number, clubs, both scores), with each Stats API club
matched to its Retrosheet code from the season itself:

| Season | Finals (both) | Agree | Differ |
|---|---|---|---|
| 2025 | 2,430 | 2,430 | 0 |
| 2021 | 2,429 | 2,428 | 1 |
| 2020 | 898 | 870 | 28 |
| 2015 | 2,429 | 2,426 | 3 |

**Every difference is the same game with home and away swapped**: one 2021 game (2021-08-10, Toronto and the
Angels), three Orioles-Rays games in 2015 (2015-05-01 to 05-03, moved to Tampa during the Baltimore unrest), and 28 in
2020, the season of relocations (Toronto's home games away from Toronto, series moved after outbreaks). Checked
against the Stats API's own venue (`mlb_probe4.py`): in every sampled case the Stats API's home club is the one
batting last, playing in the other club's park (Toronto "at home" in Nationals Park in 2020, Baltimore "at home" in
Tropicana Field in 2015, Toronto "at home" in Angel Stadium for a 2021 makeup game), and Retrosheet names the club whose
park it was. The score, the date and the game number agree. That is a
neutral-site question for the registration (Stage 98), as the NFL's Stage 38 answered for its own: the Stats API's
venue on each game says where it was played.

## 3. A market for Model B

ESPN's pre-game moneyline, both sides, read for every final game by `python -m src.sports.mlb.market_history 2010 2026`
(`src/sports/mlb/market_history.py`): the closing price where ESPN gives one, the listed price before that, never a
live provider's. Games priced, of the history's finals:

| Season | Priced | Share |
|---|---|---|
| 2010 | 0 of 2,462 | 0% |
| 2011 | 0 of 2,467 | 0% |
| 2012 | 670 of 2,467 | 27% |
| 2013 | 2,408 of 2,469 | 98% |
| 2014 | 2,395 of 2,462 | 97% |
| 2015 | 2,409 of 2,465 | 98% |
| 2016 | 2,386 of 2,463 | 97% |
| 2017 | 2,393 of 2,468 | 97% |
| 2018 | 2,274 of 2,464 | 92% |
| 2019 | 2,448 of 2,466 | 99% |
| 2020 | 941 of 951 | 99% |
| 2021 | 2,448 of 2,466 | 99% |
| 2022 | 2,462 of 2,470 | 100% |
| 2023 | 2,468 of 2,471 | 100% |
| 2024 | 2,449 of 2,472 | 99% |
| 2025 | 2,477 of 2,477 | 100% |
| 2026 | 2,467 of 2,469 | 100% |

There is no real moneyline before 2012. ESPN's odds for 2010 and 2011, and most of 2012, carry only a point spread
and a moneyline of 0, which is no price; the probe in #711 counted those as priced, which this section corrects. Part of
2012 (late in the season) is priced, but 669 of its 670 prices are AccuScore's, a model's output rather than a book's,
and are not used (audit 8, finding S3; the Stage 98 amendment of 2026-11-13). Nor is a price whose two implied
probabilities sum outside 1.00-1.20 (75 prices, in 2013 and 2017 to 2019). From 2013 ESPN prices 92% to 100% of each season's
finals; the rest have no usable ESPN price or cannot be matched to exactly one ESPN game (some doubleheaders), and
are left unpriced rather than guessed. Model B trains only on games with a usable price (Stage 98), so its training starts in 2013 in
effect, which is enough for the validation and confirmation seasons.

## 4. Starting pitchers

The Stats API's schedule names each game's probable pitchers, and a box score names every pitcher who appeared, the
starter first. A past day (2025-07-04) named both probables for all fifteen games. **When** the probables are
published before first pitch cannot be measured in November; it is measured in spring training (February 2027) by
reading the schedule on a timer, before Stage 101's starting-pitcher routine is set. OPEN until then.

## 5. Club identity across seasons

The Stats API's club `id` is stable through renames and moves: 114 was "Cleveland Indians" (CLE) in 2021 and is
"Cleveland Guardians" (CLE) in 2025; 133 was "Oakland Athletics" (OAK) in 2021 and is "Athletics" (ATH) in 2025.
Every table keys on the id, never on a name or an abbreviation. Retrosheet's codes differ from the Stats API's
abbreviations for eighteen clubs (ARI for AZ, CHN for CHC, ANA for LAA and so on); the map is learned per season as in
section 2, not typed by hand.

## 6. Doubleheaders, postponements and suspended games

2025 as listed by the Stats API: 2,464 schedule rows for 2,430 games. A postponed game keeps its `gamePk` and is
listed again on the day it was played, so 34 games appear twice; 30 rows are "Postponed" and 5 games "Completed Early"
(shortened, and final). 61 rows carry a doubleheader flag (`S` for split, `Y` for traditional); each game of a
doubleheader has its own `gamePk` and game number 1 or 2 (2025-04-26 has one). So: one row per `gamePk`, the last listing wins, a final is "Final" or
"Completed Early", and the lock and grading key on `gamePk` (Stage 101 item 5 adds the mutation cases).

## 7. Decision record 0006

Decision 0006 says "MLB not this year". It was amended on 2026-11-12 (docs/decisions/0006-multi-sport.md): MLB is the fourth sport, built through the winter on the same core (Stages 97 to 101) and live from Opening Day 2027.
