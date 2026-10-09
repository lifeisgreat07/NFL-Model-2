# The road from 76 to about 95

Part of the stage history; the index is `docs/stage-history.md`. Moved verbatim from
that file on 2026-10-06 (Stage 49 item 24).

## Stages 11 to 22: the road from 76 to about 95 (planned 2026-09-26)

Planned with Mark on 2026-09-26 from `docs/design/UX-REVIEW-2026-09-26.md`, which
scores the dashboard 76/100 and says why, labels every proposal from his audit
prompt, and lists what not to build. Read it before starting any of these. The
order is by dependency: integrity first, then the safety net, then what the big
redesigns rest on (numbers, fresher data, team news), then the redesigns, then
testing with people, then polish. One item, one PR, wait for Booth, as always.

The estimates are the review's own rubric, not a measurement: 76 today, about 95
after Stage 21. Stage 21 re-runs `dashboard-design-audit` so the claim rests on
a command. 100 is not a target: the last points need a backend, and the static
single-file site is part of what this project demonstrates.

### Stage 11 - Integrity and access  <- COMPLETE (2026-09-26, #110 to #115)

All six items shipped one PR at a time, each merged on Booth's SAFE TO MERGE with
no discrepancies. Decisions worth keeping, so they are not re-litigated:

- **The kickoff lock (#110) is honesty, not security.** Pick times live in the
  visitor's browser (`nfl_pickem_pick_times`). A pick counts only if its time is
  before kickoff; untimed picks are kept, shown and not counted, and the page says
  how many it left out. The kickoff instant is `Date.UTC` from the Eastern fields
  plus the US daylight-saving rule -- never a `Date` parsed from the Eastern
  string -- and `tests/test_my_picks_kickoff_lock.py` runs it under two TZ values.
  **An untimed pick on a game not yet kicked off is stamped "now" on render**
  (it is in storage now, so it was made by now); a locked game is never stamped.
  **Shared weeks are not scored**: a link carries no times. Carrying times in
  share links was left out on purpose (a time in a URL is as editable).
- **`tallyMyPicks` is the only tally** behind the badge, streak, trend line and
  scoreboard race. Four hand loops were four places to forget the lock.
- **`.btn-link` has `min-height:24px` (#112)**, on the component, not one control.
- **"Pick'em rank n (k points)" (#113)** via `pickemRankLabel`; the PDF's
  `Rank`/`Pts` headers were left for Stage 14, which owns every `pt`/`pts`.
- **The footer is `provenance_line()` in `src/sports/nfl/generate_dashboard.py` (#115)**,
  from `MODEL_VERSION` and `min(TRAIN_SEASONS)`. Its "Updated ... UTC" half
  moved to the Week Board header in Stage 13 (#125, `updated_line()`), because
  the sidebar is hidden below 1080px and no phone ever saw it.

The original plan, kept for the reasoning:
The two places the page can currently say something untrue or unreachable, then
the small wording fixes. **First task: lock My Picks at kickoff** -- buttons
disabled from `gameday` + `gametime_et`, each pick stored with the time it was
made, Season Accuracy counting only picks made before kickoff and saying how
many it left out (legacy picks with no time are kept, marked unverified, not
counted). Measured 2026-09-26: writing every graded winner into
`nfl_pickem_my_picks` shows "My picks 100.0%, 32 of 32". Then: the closed
`#bnav-more-sheet` made `inert` (at 1440 px the 19th Tab press lands on its
invisible "Team Deep-Dive" button); `+ view context` toggles at least 24 px tall
(13 px at 390); "Confidence #n · k pts" renamed "Pick'em rank n (k points)";
"Illustrative margin" retired (margin modelling was REJECTED, and its `~` reads
as a minus); the sidebar footer's build internals ("2026_week3", "week(s)
saved") replaced by one plain provenance line generated from config.

### Stage 12 - Self-hosted assets and browser checks in CI  <- COMPLETE (2026-09-26, #116 to #122)

Seven PRs, each merged on a Booth SAFE TO MERGE with no discrepancies (#120 only
after two DO NOT MERGE audits of its description, first for not saying its own
check was red, then for a future-tense sentence -- see the last bullet): the font
(#116), 24px standalone links (#117), and the Playwright job (#120) -- plus four
page defects the checker found, each fixed in its own PR before the job could go
green: focus on a 1x1 hidden week select (#118) and 21-22px reliability points
(#119) found from the sandbox; sideways-scrolling boxes with no keyboard way in
(#121) and text dimmed with opacity (#122) found by axe on #120's first CI run.
Decisions worth keeping:

- **The checker proves itself first.** `--self-test` runs every rule against a
  fixture built to break it; the workflow fails if any rule cannot fail.
- **axe runs only in CI**: the sandbox proxy refuses axe-core, so a sandbox run
  of `check_page.py` is every rule except axe. Say so in any PR note. Booth CAN
  install both, and did, reproducing CI node-for-node.
- **A box that scrolls sideways is a named Tab stop only while it scrolls and
  only if it holds no control of its own** (`setScrollStop`, #121);
  `data-scroll-stop` records what was added so fitting removes exactly that.
- **No text is dimmed with opacity** (#122). `tests/test_no_dimmed_text.py`
  lists every partial opacity with why it holds no text. axe cannot judge text
  on the sidebar's gradient ("needs review", not a violation), so a token-level
  contrast sweep found two failures axe never reported.
- **A future-tense sentence about a PR that does not exist yet is a Booth
  DISCREPANCY** (#120's second audit): "is fixed in a second PR" was read as a
  present claim. Write "will be fixed" or wait until it exists.

**Decided with Mark 2026-09-26, before starting:** self-host FOUR font files only
-- Plus Jakarta Sans latin and latin-ext, the variable normal face (400-800) and
italic 500, 73,692 bytes from fonts.gstatic.com, SIL Open Font License. The
vietnamese and cyrillic-ext subsets are dropped. **The 32 team logos are NOT
self-hosted**: they are NFL trademarks and copying them into a public repo would
redistribute them. They stay hot-linked from ESPN, the page already falls back to
the abbreviation, and the CI job proves every card and pick button still works
with ESPN blocked. Three PRs: the font (inlined into the built page at build
time, so the site stays one file); 24px targets for the six text links on
"Checking the AI's work" (16px in the fallback face, 18px with the webfont,
measured 2026-09-26); then the Playwright job.

The original plan, kept for the reasoning:
The safety net goes in before the big UI work. Self-host the Plus Jakarta Sans
files and the 32 team logos (today the page depends on Google and ESPN at load,
and a render without the font can find nothing -- see the webfont traps). Then
a CI job driving Playwright on the built page at 360, 390, 768, 1024, 1280 and
1440: no horizontal overflow, no focusable element off-screen or hidden, touch
targets at least 24 px, axe-core with no serious or critical violations on all
nine pages, and a byte budget on the built HTML. Font loading is asserted from
measured widths, never `document.fonts.check()`. No pixel-diff screenshots.

### Stage 13 - Landing and links  <- COMPLETE (2026-09-26, #123 to #127)

Five PRs, each merged on Booth's SAFE TO MERGE with no discrepancies: the Week
Board opens first (#123); the orientation banner is three lines plus a native
"How to read this" disclosure, placed after the second card on a phone by
`placeOrientation()` (#124); "Updated" moved to the Week Board header (#125);
hash routes `#board[/week]`, `#team/XX`, `#modellab/<slug>` and one per page,
pushState on a page change and replaceState on a week or team change, share
links never read as routes (#126); a meta description and a static Open Graph
card, `assets/og/og-card.png`, copied to the site root by deploy-pages (#127;
Mark approved the card 2026-09-26). Team rows and week rows do not link to
the routes yet.

The Week Board becomes the default page and first in both navs (the bottom nav
becomes Board, Ratings, Picks, Accuracy, More). The orientation banner becomes
three lines with a "How to read this" link, dismissed per device, and on a
phone sits after the first games (measured: the first card starts at 914 px on
an 844 px screen). An "Updated" time moves into the Week Board header. Hash
routes for pages, weeks, teams and experiments, coexisting with `#picks=`
share links; the routing is new code (STAGE8-DESIGN.md calls `openTeam` and
`openWeek` stubs "already wired", but neither exists in the template -- correct
that sentence in the same PR). A meta description and one static Open Graph
image.

### Stage 14 - One meaning per number  <- COMPLETE (2026-09-26, #128 to #130)

#130 restated Methodology's two accuracy-led comparisons (B vs A, A vs the
market) on log loss and Brier with Model Lab's intervals, every figure held to
the page's own tables by `tests/test_scoring_rule_claims.py`. Model Lab's 46
hand-written rows were left for Stage 18, which regenerates them with the
scoring rule leading (Mark told of the scope 2026-09-26).

Formatter functions (`fmtProb`, `fmtPP`, `fmtRating`, `fmtInterval`,
`fmtPoints`) with a test banning bare `pt`/`pts` outside pick'em points. Net
rating shown as points per 100 plays (`+14.9`, not `+0.149`), a display-only
rescaling held to the data by a test. **Decided by Mark 2026-09-26 from a
rendered side-by-side: per 100 plays** (BUF +14.9, offense +15.4, SOS +5.1,
bar scale ±17) on Power Ratings' net, offense, defense and SOS. Accuracy-led claims in Model
Lab and Methodology restated on log loss and Brier.

**Progress (2026-09-26):** #128 (accuracy gaps as "pp", spreads via `fmtPoints`,
a test banning bare pt/pts) and #129 (per 100 plays via `fmtRating`, on Power
Ratings and Team Deep-Dive; the card's `whyRow` figures deliberately left per
play) merged. Only formatters with a caller were added; `fmtProb`, `fmtPP` and
`fmtInterval` wait for one. **Lesson from #129's first audit (a DISCREPANCY):**
"these case files are not affected, so they were not run" is a claim, and it
was wrong -- one anchored on an edited line. Run the cases that name a test you
edited, or do not say they are unaffected.

### Stage 15 - Weekend refresh and game status  <- COMPLETE (2026-09-27, #132 to #137; display is Stage 17)

**Shipped, each merged on Booth's SAFE TO MERGE with no discrepancies:** #132
the nfl.com probe (a runner reads it, 16/16 each of weeks 1-4); #133 the
weekend refresh (`src/sports/nfl/weekend_refresh.py`, snapshots to a status folder under
data, Friday 05:17, Sunday 21:47 and Monday 05:37 UTC); #134 the card status
line under the kickoff; #135 the TV checks (`src/sports/nfl/tv_channels.py`,
`data/nfl/tv/exceptions.json`); #136 TV read with `--pending` by both the weekly
update and the weekend refresh, continue-on-error in both; #137 the canary
checks next week's nfl.com page. Decisions worth keeping:

- **One network per game, the first nfl.com lists.** Measured against ESPN's
  own scoreboard from the local Windows machine, weeks 1-4: the first-listed network matched all
  64 games, while the full list claimed an ABC simulcast for week 4's Falcons
  at Saints that ABC's own schedule does not carry. The rest is kept as
  `listed`, never shown.
- **Alternate and Spanish-language feeds** (Telemundo, Universo, ESPN
  Deportes, ESPN2, FOX Deportes) are known and silently not shown; any other
  unlisted name is reported. **A slot no rule covers needs a sourced
  exception**, the same as a rule break. Thanksgiving, Black Friday,
  Christmas and Saturday games need entries before their weeks or they are
  held back and reported (a warning, never an error).
- **Canary: a changed feed is an error, a missing kickoff or network a
  warning** -- week 18's kickoffs are not set until late December.
- **A graded card says nothing from a stale snapshot.** Monday morning's
  snapshot still calls Monday night's game upcoming when Tuesday grades it.
- The Stage 17 display still owes the plan's item 7: the network name only,
  and one line saying Sunday-afternoon CBS and FOX games are regional (the
  data carries `territory`).

**ESPN is REFUSED from GitHub's runners (read 2026-09-27; #131 closed
unmerged).** #131's probe got `HTTP Error 403: Forbidden` on all four weeks
in under a second on the Actions runner; Booth reproduced the 403 from its
own environment with a browser-style User-Agent; the local Windows machine gets 200 and 16/16
complete. So ESPN blocks datacenter addresses, not the request. **Do not
route around it** (headers, proxies, another ESPN host): Mark ruled that out.
Options put to Mark 2026-09-27: A a sourced season file cross-checked from
the local Windows machine, B probe another automatic source, C drop the channel, D a
self-hosted runner (not recommended: a public repo's PRs could run code on
the local Windows machine). **Mark chose B**, and #131 was closed rather than merged because
a probe of a feed nothing will use is a check that is red by design.
**The candidate is the league's own page**,
`www.nfl.com/schedules/2026/by-week/week-N`. Its server-rendered HTML embeds
structured game data (a Next.js payload, not a documented API): per game,
`broadcastInfo.homeNetworkChannels`, a `territory` of NATIONAL or REGIONAL,
the kickoff in UTC, both teams, and `externalIds` carrying `gsis` and
`elias` ids. **The join key is `elias` = nflverse `old_game_id`**: equal on
all 32 games of weeks 1 and 4 (`nflreadpy.load_schedules([2026])` on
the local Windows machine, 2026-09-27). NOT `gsis`: nflverse leaves it blank until a game is
played (NaN on every week-4 row). Fetched on the local Windows machine and parsed 2026-09-27: 16 of 16 games
carrying a network, for each of weeks 1 and 4. Sports Media Watch's hand-kept NFL TV schedule, read
the same day, names the same first network for all 16 week-4 games (it
omits ABC's Monday simulcast, which nfl.com lists). **Trap:** nfl.com's `ways-to-watch/by-week/week-4` page
served a different slate (apparently last season's) on the same day, so the
URL is part of the check, not a detail. Whether Actions can reach nfl.com is
the next probe's question; nothing depends on it until that is answered.
The TV plan below still stands with the source swapped, subject to that
answer.

A light scheduled run between the Thursday lock and Tuesday's grading that
updates game status, final scores and the latest line, and never touches saved
picks. **Two writers of picks is two ways to break a lock** (2026-09-24), so it
writes only status, scores and lines, and a test holds it off `predictions/`.
Cards gain a status: upcoming, played and awaiting Tuesday's grading, or final
with the score. It also gives Stage 16 its refresh cadence.

**TV channel per game (added 2026-09-26).** nflverse's schedule has no broadcast
column (all 46 checked). ESPN's public scoreboard does, per game
(`site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?seasontype=2&week=N&dates=2026`,
`competitions[0].broadcasts[].names`), and it was reachable from the local Windows machine on
2026-09-26 with all 16 week-4 games carrying a network. It is undocumented, so
accuracy cannot be assumed; it has to be earned and then watched. Nothing can
guarantee a third party is right, so the guarantee this stage makes is narrower
and checkable: **the page never shows a channel that failed a check, and every
channel it shows can be traced to where and when it was read.**

1. **Exact join, then a cross-check.** Match on nflverse's `espn` game id, never on
   team names or dates, and then require ESPN's two teams and kickoff to agree with
   the nflverse row. Any disagreement drops that game's channel and is reported.
2. **A closed list of networks.** CBS, FOX, NBC, ESPN, ABC, NFL Network, Prime
   Video, Netflix, YouTube, Peacock, ESPN+. A name outside it is not shown until a
   person adds it to the list in a reviewed PR.
3. **Slot rules as warnings.** Thursday night is normally Prime Video, Sunday night
   NBC, Monday night ESPN or ABC, Sunday afternoon CBS or FOX. A game breaking its
   slot's rule is shown only if it is on a list of known exceptions (holiday games,
   international games, streaming exclusives) and is otherwise held back and
   reported. The exceptions list is data with a source per entry.
4. **Provenance.** Each saved channel carries the URL it came from and the time it
   was read. Every fetch is kept, so a change between fetches (a flexed Sunday night
   game) is visible in the weekly summary as "changed from X to Y", never a silent
   overwrite.
5. **Measured before it ships.** Weeks 1 to 4 of 2026 compared, game by game,
   with the league's own published schedule, and the result written into the PR:
   how many matched, and what each mismatch was. It ships only with zero unexplained
   mismatches.
6. **Watched after it ships.** The nightly canary fetches the feed and checks its
   shape; a missing field or an empty week opens "NFL: Nightly canary failing", like any
   other upstream break. A missing or failed channel is a WARNING, never an error:
   no pick waits on a TV listing.
7. **Honest display.** The card shows the network name and nothing it cannot back:
   Sunday afternoon CBS and FOX games are regional, and the feed does not say where,
   so one line on the page says so rather than implying every viewer gets that game.
   Stage 17 puts it on the card; before then it is data only.

Tests, each with a mutation case: a mismatched team or kickoff drops the channel;
an unlisted network is held back; a slot-rule break without an exception is held
back; a changed channel is reported as a change; the refresh never writes
`predictions/`. The reachability of the feed from GitHub's runners is the first
thing checked, before any code is written.

### Stage 16 - Team news  <- COMPLETE (2026-09-27, #138 to #140; the card line is built in Stage 17)

**Shipped:** #138 `src/sports/nfl/team_news.py` writes one file per locked, ungraded week
(starters Out or Doubtful by name, Questionable as a count, the pick's own
quarterback); #139 both scheduled workflows run it with `--pending`,
continue-on-error; #140 Team Deep-Dive's "This week" block, at most five
sourced, dated lines, gone once the week is graded. When the pick's
quarterback is himself listed Out or Doubtful, that replaces the QB line.


Mark wants this clear and concise, not information overload. **The data
exists:** checked 2026-09-26, `nflreadpy.load_injuries` carries 2026 weeks 1-3
for all 32 teams with `report_status` Out / Doubtful / Questionable, and
`load_depth_charts` and `load_rosters_weekly` carry 2026 too. (Injury data as a
MODEL feature stays closed on value; this is display, which Stage 7.5 already
said is a separate question.) Two tiers:

- **Automated, from nflverse:** starters (from the depth chart) listed Out or
  Doubtful on the official report, and the announced starting quarterback with
  a change flagged. Questionable players are a count, not a list.
- **Sourced by hand, rarely:** coach firings and trades, through the weekly
  QB-research routine's PR with a source link per item. That routine was made
  through the HTTP API, so only Mark can edit its prompt.

Display rules, to keep it short: the Week Board card gets at most one line and
only when a starter on either side is Out or Doubtful, or the quarterback
changed; Team Deep-Dive gets a "This week" block of at most five items, each
dated with its source. Items expire with the week. The plain-language guard
applies. Data file first (with a hypothesis about what a reader needs from it
written in the PR), then Team Deep-Dive, then the card line in Stage 17.

### Stage 17 - Week Board card v2  <- COMPLETE (2026-09-28, #146, #148 to #153)

**Decided 2026-09-27 from rendered side-by-sides: "B refined".** Keep the
team-colour bar split by Model B, team names at its ends; one probability line
beneath on the same scale, marked at 50%; Model A circle, Model B square,
Market triangle; markers closer than 7 points take fixed lanes (market above,
B on the line, A below; 7 is measured: a 12px marker is 6.8 points of the
narrowest 176px line); key ordered B, Market, A; a disagreement line only when
Model A picks the other team; one screen-reader sentence. Mark noted he had
grown used to the old card and accepted the new one as more readable.
**Shipped 2026-09-28:** #148 the channel pill in the kickoff line, one
regional line above the grid (only when a shown card carries a REGIONAL
channel), the quarterbacks the pick was made with ("(assumed: last game's
starter)" on a `last_game` side), and one labelled team-news line (the pick's
own QB on the report first, then "new QB", then starters out or doubtful by
name up to two and counted beyond). The channel and the news leave the card
once its game is final or graded; the quarterbacks stay, because they are part
of the pick. #149 "Model A's reasoning" above the why sentence, class
`.why-by` (NOT `.why-label`, which the numbers panel's rows already wear).
Weeks 1 to 3 were saved under v2.4, so week 4 is the first card with names.
#150 `[` / `]` step weeks on desktop; #151 team logos back on the matchup
header (20px); #152 `.card-status` names `--text` and
`tests/test_css_tokens_defined.py` guards every `var(--x)`; #153 the retired
rows' CSS removed. "No HIGH/LOW words" needed nothing: the card had none.


One decision per card. A single probability line from away team to home team
with Model A ●, Model B ■ and Market ▲ (the shapes Season Accuracy already
uses); Model B's number as the headline, for the team it favours; the market
as a probability, not only a spread; the announced quarterbacks named (the
saved predictions gain the resolved starter names -- a data-output change,
reviewed as production code); Stage 15's status and TV channel; Stage 16's one news
line; no HIGH/LOW confidence words. **Open decision for Mark:** the team-colour split
bars kept on 2026-09-21 -- keep them as the line's end caps, or keep the bars
and put the line beneath -- chosen from rendered side-by-sides in both themes
and under protan and deutan simulation, as that decision was. `[` and `]` step
weeks on desktop.

### Stage 18 - Model Lab rebuilt from the experiment records  <- COMPLETE (2026-09-28, #141 to #143, #154 to #156)

**Shipped:** #141 `src/sports/nfl/model_lab.py` over `experiments/nfl/stage*/results/` plus
the 46 old rows moved once, verbatim, to `experiments/nfl/legacy/rows.json` (frozen
by sha256 in `tests/test_model_lab.py`); #142 the table rendered at build time
by `render_model_lab_rows` (tests that read Model Lab copy use
`tests/page_source.py`); #143 decision chips with counts. Mappings onto the
five decisions are my calls, listed in `experiments/nfl/legacy/README.md`, for
Mark to overrule. #154 each registered result opens with `interval_glyph()`,
its interval drawn against zero (`&minus;` in the text equivalent: the
generator writes `index.html` without `encoding=`, and a literal U+2212 crashes
the build under cp1252). #155 the experiment log is cards below 768px (the
table first fits at about 651-655px; the figure depends on text rendering).
#156 the reliability diagram follows the experiment log; its explanation is
behind "How to read this" and the Brier definition behind "What these numbers
mean", while the bootstrap findings stay in view (they are results).


Generated from a data file, not 46 hand-written rows: Stage 5 and 6 read from
`experiments/nfl/*/results/`, the older rows moved in once, verbatim. Five
decisions as the project defines them plus a leakage flag (the page uses 11
labels today); filter chips with counts; the proper scoring rule and an
interval glyph first in each result; cards on a phone; the reliability diagram
below the experiments with "How to read this". Every figure held to its source
file by a test.

### Stage 19 - Team pages  <- COMPLETE (2026-09-28, #157 to #162)

**Shipped:** #157 Team Deep-Dive opens on Power Ratings' rank 1
(`teamDiveDefault()`), a `#team/` link still wins; #158 headings on its games
list (aria-hidden; each row names its numbers through `.visually-hidden`), and
phone rows put the result on the opponent's line; #159 the accuracy trend's
week labels and end-labels placed together by `spreadLabels()`; #160 "How
sure, and how right" on Season Accuracy; #161 Power Ratings' rank change and
biggest-moves line; #162 offense and defense beside net on Team Deep-Dive.

**Decisions, so they are not re-opened:**
- **Season Accuracy's score is log loss in plain words** (Mark): no exception
  to `tests/test_plain_language.py`; Methodology's glossary names the term.
  It is a block under the scoreboard, not a row in it, so the "picked the
  winner" verdict keeps one meaning. Absent below 50 graded games
  (`FORECAST_SCORE_MIN_GAMES`), paired over the games all three forecasts
  priced, probabilities clamped away from 0 and 1.
- **Power Ratings' arrow follows RANK** (Mark): places moved since the
  previous weekly update, from `previous_ranks()` over the season's live
  history. It refuses (shows nothing) with one week, a partial previous
  week, or a latest week that is not the ratings snapshot, and
  `test_the_committed_ratings_are_the_latest_history_week` holds that
  premise. `with_rank_change()` is a separate step because
  `tests/test_playoff_odds_column.py` reads the `build_teams_js` call as
  written.
- **Team Deep-Dive's offense and defense** ride on every timeline point;
  one note above the rows says net is offense minus defense and that for
  defense lower is better (Mark). On a phone the pair takes a second line
  and the bar gives up width so net stays on the first.

**Mark's page review, 2026-09-28 afternoon (#165 to #168), decided:**
- Week Board: logos at the two ends of Model B's bar, not the title (on a
  phone they stack above the abbreviation); no "picks graded on Tuesday";
  no "Pick'em rank N (M points)" line. The rank still drives the
  "most confident" sort.
- Methodology: a number column's header is right-aligned over it
  (`th.num`); `tests/test_table_alignment.py` checks every static table.
- Model Lab: every interval graph sits in one shared frame, zero centred,
  still on its own row's scale (Mark chose this over one shared scale);
  decision pills never break inside themselves.
- Team Deep-Dive: the team's 48px logo and full name head the page.
- TV channels show only while a game is unplayed, by design; week 4's appear
  after Thursday's lock run.
- README screenshots retaken 2026-09-28 with logos served locally.

### Stage 20 - Testing with real people

Five people -- a recruiter, a football fan, a data person, someone on a phone,
someone using a keyboard or screen reader -- each given the same three tasks
("who does the model like this week and how sure is it", "is the model any
good", "what did the team news say about your team"). Findings written into
`docs/design/` and turned into items, not acted on from memory. This is the only
step that turns the review's estimates into evidence, and it decides what
Stage 22 actually contains.

### Stage 21 - Once the season has data (not before week 5)

Gated by the calendar, not the order: derived insights, three kinds only (rank
moves of three or more places, model-vs-market gaps of ten points or more, games
both models put within five points of 50%), each generated from data with its
threshold in a test; sparklines on Power Ratings once four 2026 weeks exist;
then the `dashboard-design-audit` re-run, recorded against 15/40 and 28/40.

### Stage 22 - Beyond 95

Only what Stage 20 shows people notice: installable on a phone (manifest and a
service worker, offline); a manual screen-reader pass; a data-table alternative
for every chart; and the template split, only if the template passes 7,000
lines, with a build that inlines the parts back into one file and a test that
the built page is byte-identical before and after.
