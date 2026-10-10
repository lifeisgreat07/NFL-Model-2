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
MERGED 2026-10-08 as #351, re-made by `migrate_nfl_v12.py` on that day's
`main` (four hand edits for work merged after v11's rehearsal), the whole
corpus run once (one case re-aimed, `d5f4069`), the #265 proof 13 of 14
byte-identical and the page identical once the path moves are undone. Mark
re-pointed the six cron-job.org jobs that night.

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

## Stages 62 to 67: the site and the NBA (Mark, 2026-10-09)

Mark's list after Stage 52 merged, with Claude's pushback taken where he
agreed. Declined: the leagues' official logos on the home page (trademarks
read as endorsement on a public site; one icon set of our own instead, in
Stage 62). Decided at the same time: Stage 38's neutral-site question gets
a declared rule (no home edge at a neutral site, back-checked on past
neutral games, disclosed as a rule change rather than a tested win); Stage
46 items 6 and 9 go ahead and item 8 (`feed.xml`) is dropped; Stage 47
items 13 and 14 are approved; Stage 40 waits for January.

### Stage 62 - One site, one look

1. The light/dark choice is the site's, not each page's: one shared storage
   key, declared as an exception the isolation tests name (each page had
   its own key since Stage 53 item 5, so each button worked alone).
2. One icon set for the sports in the style of the NFL's football: a puck
   for the NHL, a ball for the NBA, top left on every page and on the home
   cards; rendered options first.
3. The NHL's team logos at the NFL Week Board's size.
4. Browser checks that the theme follows the visitor from page to page.

Progress (2026-10-09 overnight): items 1 and 4 done (#353, the key
`site:theme`), item 3 done (#354). Item 2: options rendered on the
canvas "Sportalytics Icons and Wordmark"; waiting on Mark.

Item 2 done (2026-10-09, #375): puck P3 and ball B2, top left on the NHL
and NBA pages (sidebar and phone bar) and on the home cards.

### Stage 63 - Boards that show what happened

1. On the NHL board, every played game shows the pick, the final score,
   the winner and whether each model was right.
2. Every upcoming game with a locked pick shows it, marked locked; a game
   not yet locked says when its pick will lock.
3. The NBA board the same, once it exists (Stage 65). The NFL board
   already does this (Mark: no gap there).

Progress (2026-10-09 overnight): items 1 and 2 done for the NHL (#355);
the lock time shown is the page's copy of `lock.py`'s rule, run
against `GameLock` over 384 start times. Item 3 waits for Stage 65.
Item 3 done with Stage 65's board (#370).

### Stage 64 - A day at a time

Mark chose, from the rendered "NHL Day Board Options" (2026-10-09): option
A's day strip (seven day buttons with game counts, opening on today) with
option B's compact rows (time, game, pick, result; a row expands on tap to
both models, the market, the lock time and the goalies).
1. The NHL board opens on today and moves day by day; the week stays one
   tap away.
2. Fewer cards on screen, phone first; the day's summary ("3 games, 1 of 1
   right so far") above the rows.
3. The NFL keeps its week view: it plays by the week.
4. Browser checks at phone and desktop widths, both themes.

Progress (2026-10-09 overnight): items 1, 2 and 4 done (#356), a
click-through browser check included.

### Stage 65 - The NBA goes live

Mark: on GitHub's runners only; his PC is not on overnight.
1. The season's start date and a schedule source a runner can read.
2. Model A live from the first game, since it needs no market.
3. Model B only where a runner can read a pre-game price; where none can,
   the page says so plainly.
4. An availability/injury input a runner can read, stored per pick with its
   read time, as the NHL's is; none readable: Model A without it, said so.
5. A forward-test registration before the first lock, the daily run, its
   cron-job.org jobs (Mark), alerts "NBA: ...", drift baseline and canary.
6. The board built like the NHL's after Stages 63 and 64; the home card
   shows live status.

Progress (2026-10-09 overnight): the source probe ran on a runner
(#357). hoopR, ESPN (scoreboard, box score, odds, injuries), Kalshi,
Polymarket and SportsDataverse's injuries answered; DraftKings and
cdn.nba.com did not. Opening night is 2026-10-20. Claude's go/no-go
(GO for both models, on conditions) is in `memory/2026-10-09.md`;
Model B's market and the start date are Mark's.

Done (2026-10-09): Mark said GO for both models from opening night,
ESPN's odds with Kalshi as the named fallback. #367 registration and
drift baseline; #368 lock, market, injuries, drift and the daily run; #369
workflows, canary and alerts; #370 the day board and the live home card.
Mark set up the three cron-job.org jobs the same day.

### Stage 66 - The home page, looked at again

Mark wants a home page that makes sense to a first-time visitor: "highest
UX score possible".
1. An audit of today's home page: what a newcomer sees first, the phone
   layout, each card's content, anything stale or empty.
2. Two or three rendered options for Mark, built on Stage 62's icons and
   Stage 67's name.
3. The chosen option built, with browser and accessibility checks.

Progress (2026-10-09 overnight): item 1 done,
`docs/design/HOME-AUDIT-2026-10-09.md`; item 2, three options on the
canvas "Sportalytics Home Page Options" (Claude recommends A with C's
"New here?"); waiting on Mark.

Item 3 done (2026-10-09, #377): option A with C's "New here?", axe-core
clean at six widths.

### Stage 67 - Sportalytics

Mark's name for the project. The display name only: the repository keeps
its name, so the published address, the cron-job.org jobs and the API calls
stay as they are (Mark: no redoing the API work).
1. Page titles, the header, the home page, share images and link previews,
   and the README's first line say "Sportalytics".
2. "The Pick'em Model" goes, with a test that no old name shows anywhere a
   visitor can see.
3. A small wordmark beside Stage 62's icons, rendered options first.
The name is in use elsewhere (an Android developer, "Sportalytics Private
Limited"); fine for a portfolio, worth a trademark check if the site ever
goes commercial.

Progress (2026-10-09 overnight): item 3, three wordmarks on the canvas
"Sportalytics Icons and Wordmark"; waiting on Mark.

Done (2026-10-09, #376): wordmark W2, every visitor-facing name, the
share image remade, and `tests/test_product_name.py`'s check that the old
name shows nowhere a visitor sees.

## Stage 68 - Fable audit (2026-10-09)

The fifth audit (Fable, 80/100, run on `main` at `b2cde78`, which is
`fc0d3d4` after #378 plus four bot data commits). Every finding was checked
against the code first; the verdicts, with evidence, are in the Audit
Response Log. Two findings were wrong (E9's daily slot guard, U40's NFL QB
provenance), many were partly right, and the NHL half of the dated row
overlap does not happen. What is accepted is below, in the order it will be
done: the dated items first (Ubuntu 26 from 10-19, NBA opening night 10-20),
then what can lose a pick, then what a visitor sees, then the rest. One PR
per item; Stage 40 is not touched.

1. The NHL and NBA daily runs keep pipefail through `tee`, with a scan of
   every `| tee` in every workflow (E1). Done, #380.
2. The daily runs retry a refused push (three tries, rebasing between) and
   keep the picks as an artifact when the run fails (E2).
3. A started game with no saved pick raises the alert; the start delay is
   measured against the slot the run belonged to, with a threshold that
   fits a daily sport (E3).
4. `ubuntu-24.04` pinned on the writers, the canaries and the browser
   checks until a green NBA week; then unpinned (E6). Before 10-19.
5. The NBA's phone rows stop drawing the pick over "Locks 5:30 PM" (U25,
   NBA only: the NHL's labels fit). Before 10-20.
6. The NBA explains itself before opening night: the home card's "Live
   from" status keyed on no picks, a pre-season panel on the board with
   the backtest's H3 REJECT, and the opening tip-off read from the
   schedule rather than three hard-coded times (U4, U23, U24, U38). Before
   10-20.
7. Booth's dispatch refuses a fork PR (E11).
8. NHL/NBA team abbreviations checked against the league's list when the
   schedule is built, and escaped where the page draws them (E12).
9. The Pages deploy watches every sport's data folders (E4).
10. The weekend refresh gets a concurrency group, so a late GitHub copy
    waits for the next slot's run instead of racing its push (E5).
11. `releases.yml` fails when a version has no tag; v2.6 is tagged (E7).
12. One list of watched runs, NHL and NBA included (E8).
13. The page-header guard covers all three sports, and the two "Day by
    Day" eyebrows that break it are fixed (U15, E32).
14. The dependency audit reads both requirement files; scipy is listed
    (E14).
15. Each sport's daily run tested end to end over a small synthetic slate
    (postponed, overtime, no price, a late run), and the NBA's page inputs
    get the NHL's tests (E29, E30, E31).
16. Docs: the stale comments and docstrings, SECURITY.md (21 dispatchable
    workflows, Booth's `pull-requests: write`, the OAuth token, the PAT's
    expiry), and a README for three sports (E13, E19, E33).
17. Meta and share descriptions name three sports; every page's
    `theme-color` matches the background, `#0B0D10` (U9).
18. One product in the words: titles, sub-lines, the wordmark as a link,
    one sidebar foot with ET stamps, the theme icon, Correct/Missed,
    goalie pills at the type floor, the home footnote and footer, one
    sentence on who runs the site, the GitHub link in "Can I check the
    picks?", the NBA's record tile on the home strip (U5's link, U6-U8,
    U10, U12-U14, U16-U18, U20, U21, U26, U28, U30). A few PRs, not one.
19. The home, NHL and NBA builds strip CSS comments as the NFL's does
    (U45).
20. Lock proof for the NHL and NBA, and graded rows keep their saved time
    (U41).
21. The NHL's "How sure, and how often right" table on the NBA (U39).
22. A share block per sport (U42).
23. Hash routes on the NHL and NBA pages, then home links to their
    Methodology (U22, U37).
24. One `safe_json`, one `font_faces_css`, one `escapeHtml` (E17).
25. mypy over `src/core`, `src/site`, `src/sports/nhl`, `src/sports/nba`,
    measured before it gates (E18).
26. Disclosures on the pages: the NBA drift baseline's known lean, both
    tuned parameters at the edge of their grids, neutral-site games
    keeping the home edge in hockey and basketball (E20, E21, E23).
27. Pick records carry `data_provenance` and `training_through`, and
    `game_type` in all three sports (E26).
28. Dispatchable NHL and NBA backtest re-runs that diff against the
    committed results and never commit (E27).
29. The audit-log collector commits only when the log changed (E34).

Waiting on Mark: E10 (reopen the dispatch-input decision on the PAT's new
fact), E15 (delete the unused sport contract or build it), the home
additions inside option A (U1, U2's compact strip, U3), the switcher
(U11), the NFL board on a phone (U29, U32-U34, U36), the board's spare
column (U27), shared font files (U44), and the measurement registrations
drafted for E22, E24, E25 and E28. Deferred: E16 (after opening night),
U31, U43, U46, U47. Declined with reasons in the log: E9, U19, U35, U40,
U48.
