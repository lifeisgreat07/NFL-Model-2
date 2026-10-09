# More sports, NHL then NBA

Part of the stage history; the index is `docs/stage-history.md`. Moved verbatim from
that file on 2026-10-06 (Stage 49 item 24).

## Stages 50 to 61: more sports, NHL then NBA (Mark, 2026-10-05)

Mark: make the project multi-sport. A home page with a card per sport;
each card opens that sport's boards, ratings, accuracy and the rest. NHL
first, then NBA; MLB not this year (its season has ended). Two rules for
all of it:

- **Each sport runs the NFL's workflow**, so moving between sports feels
  the same: the same page set, Model A (the sport alone) beside Model B
  (plus the market), the same lock, grading, drift check, alerts,
  registrations and paired bootstrap, a routine for the late-breaking
  player (the starting goalie is the NHL's quarterback), and the same PR
  loop with Booth.
- **Nothing bleeds between sports**, and that is enforced by tests, not by
  care: a sport's code imports only the shared core, never another sport;
  a sport's workflows write only that sport's folders; every name a sport
  owns (files, issues, jobs, storage keys, CSS, routes) carries the sport;
  a change to one sport leaves every byte the other publishes unchanged.

Checked on 2026-10-05 from the local machine (read-only; nothing in the
repository): the NHL's public API (`api-web.nhle.com`) answered the
schedule and a finished game's play-by-play (337 events, shot coordinates,
the goalie in net, four goalies on the roster), with play-by-play back to
2010. It carries **no betting lines**. SportsDataverse's
`fastRhockey-nhl-data` and `hoopR-nba-data` were both updated that day.
The 2026-27 NHL season began September 29 (1,344 games, 84 per team).

### Stage 50 - The multi-sport contract

1. Decision record 0006: the architecture, the isolation rules above, and
   what is shared (lock engine, grading, drift, bootstrap, registry, alerts,
   page shell and design tokens, agents, session tools) against what each
   sport owns (data, features, models, lock rule, rules of the game,
   pages, routines, workflows).
2. The sport-module interface, written down and typed: schedule, results,
   features, model specs, lock rule, game rules (ties, overtime,
   shootouts, standings points), display settings.
3. The layout: `src/core/`, `src/sports/<sport>/`, and per-sport `data/`,
   `predictions/`, `results/`, `experiments/` folders and page routes.
4. Isolation guards, each mutation-tested: no sport imports another; no
   sport's workflow commits outside its folders; every sport-owned name
   carries its sport; core imports no sport.
Documents and tests only; may run before the lock.
DONE 2026-10-05 in #292: `docs/decisions/0006-multi-sport.md`,
`src/core/sport.py`, `src/core/isolation.py`, `tests/test_sport_isolation.py`,
17 mutation cases, all caught. Mark approved the six design choices: three
layers, with `src/site/` the only code that sees every sport; `src/sports/nfl`
and `src/sports/nfl/research` counted as the NFL until Stage 52; the lock rule per
sport and the lock engine shared; a fixed schedule column contract with a
cancelled state; Model B optional; rule 5 a build proof, not a test.

### Stage 51 - NHL data, decided before any model

1. A probe workflow (like `nfl-schedule-probe.yml`): schedule, results and
   play-by-play read from GitHub's own runners.
2. History depth and completeness per season; the primary source and a
   checked fallback (the API and `fastRhockey-nhl-data`).
3. A market source for Model B, historical and live; if none, the NHL ships
   Model A only and says so.
4. A starting-goalie source and when it publishes; the injury source.
5. Team identity across seasons (relocations and renames, the 32 teams).
6. A written go/no-go. Read-only; may run before the lock.
DONE 2026-10-05 in #294, except item 2's fallback check (both loaders
agreeing on one week, as `nfl_data_py` was checked), which is Stage 55 item
1. The probe passed on GitHub's runner for all seven sources. The go/no-go
is `docs/nhl-data.md`: GO for Model A and Model B. Mark ruled out paid data
and chose the Kaggle sets; the one with lines cites ESPN's public API, so
the source itself is used (Claude, under Mark's delegation): free, every
game from 2020-21, the three-way line before 2024-25 converted and checked
against the free archive's two-way close.

### Stage 52 - The NFL becomes the first module

1. Sport-agnostic code moves to `src/core/`; the NFL's to `src/sports/nfl/`.
2. The NFL's files move to `data/nfl/`, `predictions/nfl/`,
   `results/nfl/`, `experiments/nfl/`, history kept (`git mv`).
3. Workflows renamed per sport with schedules unchanged; Mark re-points
   the cron-job.org jobs and the QB routine's paths.
4. Tests and the mutation corpus re-targeted; the whole corpus run once.
5. The proof: picks, backtest, `data/nfl/calibration.json` (moved) and the page
   byte-identical before and after (the #265 method).
After the 10-08 lock and Stage 42's slot guard, merged in the window after
a Thursday lock so a weekend of refreshes and the canary test it before
Tuesday's run.
BUILT AND PROVEN 2026-10-05, not merged. One re-runnable script does the
whole move (`migrate_nfl.py` in the session archive, with `git mv` for
history); re-run it on the `main` of the merge window rather than rebasing
the branch. Core: alerts, atomic_write, runlog, model_specs, template_parts
(typed to --strict). Workflows renamed `nfl-*.yml` with "NFL ..." names and
"NFL: ..." alert titles; the isolation guard's legacy lists emptied.
Records (`memory/`, `data/`, `experiments/`) are never rewritten: an early
version edited Booth's audit log. Suite on the moved tree: 0 failed. Proof:
the weekly run's picks for week 5 with the clock fixed, the backtest, the
calibration file, ratings, odds, line history and the PDF text all
byte-identical; the page differs in 26 path strings, each naming a moved
file.

### Stage 53 - Pages per sport

1. The template split into the shared shell and per-sport parts; the build
   writes `/nfl/index.html`.
2. The NFL moves to `/nfl/` with a redirect from the old address; README,
   share image, link preview and the tests that hold the URL change together.
3. The deploy builds each sport on its own: a sport whose build fails keeps
   its last good page and opens its own issue; the others publish.
4. Browser checks per sport page.
5. Per-sport browser storage keys (My Picks) and CSS scopes.

### Stage 54 - Locks per game, runs every day

1. The lock rule becomes the module's: the NFL's weekly rule through the
   interface unchanged; per game for the NHL (saved before its start,
   never rewritten, only locked picks graded).
2. Daily runs started by cron-job.org, GitHub's cron as fallback; the slot
   guard generalised per sport.
3. Grading per game; postponed, cancelled and suspended games; previews.

**Progress (2026-10-06).** The NHL's per-game lock rule merged as #299 (`src/sports/nhl/lock.py`),
and its per-game grading as part of #302 (a cancelled game is never counted). The NFL's weekly
rule moves behind the interface with Stage 52; the slot guard waits for Stage 42.

### Stage 55 - The NHL data pipeline

1. Loader, schema check and cache for the NHL; the canary for the NHL.
2. Schedule, results and live status (scheduled, in progress, final,
   postponed); the day's slate.
3. Starting goalies, injuries and the market lines, each stored per game
   with where and when it was read.
4. Team colours and logos, checked for contrast and colour-blind
   separation like the NFL's.

**Progress (2026-10-05).** Items 1 and 2 merged as #295 (`src/sports/nhl/schedule.py`), item 3 as #296
(`market.py`, `goalies.py`, `teams.py`); injuries followed as #320 (`injuries.py`: ESPN's list from
SportsDataverse, stored in each saved pick with its day and read time, context only). Item 4 (colours and logos)
merged as #300. The NHL's canary merged with #302 and was scheduled by #303, which put a copy of
`alerts` in the core ahead of Stage 52 (Stage 52's script now drops the NFL's copy).

### Stage 56 - The NHL model and its backtest

1. A registration before any result: features, validation and held-out
   seasons, log loss first, the market as baseline if Stage 51 found one.
2. Model A: team strength from shots and goals, recency-weighted, plus a
   starting-goalie term; refit on strictly earlier games.
3. Model B if there is a market; the backtest, calibration and the
   reproducibility audit; every published figure tied to its file by a test.

**Progress (2026-10-05).** Item 1: `experiments/nhl/stage56/registry.json`, merged as #298 before any
model was fitted, written under Mark's delegation. Items 2 and 3 merged as #301: the history
(2015-16 to 2025-26, shots on goal agreeing with the fallback on every game), Model A and Model B,
and the backtest as registered. H1 ACCEPT (Model A beats the base rate), H2 and H3 INCONCLUSIVE,
the goalie term adding almost nothing (M1). Booth reproduced the backtest byte for byte on Linux.

### Stage 57 - The NHL's pages

1. The board: today's games and the week by day, with the NFL board's card
   design, the goalie where the NFL shows the quarterback.
2. Ratings (teams and goalies), Season Accuracy, calibration, Model Lab,
   Methodology, a team page, What's Changed, Checking the AI's work.
3. Standings odds with NHL rules (two points a win, one for an overtime
   loss, the NHL's tiebreakers) by simulation.
4. Rendered options for Mark where the NHL differs from the NFL; looked at
   in both themes at phone and desktop widths before any PR says so.

**Decided (Mark, 2026-10-05, from the rendered "NHL Board Options").** The board pages by week,
grouped by day (option C; he also liked the strip of days, so a strip pinned above the week as
jump links is worth showing him when it is built). Each goalie carries its status, Confirmed in the
accent blue so green still means only a pick scored right (A). The market line shows both prices
and the probability with the margin out (A).

**Progress (2026-10-06).** Item 3 (standings odds) merged as #307. The daily run writes the pages'
schedule and ratings files every run (#309). The pages merged as #310 (`src/sports/nhl/site.py`,
`src/sports/nhl/pages/`): the week by day with the strip of days, the cards with both models, the
market and each goalie's status, standings odds, ratings, Season Accuracy, Model Lab, Methodology
and Checking the AI's work, rendered in both themes at phone and desktop widths before the PR.
Not deployed: the deploy wiring waits for the 10-08 lock and goes with Stages 52 and 53. Item 2's
team pages, calibration table and What's Changed merged as #315. #317 put the page under the
browser checks (Stage 53 item 4 for the NHL), which found tables a keyboard could not scroll; a
phone-width look found #310 had shipped with no menu below 1080px. Both fixed in #317.

### Stage 58 - The NHL goes live

1. A forward-test registration, then the first lock.
2. The daily workflow, its cron-job.org job (Mark), alerts titled "NHL: ...",
   its drift baseline, its rows in the runs table and the session-start
   check.
3. A goalie routine on game mornings that opens a PR with sourced starters,
   never given the lock scripts (Mark creates it, as the QB routine).
4. Booth's protocol, Spotter and Line Judge cover the NHL.

**Progress (2026-10-06).** Item 1's registration and the daily run, canary and drift check merged as
#302 (`experiments/nhl/stage58/registry.json`, baseline 0.6753). Item 2's workflows merged as #303
(`nhl-daily.yml` 14:00 and 21:00 UTC, `nhl-canary.yml` 06:40 UTC, "NHL: ..." alerts, the
session-start check), with #306 after the first hand run failed on a folder that did not exist yet.
Left for item 2: the cron-job.org jobs (Mark) and the runs-table rows, which wait for the NHL's
pages. Items 3 and 4 are not started; Daily Faceoff is read by the run itself until the routine exists.

### Stage 59 - The home page

1. Two or three rendered designs for Mark: a card per sport with live
   status from the build ("Week 5 picks locked", "9 games tonight").
2. The site root becomes the home page; a sport switcher in the shared
   header; share image and link preview for the home page.
3. Browser checks, accessibility, both themes, phone first.
Launched the day the NHL's forward test is live, not with "coming soon".

**Decided (Mark, 2026-10-05, from the rendered "Pick'em Home Options").** Option A: a card per sport
with its live status ("Week 5 locked", "9 games tonight"), its season record and a link to its board.

### Stage 60 - The isolation audit

**Progress (2026-10-06).** Item 1 merged as #316: `tests/test_sport_read_sets.py` runs each
sport's page build under an audit hook and fails on any file of another sport it opens; #321 added
the NBA's build. Item 2's corpus half: the whole mutation corpus at `36fc82d` (2026-10-06), every
case caught by the test it names. Its other half, a Booth fixture with a planted cross-sport leak,
spends a Booth run and waits for Mark.

1. A test run that changes the NHL and proves no NFL byte moved, and the
   reverse.
2. The whole mutation corpus; Booth fixtures seeded with a cross-sport
   leak it must catch.
3. A fresh audit of the multi-sport repository before the NBA starts.

### Stage 61 - The NBA, the same way

Stages 51 and 54 to 58 again for the NBA: the probe (`hoopR-nba-data` as
the likely source; the NBA's own stats site has refused cloud servers), the
pipeline, the model (player availability is the late-breaking input; rest
and back-to-backs only through a registration), the pages, an availability
routine, the go-live, and a card on the home page.

**Progress (2026-10-06).** The probe and `docs/nba-data.md` merged as #311 (GO for history and
backtest from ESPN on the local machine; the live run is Mark's call, since no runner can read a
pre-game price or injury report). The registration merged as #312
(`experiments/nba/stage61/registry.json`: point, efficiency and availability matchups; H1 to H3, M1 and M2), before any
feature was computed on real games. The schedule loader merged as #313 and the history reader as
#314: ESPN's box scores are empty for 501 games of 2015-16 to 2017-18 and six of 2020-21's
play-in, so those come from hoopR's box scores, and the eight neither has are named. #318 left
projection sites (numberfire, teamrankings) out of the market. The backtest merged as #319: H1 ACCEPT,
H2 ACCEPT, H3 REJECT (Model B worse than the market alone), and the availability term worth 0.012 of
log loss (M1). No live NBA picks until Mark decides how the live run reads a price and injuries.
The pages merged as #321: the backtest said plainly, no board (option A of the rendered "NBA Board
Options", Claude's recommendation under the delegation, for Mark to confirm).
