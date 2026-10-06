# Stage history

Every stage section from 2 to 29, moved verbatim out of `CLAUDE.md` on
2026-09-29 (Stage 29, the CLAUDE.md split). Stage numbers are frozen: a
finished stage keeps its number and is recorded as finished here. The rules
still live in `CLAUDE.md` and the traps in `docs/traps.md`; what is next
lives in `docs/context.md`, never here.

This text was written when it was all one file. An "above" or "below" that
points at the methodology, "Findings that still constrain the work" or the
environment now means `CLAUDE.md`; one that points at a trap means
`docs/traps.md`.

## Moved from CLAUDE.md's "Current state" and "Start here"

**Stages 2, 3 and 7.5 are complete; Stage 1 was retired 2026-09-24. Stage 4 is complete (#100 to #107, 2026-09-24). Stage 7.6's repository half is done.
Stage 8, 8b and 8c are all complete; its decisions live in
`docs/design/STAGE8-DESIGN.md` and its specification is the pair of mocks
beside that file. Stage 9 is complete (#87, 2026-09-22; its button
component moved to Stage 10). Stage 10 is complete (#89 to #94, 2026-09-23). Stage 11
is complete (#110 to #115) and Stage 12 is complete (#116 to #122), both 2026-09-26. What is next is in
`docs/context.md`, which is rewritten every session and is the only place
current status belongs.**

Merged PRs are not listed here -- that list went stale at #57 while main reached #68.
Stage 7.5 has cut 14 pages to **9** — Playoff Odds
became a column on Power Ratings, Roadmap folded into Changelog (renamed What's
Changed), and How This Compares, Data Sources and the Glossary became parts of
Methodology. The plain-language guard is live and its allowlist is empty.
Stage 7.6's repository half is done: the README opens on a recruiter overview
and `tests/test_readme_accuracy.py` holds it to its own claims. Its browser
half — the repo description and topics — is still Mark's to do in the GitHub UI.

**Stage 3 closed with the finding it exists to prevent.**
`src/agents/collect_agent_log.py` was written and tested in Stage 3 and had **never
run** — nothing invoked it, its data file did not exist, and the generator had
never heard of it. Tested, mutation-covered, and dead. PR #47 connected it. Then
it ran and the page still said "The record has not been collected yet", because
a commit pushed by one workflow's `GITHUB_TOKEN` cannot trigger another; #48
fixed that with a `workflow_run` trigger. Two links of the same chain, each one
a step that ran correctly and had nothing downstream consuming it. The record is
live now, in `data/agent_log.json`. **Its `summary` block is the count — do not
copy those figures into prose here.** They grow with every audit, and the ones
this paragraph used to carry (45 audits, 167 claims, 11 discrepancies) were
understating the real totals by a third within a day.

**Stage 8 is done** — design system, colour tokens and motion all merged, and
Stage 9 is under way. This paragraph said "the next thing is Stage 8, and it is
blocked on Mark naming a visual reference" for a day after that stopped being
true. **What is next is in `docs/context.md`, never here.** The Stage 8 section
below is kept for the reasoning, not as a to-do.

## Stages 2 to 7.6

### Stage 2 - Deferred UX & repo hygiene  <- COMPLETE (2026-09-06)

Shipped as PRs #21-#24. See "Findings that still constrain the work" above; the four
corrections it produced are worth reading before starting anything that
assumes an audit finding is accurate.

### Stage 3 - Agent development  <- COMPLETE

**Built and merged:** Scout pre-flight, which checks a PR description against
reality before it opens (`src/agents/scout_preflight.py`, #26). A committed mutation
corpus, so mutation tables are a command rather than a throwaway script
(`tests/mutation/`, #27). A test that every regenerating workflow prunes build
churn (#28). Booth reports that record the head SHA and body read-time, and a
past-tense rule for claims about a description (#29). An `edited` trigger so a
rewritten description is re-audited at all (#30) -- demonstrated live on PR
#34 on 2026-09-07: editing the description with no manual dispatch fired a
second audit on its own. #30 shipped on a mutation test and an argument
because Booth structurally cannot audit its own workflow file, so that
live run is the evidence it could not produce for itself. A machine-readable
`booth-verdict` block plus the parser that reads it (`src/agents/booth_verdict.py`,
#31). The regression-fixture format and its integrity checks (#32).

**Two Booth defects were found and fixed on 2026-09-07**, both invisible to any
test because they concern how a report is read rather than what it checks. It
never re-audited a description-only edit, so a body could be rewritten after
its audit while the audit comment went on looking current. And it reported a
snapshot in the present tense, asserting what "a reviewer sees right now" about
text already replaced. Fixed in #30 and #29 respectively.

**Remaining, in the order agreed on 2026-09-07:**

1. **The fixture runner — BUILT** (`src/agents/booth_fixture_runner.py`).
   `assemble` builds a throwaway git repo from a fixture's `base/` and `head/`
   as two real commits, because Booth's procedure runs git commands and a
   patch file could not answer them. `prompt` renders the instructions.
   `record` parses the verdict block, checks it against the fixture's declared
   expectation, and writes `baseline.json` — including when Booth FAILED,
   since that is the most important result the suite can produce. `check`
   re-derives the answer from the stored verdict rather than trusting the
   stored flag, so an edited expectation stops a recorded pass from counting.
   The loop is complete manually today: assemble, run the prompt in a fresh
   session, record the report.
   DONE: `.github/workflows/booth-regression.yml` invokes the real action on
   `workflow_dispatch`, one fixture per dispatch. It landed in `79d5912`,
   fourteen minutes after the sentence saying it was still to do -- which is
   why this block is dated rather than trusted. Booth runs on subscription auth, so it costs no
   money — but it does cost usage, so never spend an audit to learn something
   a committed baseline already records.
2. **The agent decision log.** Listed here as agent work, but it is the item
   that renders. Right now a visitor sees no evidence that Scout, Booth, the
   mutation corpus or the fixture suite exist at all. It converts everything
   invisible into the thing a hiring manager actually looks at, and Booth's
   cost and latency numbers ride along nearly free.
   **It is not a new page.** It merges into the existing AI Reliability page,
   which Stage 7.5 renames in plain English and rebuilds — that page is already
   the agent story, told as three hand-written incidents frozen in time. Feed
   it from Booth's `booth-verdict` blocks so it stops being maintained by hand.
   Build the log here; do the rename and merge in 7.5.

**Then leave Stage 3.** The remaining items are deliberately parked, not
forgotten: the other five regression fixtures (one proves the mechanism; five
more is polish), the inter-agent disagreement protocol, the "Archivist" role,
and migrating the remaining ad-hoc mutations into the corpus. The
prompt-injection resistance test is the one worth returning to — it is a
recognisable AI-safety competency and cheap as a single focused PR — but it
does not belong ahead of the dashboard.

The reason for stopping: seven PRs on 2026-09-07 all landed on agent
infrastructure, and the dashboard has not been touched since Stage 2. Nothing
remaining in this stage moves the thing a visitor sees.

### Stage 4 - Automation & monitoring  <- COMPLETE (2026-09-24)

All nine items shipped the same evening, one PR at a time, each merged only
after Booth said SAFE TO MERGE with no discrepancies (Mark allowed Scout to
merge on that condition for this run): #100 data-quality checks, #101 Booth
alerts, #102 nightly canary and schema snapshot, #103 build-output smoke
check, #104 drift to an issue, #105 weekly summary and failure alert, #106
reproducibility audit and leak-free tests, #107 play-by-play cache. Which
file does what is in `docs/architecture.md`; this section keeps the
decisions, so they are not re-litigated.

- **Every alert is a GitHub issue, one per problem**, matched on exact title
  among OPEN issues (`src/pipeline/alerts.py`). Closing an issue is how a person says
  "handled"; the next failure opens a fresh one. Titles in use: "Booth audit
  failed: PR #N", "Nightly canary failing", "Model drift detected", "Weekly
  update failed".
- **Booth alerts are their own workflow** (`booth-alert.yml`, `workflow_run`
  on "Booth PR audit"), because the Claude Code action will not run on a PR
  whose `booth-pr-audit.yml` differs from main's. `cancelled` raises nothing:
  it is a newer push superseding an older audit.
- **Data-quality ERRORs stop the weekly run, so they are kept to what would
  corrupt a pick.** The 272-game count is a WARNING (Mark, 2026-09-24): a
  dry run found 2022 lists 271, the cancelled Buffalo-Cincinnati game, so an
  ERROR would have stopped every run of a season shaped like that. The
  latest completed week missing play-by-play, and an unpublished schedule,
  are warnings for the same reason.
- **Drift opens an issue and never fails the run.** The check is on
  accuracy, which cannot carry a result here, so the issue says to compare
  log loss and Brier before acting.
- **The weekly summary reads only what the run left** (git status, the log,
  drift-report.txt), so it cannot disagree with the run. The lock step's
  `shell: bash` is load-bearing: it is what gives `| tee` pipefail.
- **The schema snapshot is column names only**; dtypes vary with the pandas
  version. Refresh it on purpose with `python -m src.pipeline.schema_check --season
  <year> --update` after looking at what changed.
- **The play-by-play cache is the canary's alone.** The run that makes picks
  always fetches fresh; a test holds that. It was the lowest-value item and
  was kept because Mark asked for all nine.
- **The reproducibility audit re-runs by hand or from Run backtest**, never
  in the suite (it needs nflverse). Its committed record is tied to
  `data/calibration.json`, so regenerating calibration means re-running it.

Not yet seen live, because each needs a real event: the Booth alert (a
failed audit), the canary's alert (a failed night), the drift issue (a
flag), the weekly summary (the next weekly run) and its failure alert.
`docs/context.md` lists what to check and when.

### Stage 5 - Model depth, real hypotheses only

Residual analysis FIRST, since it tells you which of the rest are worth
attempting. Then market-implied probability calibration as a Model B feature;
per-team learned home-field advantage; rest and travel; weather and wind for
outdoor games; situational splits; multi-season QB priors; injury-adjusted QB
ratings, indefinitely parked with the injury data closed; learned blend weight
between Models A and B - if an ensemble doesn't beat both, that's a publishable
REJECT.

### Stage 6 - New data sources  <- COMPLETE (2026-09-28, #108, #163, #164; line movement waits for season end)

Next Gen Stats via nflreadpy, the most promising untapped source already in the
stack; participation/personnel grouping; referee crew assignments, cheap and
testable; multi-book line dispersion, gated on the line
accumulation below rather than a new build. Each item needs a stated hypothesis BEFORE the data is
pulled, or it is fishing.

**Next Gen Stats: answered 2026-09-26, nothing accepted.** Registered in
`experiments/stage6/registry.json` (#108) before any of it was loaded, with one
budget of five confirmatory slots (99% intervals) for the whole of Stage 6. The
N1 screen FAILED: four passing numbers (completion over expected, time to throw,
aggressiveness, intended air yards) did not predict a quarterback's next game
beyond his recent EPA plus play-by-play CPOE, so N2 and N3 were never run and no
slot was spent. `experiments/stage6/README.md` has the figures. Do not re-open it
without a new registration and a reason the answer would differ.

**Referees: answered 2026-09-28, nothing accepted.** Registered in #163 before
any referee or penalty value was read (R1 screen, R2 feature, A2 lock check;
personnel groupings P1 DEFERRED with the reason written down). R1 FAILED in
#164: across the 12 referees with 40+ games in 2016-2020 and 24+ in 2021-2023,
the weighted correlation of a referee's home/away penalty-yard gap between the
two periods is +0.18, 95% interval -0.28 to +0.65. R2 and A2 were never run; no
slot was spent. The first R1 run was discarded for a join bug and disclosed
(the schedule's OAK/SD are play-by-play's LV/LAC; home and away now come from
play-by-play). Stage 6 spent none of its five slots.

**When the rest of Stage 6 runs (decided 2026-09-26):** after Stage 18, so its answers
land in the generated Model Lab instead of being hand-copied into it. Line movement
still waits for the end of the 2026 regular season.

**Line movement and the closing-line backtest (moved here when Stage 1 was
retired, 2026-09-24).** Line snapshots accumulate on every weekly run and are
confirmed working. Do not test anything on them before the 2026 regular
season ends: that is the trigger for the first line-movement test and the
closing-line backtest, each with its hypothesis written down first. A test on
a few weeks of snapshots is the small-sample result this project refuses to
publish.

**Closed sources -- do not re-check.** Stage 1 used to re-check these every
session; it was retired on 2026-09-24 because none of them has a future here.
Injury/roster data as a model feature: closed on value, not availability
(showing team news on a page is a separate question, see Stage 7). Checked 2026-09-26: `nflreadpy.load_injuries` now
carries 2026 (weeks 1-3, all 32 teams), so Stage 16's team-news display can be
automated. ESPN QBR:
abandoned upstream, ends at 2023 (re-confirmed 2026-09-24: no 2024 or 2025
rows, and nflreadpy has no loader). Public betting percentages: no free
source, so reverse line movement is out too. An ensemble needs a second
independently useful model, and Stage 5 accepted none.

### Stage 7 - Portfolio polish

**Where the write-ups live, decided with Mark 2026-09-24: both, one source.**
The full text is in `docs/case-studies/` (and `docs/lessons-learned.md`),
for a technical reader who can check every figure. "Checking the AI's
work" carries a short plain card for each that links to it. Two full copies
would drift, which is the failure this repository keeps paying for, and
`tests/test_case_studies.py` holds cards and files to each other. A
figure in a case study is either measured (held to its data file) or
quoted from a commit (held to that commit). #96 and #97 shipped the first
two; the rest is one PR (#98) because Mark could not merge between items.

README rewrite for a cold technical reader; architecture diagram; case study of
the QB rating leak; public "lessons learned" page; write-up of the Booth
regression suite and injection test. Add a case study of Booth's first audit -
a verifier that caught a flaw in its own harness and an unreproduced claim on
the live dashboard is a better story than the feature it was auditing. Add a
second: the Stage 2 corrections, where four of seven queued items turned out to
be misdiagnosed, including a page that had never worked.

NOTE ON ORDER: this sits before the visual stages by explicit instruction, but
anything in it that shows the dashboard - screenshots, the architecture
diagram's UI layer, the lessons-learned page's framing - will be redone once
Stages 8-10 land. The text-only items (README, QB-leak case study, Booth case
study) are safe to do here; hold the visual ones.

### Stage 7.5 - Content & structure pass  <- BEFORE the visual overhaul

A decimal, not a renumber: stage numbers are frozen, and this runs between 7
and 8. It exists because doing it afterwards means designing pages we are
about to delete and sizing token scales against markup that will not survive.

**Why it comes first.** The dashboard has 14 pages. Stage 10 needs a shared
page-header across all of them, a table system, empty/error/loading states on
every page, and a mobile pass — so each page removed is removed from four
workstreams at once. Stage 8's audit counts (31 ad-hoc spacing values, 21 font
sizes, 8 radius values) were measured against current markup; building scales
to fit pages that are about to go means sizing the system against the wrong
target.

**The reader is a 12-year-old, not a data scientist.** This is the governing
constraint for the whole pass, from the user directly. The dashboard currently
reads as AI slop in places and overwhelms rather than informs. Jargon is
allowed only where someone has opted into depth.

**Target structure, 14 pages down to 9:**

- What the model says — Boards, My Picks, Power Ratings, Team Deep Dive
- Track record — Season Accuracy
- How it works — Methodology (absorbs How This Compares, Data Sources, and the
  Glossary as a closing section), Model Lab
- How this was built — the AI Reliability material plus the live agent decision
  log, renamed in plain English
- Changelog — absorbing the "what's next" half of Roadmap

**Deletions and merges, with what was checked:**

- **Playoff Odds — DONE (PR #40).** The page is gone; the number lives on as a
  sortable column on Power Ratings. The page had been 585 characters of visible
  text and 953 of markup (measured by extracting `<section[^>]*id="page-playoffs".*?</section>`
  and stripping tags), nearly all caveats. Its bar normalised to the leading
  team, so a 40% favourite rendered full-width and read as near-certainty; the
  bar was deleted rather than transplanted, which retires that queued Stage 10
  defect. The one non-obvious requirement: the odds are joined onto the team
  objects in `build_teams_js` in Python, because the table sorts by reading
  `a[sortKey]` off a team — a browser-side lookup would render in the cell and
  silently refuse to sort. The same PR fixed the `#` column, which had been the
  row's position in the current sort and started printing "#1" beside the
  ninth-rated team as soon as the new header made another sort worth clicking;
  it is now a power-rating rank computed in Python that travels with the team.
  Guarded by `tests/test_playoff_odds_column.py` and sixteen mutation cases.
- **Roadmap — DONE (PR #41), but NOT as planned.** The plan below was wrong and
  is kept as written so the correction is legible. The Roadmap is gone and its
  content is folded into Changelog, which is renamed **What's Changed** and now
  has three parts: the generated model versions, "What got built" (the 16 Done
  cards), and "What we tried that did not work" (the 7 rejections).
  **The premise failed on inspection.** The claim was that the Done list
  duplicated the Changelog. It did not: the Changelog is 7 *model* versions
  from `config.VERSION_HISTORY`; the Done list was 16 mostly-*product*
  milestones, and only ~3 overlap. Executing the plan literally would have
  destroyed the only record of the picks log, the calibration table, the
  deep-dive page and the nflreadpy migration — silently, with every test green,
  because nothing tested that the content existed.
  `tests/test_whats_changed_page.py` now asserts a floor on that record, and
  `test_those_milestones_really_are_absent_from_the_generated_changelog` guards
  the *reason*: if VERSION_HISTORY ever grows to cover product work, that test
  goes red and the hand-written cards genuinely can be deleted.
  Two dead links fell out of it, both found by the new nav guard rather than by
  reading: **the mobile bottom-nav still listed Playoff Odds**, shipped on main
  by PR #40 — that PR removed the sidebar button only — and it would have kept
  the Roadmap tab too. There are TWO navs. Also on the merge: the rejection
  cards had always worn `.status-done`, so "TESTED — REJECTED" was painted in
  the success green; they now use the neutral pill.
  ORIGINAL PLAN, PRESERVED — **Roadmap — delete, keeping only "what's next" and
  the DEFERRED/REJECTED entries**, folded into Changelog. Its "Done" list
  duplicates the Changelog,
  which is now generated from `config.VERSION_HISTORY` — two sources of truth
  for the same information. This also resolves the separate "remove 2025 Week
  10" item: that reference lives inside a Roadmap Done card about the nflreadpy
  migration, so one edit covers both.
- **How This Compares, Data Sources and Glossary — DONE (PR #43), merged into
  Methodology together.** 12 tabs → **9**, which is Stage 7.5's target. All
  content kept; the ATS finding survives and is asserted by a test.
  The premise check this time was about SIZE, not duplication: Methodology was
  already 10.7k visible characters and ten sections, and the three pages add
  7.8k more. Merging them flat would have traded three tabs for one page nobody
  finishes. So the page is now four `.method-part` blocks — How the model works,
  How this compares, Where the numbers come from, Words used on this page —
  each with a title and a one-line lead, behind a `.page-jump` row of anchor
  links. The ten original Methodology headings were demoted h3 → h4 so the
  parts are the only h3s and the hierarchy means something.
  ORIGINAL PLAN, PRESERVED — **How This Compares — merge into Methodology.** Do NOT delete the content.
  The page exists because it is the question a sceptical reader asks first, and
  it carries the ATS finding: 51.61%, CI contains 50%, below break-even. That
  honest negative is the project's credibility. It does not need its own tab;
  it does need to survive.
- **Data Sources — merge into Methodology.** Strip the "checked and blocked"
  block and the Function column on the way; both are clutter.
- **AI Reliability — one page, renamed plainly, made live.** It reads as
  clutter because it is three hand-written incidents frozen in time. It is also
  the single most employer-relevant page here: it documents real incidents
  where the agent stated something false and the mechanical mitigation that
  worked. Stage 3's agent decision log is the same page — merge them, feed it
  from Booth's `booth-verdict` blocks, and stop maintaining it by hand.
- **Season Accuracy — declutter.** Too much on one page.

**Content work:**

- Methodology in plain English throughout.
- Simplify "track record at this confidence" on My Picks — currently far too
  many words.
- **Boards: a couple of plain sentences on why a team is favoured, in football
  terms.** The best idea in the source document. The model already computes
  per-feature contributions for Team Deep Dive, so the data exists; this needs
  a translation layer, not new maths.
- Update README.md for a cold reader.

**Two decisions taken 2026-09-08, with the reasoning, so they are not reopened:**

- **Batch related items into one PR.** The remaining 7.5 items go out as roughly
  four PRs, not eight. How This Compares, Data Sources and the Glossary all
  merge into Methodology and all touch the same page and the same nav, so
  splitting them means three audits of three fragments of one change — and
  Booth reviews a coherent change better than a slice. The counter-argument
  (small diffs are easier to revert) lost to the fact that each audit costs
  usage and a manual trigger. NOT one giant end-of-stage PR: a large diff is
  exactly where Booth's value drops, and #40 and #41 each surfaced a real
  defect that was cheaper to find early.
- **Build the plain-language guard FIRST, red, with a shrinking allowlist.**
  The reader-facing pages fail it today, so it lands with today's violations
  listed as known-bad, and each rewrite deletes entries. The list reaching
  empty IS the definition of done for the content work. Written afterwards it
  would be fitted to whatever copy happened to get written — ratifying the
  result instead of testing it, which is the "guard written after the fact"
  pattern that has bitten this repo five times.

**Make plain English testable, not aspirational.** `tests/test_plain_language.py`
holds a jargon list scoped per page: log loss, Brier, calibration,
opponent-adjusted, shrinkage, bootstrap, confidence interval and similar are
BANNED on Boards, My Picks, Power Ratings, Team Deep Dive and Season Accuracy,
and allowed only on Methodology, Model Lab, What's Changed and the build
page -- `TECHNICAL_PAGES` in that file is four entries, not three. A future session
adding "the model's Brier score" to Boards fails the suite. Without a guard,
this pass reverts the first time anyone writes new copy — the same reasoning as
every other guard in this repo.

**Explicitly NOT in this stage — these belong to the visual overhaul:**

- How much room week-by-week net ratings take over a season on Team Deep Dive.
  A layout question Stage 10 owns; deciding it before the Stage 8 direction
  exists means deciding it twice.
- ~~Import/Export picks buttons staying highlighted after a tap on mobile. A
  `:focus` state persisting after touch.~~ **FIXED in PR #68, and the
  diagnosis above was wrong.** It was not `:focus` and not touch-specific:
  the Week Board's filter handler selected `.filter-btn` page-wide, and only
  three of the nine elements wearing that class are filters. Clicking Export
  My Picks added `.active` to it, stripped `.active` off All Games, and set
  `currentFilter` to `undefined`. It reproduces under a programmatic click in
  headless Chromium with no touch involved, and a focus ring cannot remove a
  class from a different element -- the half of the symptom the original
  entry never accounted for. Guarded by `tests/test_filter_button_scope.py`.
  Kept rather than deleted, because a wrong diagnosis that survived in this
  file for days is the thing worth remembering.

**Deferred as new features, not cleanup:**

- Weekly team news on Team Deep Dive — injuries, trades, firings, releases,
  scraped and summarised briefly. This is a new external data source with
  staleness, rate-limit and reliability concerns; Stage 6 in nature, and it
  must not gate the visual work. NOTE for a future session: Stage 6 records
  injury DATA as closed, but that decision was about model features. Displaying
  team news is a different question and is not foreclosed by it.

### Stage 7.6 - The repository front door  <- CHEAP, HIGH VISIBILITY, DO IT EARLY

Added 2026-09-08 by Mark, who noticed it reviewing the repo as a stranger would.
A decimal insert like 7.5; stage numbers stay frozen.

**The problem:** GitHub's About panel says "No description, website, or topics
provided". A recruiter's first screen of this project is therefore blank, and
the README opens on fixed-effects regression, EPA, shrinkage and model metrics
— excellent for a technical reader, useless as a first impression.

Three items, none of which touch the dashboard:

1. **Repository description.** Mark's wording, to use as given:
   "NFL win-probability and analytics platform using real-world play-by-play
   data, backtesting, automated data processing, testing, and AI-assisted
   development."
2. **Topics**, where accurate: `python`, `data-analysis`, `predictive-analytics`,
   `sports-analytics`, `nfl`, `github-actions`, `testing`. Check each against
   what the repo actually does before adding it — a topic is a claim.
3. ~~**A "For Recruiters / Project Overview" section at the very top of the
   README.**~~ **DONE, PR #46 (2026-09-09).** It also turned up four claims the
   README was making that were false, including a fifth line pointing at a
   `METHODOLOGY.md` that has never existed here.
   `tests/test_readme_accuracy.py` now holds the page to its own claims.

**Items 1 and 2 are DONE (2026-09-24).** Set in the built-in browser once Mark
had signed it in to GitHub: his description word for word, and all seven
topics, each checked against the repository first. The website field was
left empty because it was not asked for. From here the only route to repo
settings is that signed-in browser: there is still no `gh` CLI and no
settings tool in the GitKraken MCP.

Note the overlap: Stage 7 already carries "README rewrite for a cold technical
reader". That is the same file. #46 put the recruiter section on top and fixed
what was wrong below it; a full technical rewrite underneath, if still wanted,
is what remains of that Stage 7 item.

## The visual overhaul (Stages 8-10)

Read this before starting any of the three. The brief is not "fix the audit
findings".

The 2026-09-06 audit scored the dashboard **15/40** and produced a list of real
defects: 21 font sizes, 31 spacing values with 63% off a 4px grid, seven
transition durations, no `prefers-reduced-motion` block, amber meaning five
different things. Every one of those is worth fixing. But they are all
**corrective** — fixing the entire list produces a dashboard that is clean,
consistent and unobjectionable. It does not produce one that makes someone stop
and look.

The stated goal is the second thing: **someone opens this dashboard and says
"that is amazing"**. That needs a visual point of view — a deliberate answer to
"what does this thing look like, and why" — that the tokens then serve. A
spacing scale with no concept behind it is just tidier arbitrary numbers.

So Stage 8 starts with the concept, and Stages 9 and 10 execute against it.
Treat the audit list as the floor, not the goal.

One live tension, now resolved: everything built in Stages 2-7 used hardcoded
pixel values, because the scales did not exist yet. That is deliberate and accepted — the
ordering was chosen so carried-over work ships first — but it means Stage 8's
job is bigger than the audit's counts suggest. Reuse an existing class before
inventing values; every new one is something Stage 8 has to unpick.

### Design tooling available from Stage 8 onward

Mark added these connectors and asked, on 2026-09-08, that they be used when the
visual work starts: **Canva**, **Figma**, and — as candidates — **Watermelon UI**,
**Motion Primitives**, **Haikei**. His instruction: "whatever we need to do to
take the design from where it's at and make it the best it can possibly be."

**The constraint that decides how each one fits.** This dashboard is ONE
self-contained HTML file: `dashboard_template.html` with placeholders swapped by
`generate_dashboard.py`. Vanilla JS, no framework, no bundler, no npm at
runtime. That is why it deploys as a static page driven by a weekly cron, and
for a portfolio piece it is a genuine asset — a stranger reading the repo sees
no supply chain. Do not spend it casually.

- **Haikei** (haikei.app) — best fit of the five. Generates SVG design assets
  that paste straight into the existing file with no architectural change. The
  caveat is what it generates: decoration. Stage 8 starts with a concept, and a
  Haikei shape applied without one is prettier arbitrary decoration. Use it to
  execute part of a concept, not to find one.
- **Figma** (MCP connected) — strongest fit for Stage 8 proper.
  `get_variable_defs` pulls design tokens, so the system lives somewhere durable
  instead of only as CSS custom properties in one file, and the file itself
  becomes portfolio material. Figma is the source; the single HTML file stays
  the runtime.
- **Canva** (MCP connected) — aim it at Stage 7, not the dashboard. README hero
  image, architecture diagram, case-study one-pager. Designing the UI in it
  would fight the code.
- **Motion Primitives** and **Watermelon UI** — both are **React** (Framer
  Motion components; shadcn-style blocks). Verified by looking them up, not
  assumed. Neither drops into a vanilla single-file page: adopting either means
  adding React and a build step to a project whose whole deployment story is one
  static file. **Recommendation: borrow Motion Primitives' motion vocabulary —
  its easings, durations, stagger patterns — and implement it in CSS transitions
  and the Web Animations API.** Stage 9 already owns "seven transition
  durations, no `prefers-reduced-motion` block", so a coherent motion spec is
  exactly what is needed; the library is one way to get one, not the only way.
  If Mark decides he wants the React components anyway, that is a legitimate
  call — but it is an architecture decision with tradeoffs that should be put to
  him explicitly, not something that arrives as a side effect of wanting nicer
  animations.

**Assessed and set aside, 2026-09-09.** Mark brought two candidates and neither
becomes the direction, but the reasoning is worth keeping so they are not
re-proposed:

- **`basbruss/Minimalist-Dashboards`** is a **Home Assistant** Lovelace
  configuration — YAML plus HACS custom cards, last released February 2023. It
  only runs inside Home Assistant; there is no CSS or component code to lift at
  any level of effort. Its *look* (soft-cornered tiles, muted palette, icon-led,
  generous whitespace, very little text) is a fair mood reference and nothing
  more. Checked, not assumed: the repository itself tells people not to copy it.
- **shadcn/ui + Tremor or v0** is React throughout. Tremor is React + Tailwind +
  Radix and was acquired by Vercel; v0 generates React/Next projects, usually on
  shadcn. Adopting them literally means replacing this dashboard's architecture,
  not restyling it — and a large share of the suite depends on the current
  shape: the jargon guard parses the template's render functions, the chart and
  why-sentence harnesses execute the shipped JavaScript, the mutation corpus
  anchors on exact source strings. A rewrite spends Stage 8 rebuilding
  verification. What a recruiter judges is the rendered page and the rigour, not
  the framework.

**The recommended path, if a shadcn-like look is what Mark wants:** take the
token layer, not the components. Its appearance is largely CSS variables — a
neutral scale, a radius scale, disciplined borders and shadows, a spacing
rhythm — and this dashboard already has a token layer to swap. Use v0 as a
design *generator* whose output is translated by hand, never imported. Keep the
hand-built SVG charts: they already do things a chart library would lose
(colour follows the entity so a filter cannot repaint the survivors; shape and
dash carry identity without colour; dark mode is stepped, not flipped). And note
the cost nobody mentions — shadcn is now the default look of a great many
dashboards, which is a real price for a portfolio piece whose pitch is
independent judgement.

**Closed:** this asked for a concrete visual reference before Stage 8 began.
Stage 8 began and closed without one; the concept in
`docs/design/STAGE8-DESIGN.md` is what answered it. A token system with no point of view behind it is just tidier
arbitrary numbers — this file says so already, and no connector changes it.

### Skills to use, and what each is for

These are available and should be used deliberately rather than mentioned.

- **`design`** (design canvas) — multi-artboard visual design published as an
  editable artifact. This is the right tool for the concept work at the top of
  Stage 8: explore two or three genuinely different directions as artboards
  before committing anything to code. Cheap to throw away, which is the point.
- **`artifact-design`** — design fundamentals; load before building any
  artifact, including the canvas above.
- **`dataviz`** — the chart method: form heuristic, the four colour jobs, mark
  specs, the hover/interaction layer, and the anti-pattern catalog. Its
  validator already produced this project's `--series` tokens
  (`scripts/validate_palette.js`, OKLab dE, CVD simulation, contrast). Every
  new colour in Stage 9 goes through it, in both themes. Its anti-patterns file
  is a checklist for Stage 10's charts.
- **`dashboard-design-audit`** — the 8-category scored audit that produced the
  15/40. Re-run it at the END of each visual stage and record the score. Three
  scores across three stages is a measurable claim about improvement rather
  than an assertion that things look better.
- **`design:design-critique`** — a second opinion on a direction before it is
  built out. Use it on the Stage 8 concept, not on the finished thing.
- **`design:accessibility-review`** — pairs with the Stage 9 focus/keyboard
  pass; contrast and CVD are already covered by the dataviz validator.
- **`artifact-diagramming`** — for Stage 7's architecture diagram, not these.

### Stage 8 - Design system foundations  <- DESIGN PHASE COMPLETE (2026-09-10)

**The concept is decided and written down.** It lives in
`docs/design/STAGE8-DESIGN.md`, which carries the token block verbatim and the
reasoning behind every value. Read it before touching CSS. The one-line
version: colour has exactly four jobs and nothing else gets a hue; team
identity is a logo, never a colour; elevation is a border, not a shadow; and
the graded colours may appear only after a game has been scored, because a
colour meaning "correct" on a game that has not happened makes the page lie.

**Stage 8b, the port, is DONE** — it lifted that block into
`src/pipeline/dashboard_template.html` and restyling page by page. The template was
3,250 lines across nine pages at `b5d6bb9`; the design was proven against two.
A great many tests assert on it -- several on colour tokens and exact strings. Treat a failing
colour assertion as a question, not as something to update to match: those
tests encode earlier decisions that were themselves argued for.

**CORRECTED 2026-09-23: the token block DEFINED the audit's foundations; it did
not satisfy them.** This sentence said "now satisfied by the token block"
from Stage 8b until 2026-09-23, while the template carried 105 hand-typed
font sizes against 15 uses of the type scale, and 263 literal spacing
lengths against 41 uses of the spacing tokens -- counted at `073a859` with
`literal_font_sizes` and `literal_spacing` from
`tests/test_type_and_spacing_scale.py`. Booth's own recount on #94 got the
same first three, and 40 token uses counting only spacing properties. The
rendered page still showed 21 distinct font sizes, the original audit's own
count. (The figures first written here, 106/10 and 232/17, came from quick
greps on another commit with no command beside them; Booth could not
reproduce them, which is this file's number trap, committed while
correcting a claim.) Stage 10's scale PR moved the page onto both
scales and `tests/test_type_and_spacing_scale.py` now holds it there. **A
token that nothing uses is a proposal, not a system: count the consumers
before writing that a scale is adopted.** What the block provides -- spacing
scale, type scale, tabular figures, radius tokens, a motion system of three
durations and one easing, `prefers-reduced-motion`, and elevation-as-border
with `--shadow-overlay` reserved for the single `.overlay` component. It is
kept below for the record of what the page looked like before:
a spacing scale replacing 31 ad-hoc values, 63% of which sit off a 4px grid; a
type scale replacing 21 distinct font sizes including seven half-pixel ones;
tabular figures across every numeric surface, currently used once in a
table-heavy dashboard; radius tokens replacing 8 values despite `--radius`
already existing; a motion system of two durations and one easing replacing
seven durations, plus a `prefers-reduced-motion` block which does not exist at
all; an elevation pass so the six shadow tokens are actually used.

**`--shadow-overlay` has TWO consumers, not one.** `docs/design/STAGE8-DESIGN.md`
says one, the `.overlay` component -- but `.overlay` appears zero times in
`src/pipeline/dashboard_template.html`; it was a mock-only element. The real consumers
are `.undo-toast` and `.rel-tip`, which is what the token comment in the
template says. Corrected here rather than in only one of the two documents.

Do the concept first. Tokens chosen to serve a direction are a design system;
tokens chosen to reduce a count are a tidier mess.

### Stage 9 - Colour, components & interaction

**A point of view on colour**, not only the removal of ambiguity. The
corrective work: retire the 33 hardcoded team-brand hex values driving
probability bars in favour of `--series` tokens — `teamColor()` falls back to the
literal `#8A93A8` (the old dark `--chalk-dim`, retired in `007cebe`), which is
wrong in light mode wherever it is reached, and is reached only for an
abbreviation outside the 32 in `TEAM_COLOR`; that same literal is baked into
`.week-select`'s chevron data-URI, where it is DEAD rather than wrong —
corrected 2026-09-21, every element wearing that class is clipped to 1x1 and
the chevron paints in no theme — and red-vs-blue
bars read as bad-vs-good rather than as two teams. Disambiguate amber -- DONE
by Stage 8b (`c90a222`): `--amber` is gone, brand, active nav, sorted column
and the flagged card all wear `--accent`, which is a blue, and the only ochre
left is `--series-b`, Model B's chart series. When this was written amber
meant all five at once.

**Stage 9's colour work is DONE (2026-09-22).** Decided, and held by
`tests/test_graded_colour_scope.py`:

- **The graded pair means one thing.** `--good`/`--warn` appear ONLY where a
  scored pick was right or wrong: the graded tag, the pick badge, the streak,
  and Team Deep-Dive's tick and cross. Nine other uses went to the neutral
  ramp: decision pills, the "Built" pill, gap numbers, a team's W/L, rating
  trend arrows, Model Lab's "Current." dot, and the incident labels. The
  guard compares the full consumer set against that list.
- **The Net Rating sign is not a hue.** The fill is neutral `--text-3` on both
  sides of zero. The zero line and the bar's direction already carry the
  sign. A diverging pair would be a fifth colour job, and its warm pole would
  read as "wrong". Contrast is 3:1 or better on both surface and track, in
  both themes, and is recomputed in the test. `--accent-strong` retired with
  it.
- **Confidence has no hue**: it is the bar's length and the number. **A
  flagged game** is the `--accent` left border. **The neutral pill is
  neutral**: `.tag-neutral` used to wear the accent, so every decision label,
  and the card's toss-up tag, carried the colour of the model's lean.
- Model Lab's hand-written version timeline was a second copy of
  `VERSION_HISTORY` and is gone.

**Deferred to Stage 10's component pass, and done there:** one button
component. There are twelve button classes styled one by
one. A keyboard sweep on 2026-09-22 found every focusable control on all
nine pages taking a visible ring. The reliability points use their halo
instead, and the next-week buttons are disabled on the latest week, which is
correct. So the focus pass needs no separate work. The two `.game-card` headers were
unified in #64.

The original brief, kept for the reasoning:
Beyond that: the Net Rating bar was deliberately left amber in Stage 2 with a
note saying sign-encoding belongs here. A diverging pair with a neutral
midpoint is the `dataviz` answer; run it through the validator in both themes
rather than picking by eye. Decide what confidence looks like, what a flagged
game looks like, and what "the model was wrong" looks like — the dashboard
currently says all three in the same amber.

Also: one button component with real variants and states; a focus and keyboard
pass paired with `design:accessibility-review`; unify the two `.game-card`
render paths.

### Stage 10 - Layout, tables & responsiveness  <- COMPLETE (2026-09-23)

**Order, agreed with Mark 2026-09-23: one PR at a time, each cut from `main`
after the last merges** — mobile pass, components (button, page header, nav
labels, onboarding banner), table system, page states, the standout moments,
then the audit re-run.

**Mobile pass: merged, #89.** Two hard pixel floors wider
than a 320px phone's 296px content box (the card grid's 340px track, the
reliability plot's 300px) are `min(Npx, 100%)`. The sidebar hands over at
1079px, not 820, and full team names drop at 1180. The template's
Breakpoints comment lists every viewport breakpoint and
`tests/test_responsive_layout.py` holds it to the media queries. **Two
queued items were not what they said:** bottom-nav clearance already worked
(the last content ends above the nav on every page at 320, 390 and 430 --
23-43px on the local Windows machine, 18.5-42.2px in Booth's sandbox on #89, because the gap
is `<main>`'s bottom padding minus the nav's height and that height is
text), and "the ratings table
clipping mid-column at 430px" is a table scrolling inside its own box, which
every phone table does. The fix for that is the table system's scroll-edge
affordance, not a layout change.

**Components: merged, #90.** Decided with Mark on
2026-09-23, from rendered side-by-sides:

- **The sidebar is grouped by the question a visitor is asking** -- This
  Week, Your Picks, Track Record, How It Was Built -- replacing two groups
  both called "Model Output".
- **Every page header is eyebrow, title, one-line description.** The
  eyebrow is the page's sidebar group, in `--text-2`, not the accent (the
  accent means "active"). On a phone it is the only place that names the
  section. `tests/test_page_header.py` holds header and sidebar to each
  other. The Week Board's welcome box sits below the title.
- **One button component: `.btn`, `.btn-chip`, `.btn-link`, `.btn-icon`.**
  Look and behaviour are separate: the older class beside each
  (`.filter-btn`, `.why-toggle` ...) is a hook for script and tests and
  carries no visuals. That is the root fix for #68 -- the filter pill's
  look was worn by six buttons that were not filters, and a handler
  selected by that look. Only real filters wear `.filter-btn` now, and a
  test says so. Navigation buttons, `.pick-btn`, `.lbx-btn` and
  `.dive-game-head` stay their own controls; the component comment says
  why for each.
- **Model Lab's header typed the model version** and said 2.4 through the
  2.5 release. It is written from `modelVersion` now.

**Table system: merged, #91.** A table either fits its
box or scrolls, and `fitTables()` measures which rather than guessing from
the viewport. A fitting table's wrapper is `overflow:clip` and its header
sticks to the window; a scrolling one draws a soft edge on the side with
more columns. The two cannot both hold: a sticky header needs no scroll
container above it, and a wide table needs one. The scrolling state is the
default, so without JavaScript a table loses its sticky header, never a
column. Borders are `separate`, because a collapsed border stays behind
when a sticky cell moves. Only sortable headers look clickable, and they
now take focus, sort on Enter and Space, and report `aria-sort`. Prose had
been wearing `td.num` and was set flush right; it is not any more.
`tests/test_table_system.py` holds each premise.

**Page states: merged, #92.** Every "nothing to show"
goes through `stateHtml()` in one of four kinds: waiting (nothing yet, and
normal), filtered (a control hides everything; it carries the button that
undoes it), missing (the build lacks something it needs), note (a line
beside content that is showing). **The one that matters is missing vs
waiting**: before, a build that lost its team history drew the same dashed
box as a quiet pre-season week, which is the flattering misreading. Missing
is solid with a heavier left rule, not `--warn` (the graded colours mean a
scored pick only). **There is no loading state, on purpose**: every page's
data is written into the HTML at build time and nothing is fetched, and
`test_the_page_fetches_nothing` says a loading state is owed the day that
changes. The SOS note folded into the system. The shared-picks and
onboarding banners did not: they are notices with actions about a mode,
not states of missing data, and they already share one component.

**The moment: merged, #93.** Mark chose ONE of three
rendered candidates on 2026-09-23: Season Accuracy opens on a scoreboard --
a verdict sentence ("The betting market leads by 1 game.") over a race of
Market, Model B, Model A and, once there are graded picks, My picks.
Declined, so not to be re-proposed without a new reason: a league ladder of
all 32 teams above Power Ratings (it repeats the table's bars) and four
headline numbers above the Week Board. Bars run from a true zero with the
50% coin-flip line marked, never from 50%. The verdict is a pure function
executed under node in `tests/test_scoreboard.py`, because generated
headline prose over signed or tied numbers is where this repo has shipped a
wrong sentence before.

**Team Deep-Dive's week-by-week room: decided NOT to act (2026-09-23).** By
week 18 the list is about 24 rows, roughly the Power Ratings table's
height. It is a question about data that does not exist yet; look again in
December if it actually reads badly.

**Type and spacing on the scales: merged, #94.** Every
font-size is a `--fs` step and every padding, margin and gap a `--s` step,
snapped to the nearest (ties to the larger); Mark approved before/after
renders of every page in both themes. Literal on purpose: 1-2px hairlines,
`calc()` safe-area terms, `<main>`'s 60px page end. SVG chart labels keep
their attributes, because they are in viewBox units that scale with the
chart.

**Audit re-run at the end of Stage 10 (2026-09-23): 28/40, from 15/40.**
Scored with `dashboard-design-audit` on the build with every Stage 10
branch applied, before the scale work: hierarchy 4, spacing 2, colour 4,
typography 2, data-viz 4, states 4, responsiveness 4, consistency 4. The
two 2s are the finding the scale PR then fixed; the score is recorded as
measured rather than re-scored after the fix, so the number is the one a
command produced.

**The moments that make someone stop.** A dashboard that is merely consistent
is invisible. Decide where this one is allowed to be striking — an entry
moment, a hero number, a chart that is genuinely worth looking at — and build
those deliberately. The reliability diagram and the Net Rating table are the
strongest candidates; both are currently rendered as competently as possible
and no more.

**The corrective list**, all still true: fix the duplicate "Model Output"
sidebar group label so the nav's own headings mean something; a shared
page-header component across every surviving page (Stage 7.5 takes 14 down to
9, so count them rather than quoting a figure from here);
a table system with sticky headers, scroll-edge affordance and consistent row
hover; a mobile pass covering bottom-nav clearance so the last row is not
covered, the ratings table clipping mid-column at 430px, and real breakpoints
beyond the three that exist; move the onboarding banner below the h1 where it
stops outranking the page title; empty, error and loading states across all
pages — the SOS note and the shared-picks banner from Stage 2 are the first two
and should fold into whatever system this produces.

**One known data-viz defect, LIKELY MOOT**: Stage 7.5 deletes the Playoff Odds
page, which removes this item with it. Kept recorded in case that deletion is
reversed, and as an example of its family — the same shape as the missing zero
line, a scale that is not what the reader assumes. The bars are normalised to
the highest team's odds rather than to 0-100%, so a league leader at 40%
renders as a full-width bar reading as near-certainty. Found during Stage 2 and
deliberately left for this stage.

Finish with a `dashboard-design-audit` re-run and record the score against the
starting 15/40.

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
- **The footer is `provenance_line()` in `src/pipeline/generate_dashboard.py` (#115)**,
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
weekend refresh (`src/pipeline/weekend_refresh.py`, snapshots to a status folder under
data, Friday 05:17, Sunday 21:47 and Monday 05:37 UTC); #134 the card status
line under the kickoff; #135 the TV checks (`src/pipeline/tv_channels.py`,
`data/tv/exceptions.json`); #136 TV read with `--pending` by both the weekly
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
   shape; a missing field or an empty week opens "Nightly canary failing", like any
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

**Shipped:** #138 `src/pipeline/team_news.py` writes one file per locked, ungraded week
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

**Shipped:** #141 `src/pipeline/model_lab.py` over `experiments/stage*/results/` plus
the 46 old rows moved once, verbatim, to `experiments/legacy/rows.json` (frozen
by sha256 in `tests/test_model_lab.py`); #142 the table rendered at build time
by `render_model_lab_rows` (tests that read Model Lab copy use
`tests/page_source.py`); #143 decision chips with counts. Mappings onto the
five decisions are my calls, listed in `experiments/legacy/README.md`, for
Mark to overrule. #154 each registered result opens with `interval_glyph()`,
its interval drawn against zero (`&minus;` in the text equivalent: the
generator writes `index.html` without `encoding=`, and a literal U+2212 crashes
the build under cp1252). #155 the experiment log is cards below 768px (the
table first fits at about 651-655px; the figure depends on text rendering).
#156 the reliability diagram follows the experiment log; its explanation is
behind "How to read this" and the Brier definition behind "What these numbers
mean", while the bootstrap findings stay in view (they are results).


Generated from a data file, not 46 hand-written rows: Stage 5 and 6 read from
`experiments/*/results/`, the older rows moved in once, verbatim. Five
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

## Stages 23 to 29: the 2026-09-28 audit (planned 2026-09-28)

From an outside audit (Fable 5.1) of `main` at `a89a6ef`. Every finding was
checked against the code before it became an item; the verdict table (what was
CONFIRMED and how, what was WRONG) and the audit's own text are in the session
archive on the local Windows machine (audits). **Mark approved this plan 2026-09-28.** He agreed
with every pushback below, and said he is willing to weaken the methodology
where that makes the project stronger overall -- so the items marked "discuss"
are NOT refused, they are discussed with him when reached. One item, one PR, as
always; each numbered item below is one PR.

**Corrections to the audit, so they are not re-litigated:**
- Every real Booth audit comment is posted by `claude[bot]` (the Claude app),
  not `github-actions[bot]`. A collector filter on `github-actions[bot]` would
  drop every audit.
- Post-lock lines are NOT lost: the weekend refresh saves the latest
  `spread_line` for every locked, ungraded week (Friday, Sunday, Monday).
- Booth already runs each PR's scoped mutation cases in CI; only the full
  corpus never runs there.
- `OVERFLOW_PAGES` also OMITS `changelog`, so the More button is not
  highlighted on What's Changed -- a live bug the audit filed as hygiene.

**Order: 23 now; 24's skipped-week marker and deploy gate before a lock is
missed; 25 in the gaps; 26 before Stage 20's testers; 21 when week 5 lands;
27 as filler; 28 after the regular season (beside line movement); 29 last,
then 22.**

### Stage 23 - Page security and Booth's read-only claim
**Progress:** item 1 merged (#169), item 4 merged (#170), item 5 merged
(#176), each SAFE TO MERGE with 0 discrepancies. #176 was expected to go
unaudited (the action used to refuse a PR editing its own workflow) and was
not: on `GITHUB_TOKEN` Booth ran on it and posted as `github-actions[bot]`.
So Mark added item 6, merged (#177). Item 2 merged (#178). **Stage 23 is done.** **Item 3 DROPPED (Mark, 2026-09-28):** the
audit's pattern would reject four `implicates` values Booth has really
written ("PR #62 description" and the like), the same parser gates the Booth
job, and after #169 the page escapes everything anyway. **Item 5 CONFIRMED
(Mark read the app's settings, 2026-09-28):** the Claude GitHub App holds
read and write on code, workflows and pull requests, so Booth could push.
Mark agreed it could merge without Booth's audit; that turned out moot, as
above.
1. One `safe_json()` for every JSON fill in the generator, so no string can
   close the page's script element; an injection test over the built page.
2. The agent-log collector keeps only comments by the Booth bot account
   (waits on item 5, because changing Booth's token changes the author).
3. Validate each `implicates` entry and the verdict `head` in the collector.
4. Escape the Power Ratings search text and the card context notes.
5. Booth's token. Mark checks what the Claude GitHub App may do on the repo.
   Then either run Booth on `GITHUB_TOKEN` and drop `id-token: write`, or
   correct README, VERIFICATION.md and the workflow comment. Any tool
   allowlist must keep pip, node and npx: Booth renders pages.
6. (Added 2026-09-28 after #176.) Scout preflight fails a PR that changes
   `booth-pr-audit.yml` or `BOOTH_PROTOCOL.md` unless its body has a line
   beginning "Human review required:". Booth reads both from the PR's own
   checkout, so its verdict on such a PR is not independent.

### Stage 24 - Weekly pipeline resilience and CI coverage
**Progress:** item 2 merged (#171: `predictions/skipped/`, a folder so no
reader of `predictions/*_week*.json` can mistake a skip for picks); item 1
merged (#172, narrower than the audit: only a failed Weekly update
rebuilds, a failed collector still does not); items 5, 8 and 9 merged
(#173, #174, #175); item 7 merged (#180), item 4 merged (#181). **Stage 24 is done.** **Item 3 skipped**: #171 makes
a manual week input mostly redundant. **Item 6 skipped**: GitHub cancels a
PENDING run when a newer one queues in the same concurrency group, so a
group shared by the weekly and weekend runs could cancel a pending weekly
lock run -- worse than the race it prevents, which #147 already narrows to
seconds.
1. Pages builds after a failed weekly run (not only a successful one) and
   lets `src/pipeline/check_build.py` decide. The job still fails and still opens its
   issue (Stage 4's design).
2. A skipped-week marker that `determine_next_week` counts and the build
   ignores, so one missed lock does not stall every later week; first tests
   for `determine_next_week`.
3. A week input on the weekly workflow's manual run.
4. Never save an empty week.
5. The test workflow runs on push to `main` and on every path, installs the
   pinned dev requirements, and installs node.
6. One concurrency group shared by the weekly and weekend runs.
7. `timeout-minutes` on the seven workflows without one.
8. Write-once JSON written atomically (tmp file then replace).
9. First tests for grading and for the drift z-test.

### Stage 25 - Small correctness fixes
**Progress: done.** Item 1 #182, item 2 #183, item 3 #184 and #186 (#184
warned about next week's missing QB columns on every run; Mark saw it would
fire falsely on a Tuesday hold run, so #186 moved the warning to lock time),
item 4 #185, item 5 #187, item 6 #188, item 7 #189, item 8 #190 (agreed by
Mark). Since #190 the generator reads and writes UTF-8 on every platform, so
the old rule "avoid literal non-ASCII in generated text" no longer applies.
1. A tie is graded as a tie: no winner, no correct/wrong.
2. README's holdout sentence says what the weekly refit does, held by the
   README test.
3. The QB columns become required schedule columns, with a warning.
4. The More button's page list: the five real More pages.
5. One HTML escaper in the template; one spelling of Offense and Defense.
6. Methodology: how the live market probability is computed, and that the
   live pick reads Thursday's line (docs only).
7. `.python-version`.
8. Discuss: `encoding='utf-8'` on the generator's reads and writes
   (`docs/context.md` lists it as known and not fixed).

### Stage 26 - What a visitor sees (before Stage 20)
**Done (2026-09-29).** Merged: 6 #191, 7 #192, 8 #193, 9 #194,
10 #195, 11 #196 (the built page drops the template's comments, the agent
log's per-audit records and its JSON indentation: about 750KB to 438KB; the
browser checker's byte budget is 800,000), 1 #197 (a final, ungraded card
reads "Model B picked GB 68% · ATL won"), 2 #198 (a page change sets the
title, `aria-current="page"` on the nav, and focus on the page heading), 5
#199 (team and week rows link to their routes; Booth said NEEDS HUMAN REVIEW
twice with no discrepancy and Mark approved the merge), 3 #200. 3 and 4 were
decided by Mark on 2026-09-28 from rendered side-by-sides (artifacts "Phone
Header Options" and "Phone Chart Text"): 3 is a sticky top bar below 1080px
with the h1 and a theme button, and the provenance line at the foot of the
page; 4 draws the trend and reliability charts 300 units wide below 640px,
with the trend chart's line-end names dropped there: 4 #201 (Booth caught its
first version growing the desktop reliability plot from 390 to 406 units;
fixed, with a test and a mutation case holding the desktop drawing).
1. A final but ungraded card stops saying "to win" and shows a neutral
   provisional result -- without bringing back "graded on Tuesday", which Mark
   removed on 2026-09-28.
2. A page change sets the title, moves focus and marks `aria-current`.
3. Phone: an h1, the theme toggle and the provenance line, decided from
   rendered side-by-sides.
4. Chart text readable on a phone (render first; the audit's 4-6px is
   arithmetic).
5. Team rows and week rows link to their routes. The bottom nav stays as
   Stage 13 set it unless Mark reopens it.
6. to 9. `aria-expanded` on the two disclosure toggles; `scope` on table
   headers; the trend and calibration charts labelled or hidden; one
   chip-state convention (four PRs).
10. The reliability points as one focusable group.
11. The built page loses the agent log's unused `audits`, its JSON
    indentation and its comments; the byte budget is then set from a fresh
    measurement with headroom.

### Stage 27 - Supply chain and guards in CI
**Progress (2026-09-29, afternoon):** item 2 merged (#202; its first run,
started by hand, caught 30 of 30), item 3 merged (#206: `ruff check .` runs
in `run-tests.yml`, so every branch must pass it), and the runner's UTF-8
fix merged (#207; `PYTHONUTF8=1` is no longer needed for the runner on
the local Windows machine). Item 1 merged (#208, on Mark's explicit OK). **Stage 27 is done.**
Booth's claude-code-action stays pinned to v1.0.236: the `v1` tag moved to
v1.0.237 at 19:30 UTC on 2026-09-29, mid-review, and the pin was kept on
the release Booth had been running. Item 4: Mark said skip
Dependabot (2026-09-28), so nothing moves the pins but a person; bump one by
hand, with its release in the comment, when an action's release matters.
`setup-node`, cache, artifact and Pages actions stay on tags.
1. SHA-pin the Claude Code action and the auto-commit action, then checkout
   and setup-python.
2. A nightly mutation slice chosen by a date seed, CAUGHT counts in the run
   summary.
3. ruff with pyflakes rules only, after one run to see what it finds.
4. Discuss: Dependabot (it opens several PRs at once, each audited).
   Decided: skip (Mark, 2026-09-28).

### Stage 28 - After the forward test (after the regular season)
Discuss each before starting. Splitting `weekly_update.main`; an offline
synthetic two-season fixture; one model spec shared by the live pipeline and
the backtest (not the research scripts, which are the record of registered
experiments); a registered experiment on regularisation and feature scaling;
a registered question on a fitted market forecast against the hand-picked
curve; drift on log loss (reopens a recorded decision); playoff games out of
the season simulation.

### Stage 29 - Front door (last)
One product name and a favicon (Mark picks); a LICENSE (Mark picks); README
"what is unusual here" and a correct "Running the tests"; the Website field
and version tags; the audit-log collector off every push; a short
CONTRIBUTING and PR template; the noreply email for future commits (no
history rewrite); CLAUDE.md split into rules plus traps and history.
**Progress (2026-09-29):** README "Running the tests" and two recruiter
bullets (#209); CONTRIBUTING and PR template (#210); MIT LICENSE (#211,
Mark's pick); favicon B, the sidebar football on a dark tile (#212, Mark's
pick); one product name, "Pick'em Model" (Mark's pick after he first
floated "NFL Analysis Tool": #213). The link preview and share image
keep "The Pick'em Model"; the repository keeps "NFL-Model-2". The noreply
email is the local machine's repo-local `user.email` (done, no PR). **Decided, not
done:** the audit-log collector stays on every push (Mark agreed with the
pushback: it commits only when a new Booth report exists, once per merged
PR however it is triggered). **Left:** the Website field and version tags
(Mark: "later"; they change his GitHub settings and published tags), and
CLAUDE.md split into rules plus traps and history (its own session).

**Not planned (Mark agreed):** packaging `src/` into subfolders, converting
`print` to logging, routing owner-only dispatch inputs through `env:`, and
scrubbing the machine name from this file. (Reversed 2026-09-29: Mark
chose to do it after the re-audit; Stage 31 item 10.)


## Stages 30 to 34: the 2026-09-29 re-audit (planned 2026-09-29)

Two independent senior audits have scored the repository: 71/100 on
2026-09-28 at `a89a6ef`, and 78/100 on 2026-09-29 at `61ada9d`, after #169
to #213. The rubric has 18 weighted categories. Code quality (70),
architecture (75) and maintainability (66) carry a fifth of the weight and
have barely moved, so the next points are there. The ceiling for a one-file
static site with no backend is about 90 to 92, so passing 90 means finishing
every stage below. Each stage boundary is a safe place to stop. The item
numbers are the audit's and run across the stages.

Rules for all five stages, on top of the PR loop in CLAUDE.md:
- Every line number in the audit was read at `61ada9d`. Find each place again
  before editing it.
- An audit finding is a hypothesis: check the mechanism in the code first.
- Any PR that moves Python code must be proven behaviour-identical: run
  `python -m src.research.reproducibility_audit` before and after and show the
  metrics match bit for bit, then build the page before and after and diff
  the two `index.html` files (byte-identical unless the PR says why not).
- No framework, chart library, backend or build step that changes the
  one-file deployment. No re-opening a REJECTED Model Lab row. No re-tuning
  half-life, alpha or QB shrinkage. No new regex-over-template test where a
  node harness can run the function instead.

Order (Mark said "whatever you think is best", 2026-09-29): Stage 30's items
that do not touch the weekly pipeline (2, 5, 6, 7, 9) first. Its pipeline
items (1, 3, 4, 8) wait until the Thursday lock has been seen to run, because
scheduled runs start up to 6.5 hours late and a pipeline mistake merged just
before a lock costs a week's picks. Then items 10, 11, 14 and 15, then 16 to
19, then 20 to 25, then 12 and 26 together, then Stage 34.

**Progress (2026-09-29, night):** item 10's split (#214) and path scrub
(#215); item 2 sticky headers (#216); item 6 preflight gate (#217); item 7
nightly alert (#218); item 5 (#219: Booth's accounts, and Mark chose true
sentences over narrowing Booth's tools); item 9 hygiene open as #221. Item
9's `env:` inputs: declined again by Mark. Item 11: no module was dead
(pushback, branch s31-module-purposes). Items 13 and 19 ready on branches
s31-task-runner and s32-env-and-rules; the issue text fix on
s30-booth-alert-wording. Item 27: tags v2.2 to v2.5 pushed, Website field
set by Mark; v2.0 and v2.1 predate the repository. Items 14 and 17 reverse
2026-09-28 declines and wait on Mark. Every deviation from the audit is
logged, with its reason, in Mark's "Audit Response Log" doc for the next
auditor.

**Progress (2026-09-30, overnight, Mark asleep):** #237 item 3, #238 the
simulation's regular-season filter (Stage 33, from item 20's fixture), #239
and #248 item 12 (batches A to D; the one-third target is not reached on
purpose, see the Audit Response Log), #240 and #246 item 18's hints, #241
item 15, #242 item 31 (icon; og card kept, Mark's earlier decision), #243
item 16, #244 item 17, #245 item 30, #247 the runner's UTF-8 mode (ends the
Windows-only WRONG-GUARD). Stages 30 and 31 are done. Left, after Thursday's
lock: item 14, ruff `I`/`UP` (item 18's tail), item 23; then items 21, 22
and 24 as registrations first; then 26 and 32.

### Stage 30 - Regressions and residuals from Stages 23 to 27

1. A tie renders as "Missed" with a red cross: `graded` is true for a tie whose
   `*_correct` are all null, and both the card tag and `pickBadge` fall
   through to incorrect. Team Deep-Dive calls the game "not yet played". Fix:
   carry `result` into `build_games_js`; show a neutral "Tie" tag and no
   badge when the game is graded but `correct` is null; Team Deep-Dive says
   "Tie". Add a node test and a mutation case. Decide whether `n_graded`
   counts a tie, and write the decision down.
2. Below 1080px the sticky top bar (z-index 40) covers every sticky table
   header (`top:0`, z-index 3). `.table-wrap.fits` is `overflow:clip`, which
   is not a scroll container, so the headers stick to the viewport. Fix: in
   the under-1080 block, offset the header by the bar's height (a
   `--topbar-h` written by a ResizeObserver, since the bar's height depends
   on the safe area and on wrapping). Add "scroll past a fitting table at 390
   and 900" to `tests/browser/check_page.py`.
3. Previews outlive their week: `load_previews` skips locked weeks but not
   skipped ones, and nothing deletes a preview when the lock is written. Fix:
   pass the skipped set too; `save_week` deletes the week's preview (the
   workflow's `predictions/**` pattern stages the deletion); a preview whose
   first kickoff has passed says the lock run did not happen.
4. `record_skipped_week` can fire on an already-locked week through `--week N`,
   because the skip branch runs before the check for an existing file.
   Reorder; test.
5. Booth leftovers: `booth_report_posted.py` accepts any bot account (use
   `BOOTH_ACCOUNTS`); the workflow header and `docs/architecture.md` say Booth
   "can only comment", but it can also edit the PR it audits. Either narrow
   its allowed tools or rewrite the two sentences. Mark's call.
6. Preflight's "Human review required:" gate reads the raw body, so a line
   inside a code fence satisfies it, and its diff misses a renamed Booth
   workflow. Use the quotation-stripped claims text and `--no-renames`.
7. The nightly mutation slice fails silently: on failure, open an issue
   through `src/pipeline/alerts.py` like every other unattended job, and replace
   "about 820 cases" with a computed figure or drop it.
8. `src/pipeline/atomic_write.py` writes a fixed `<name>.tmp` in a committed folder:
   use a unique temporary name in the same folder, and ignore `*.tmp`.
9. Hygiene, one PR: `referrerpolicy="no-referrer"` on the logo images;
   `rel="noopener"` wherever `target="_blank"` lacks it; workflow inputs
   through `env:` in `booth-regression.yml` and `run-backtest.yml`; stale
   comments in `weekly_update.py` and `weekly-update.yml`; dead CSS
   (`.glance-*`, `.confidence-badge`, `.status-next`, `.add-idea`).

### Stage 31 - Maintainability

10. The CLAUDE.md split. DONE in #214 (2026-09-29): 3,079 lines became the
    rules (436), `docs/traps.md` and this file. Its second half, taking the
    machine name and local paths out of the public documents, is a separate
    PR (Mark's pick): machine specifics go to a gitignored `CLAUDE.local.md`.
11. Delete dead modules: `src/research/compare_data_sources.py`,
    `src/research/stage5_residuals.py`, `src/research/backfill_game_dates.py`, after checking
    every document and test for mentions.
12. Retire the regex-over-template tests that a node harness already covers by
    running the same function. Use the corpus's WRONG-GUARD reports to find
    them; run the affected case files whole and quote both counts. Target: at
    least a third fewer, with every mutation case still CAUGHT.
13. One task runner (a `Makefile` or `tasks.py`) with test, lint, build,
    browser-check, mutation-slice, mutation-all and wrapup; README's "Running
    the tests" points at it.

### Stage 32 - Code quality and developer experience

14. Package `src/` into `pipeline/`, `research/` and `agents/` in ONE
    mechanical PR with no logic change. Replace the `sys.path.insert` lines
    with a `pyproject.toml` that makes `src` importable; update every
    `python src/x.py` in the workflows and `conftest.py`. Prove it with the
    reproducibility audit and a byte-identical page.
15. One `paths.py`: the root, the data folders, one `parse_week()` for the
    four copies, one `current_season()` for the two Python copies and the
    shell copy, one team list.
16. Break `weekly_update.main` into `load_inputs()`, `fit_models()`,
    `predict_week()` and `save_week()`. `weekly_summary.py` parses the printed
    output, so either keep every printed line identical or, better, have the
    run write a JSON record that the summary reads.
17. `logging` in the pipeline modules, with a default format that keeps
    `weekly_summary.py` fed. Research and agent scripts may keep `print`.
18. Type hints on the public functions of the five pipeline modules (not a
    whole-repo sweep); ruff rule sets `I` and `UP` after one dry run.
19. One README section on the environment variables and the rules only the
    code knows today: predictions are write-once; the next week comes from
    the last saved one; the suite and mutation runs rewrite `index.html`; the
    `Suite: **N passing**` literal is an interface.

### Stage 33 - Architecture and model engineering

20. A synthetic two-season fixture so the weekly update, grading, backtest,
    drift check, season simulation and weekend refresh run end to end offline
    in under two seconds, with the prediction-file schema asserted. The
    season simulation has no tests today and no regular-season filter.
    DONE 2026-09-29 in #228 (`tests/synthetic_league.py`) plus
    `tests/test_pipeline_chain_end_to_end.py`; the regular-season filter in
    #238. Not marked here until 2026-10-03, so the 10-02 handoff still
    listed it as open; re-checked then: 18 passed, slowest test 1.02s.
21. One `MODEL_SPECS` and `walk_forward(spec)` shared by the live pipeline and
    the backtest. Make `C` and `penalty` explicit at today's values, then
    REGISTER experiments on `penalty=None` and a `StandardScaler` pipeline,
    each ending as a Model Lab row whatever it shows.
    DONE 2026-10-02: `MODEL_SPECS` and `walk_forward(spec)` in #258, proven
    byte-identical; R1 (penalty=None) and R2 (StandardScaler) answered in
    #260, both INCONCLUSIVE at 98.33% on 2024-2025.
22. REGISTER a question on a fitted market curve against the hand-picked
    `spread/5.5`; if the fitted one is at least as good, store its
    probability in each prediction so the log-loss race compares like with
    like.
    DONE 2026-10-02 as R3 in #260: INCONCLUSIVE under non-inferiority
    (+0.00085 [-0.00837, +0.00982], margin +0.002), so the fixed curve stays.
23. Line snapshots on every scheduled run for every locked, ungraded week, so
    the closing-line backtest (Stage 28) has its data.
    DONE in #257, by the weekend refresh (Mark's decision). Its first run,
    `6632b14` on 2026-10-02, appended week 4's lines and nothing else.
24. Drift on log loss against a lagged-QB baseline, reopening the recorded
    decision with Stage 5's H1 evidence as the reason.
    DONE 2026-10-02 as R4 in #261, against the schedule-starter baseline
    (0.6518, Mark's choice) with the lagged 0.6643 printed beside it.
25. Tests tying the `model_version` in the calibration, bootstrap and
    reproducibility files to `MODEL_VERSION`, with an explicit "backtest
    unchanged since 2.4" allowance, and tying the README and Methodology
    backtest table to the calibration file.
    DONE 2026-09-29 in #226 (`tests/test_backtest_figures_tie.py`; the
    reproducibility record is tied by `generated_at`), unmarked here until
    2026-10-03. Widened in #264 (2026-10-03): the version check searches
    `data/` for every file with `model_version` and `backtest_seasons`
    instead of naming two, which brought in `ats_evaluation.json` and
    `low_confidence_finding.json`.
26. A template inliner: parts under `src/dashboard/` joined by the generator
    into the same one file, with a helper so existing text-anchored tests keep
    working. Byte-identical output. LAST in the stage, after item 12.
    DONE 2026-10-03 in #265, now rather than "when the next page-sized
    feature starts" (Mark's call). `src/dashboard/page.html` includes
    `styles.css`, `body.html` and `app.js`; `src/pipeline/template_parts.py`
    joins them and `tests/template_source.js` is the JavaScript twin. The
    joined text and the built page were byte-identical to main's; every
    mutation case on the old file was retargeted to its part, 536/536
    CAUGHT. `app.js` is still one large part: splitting the script further
    would be new work, not this item.

**Stage 33 is finished (2026-10-03).** Every item is done or answered.

### Stage 34 - Front door and the last points

27. Tags `v2.0` to `v2.5` from `VERSION_HISTORY`, a GitHub Release each, and
    the Website field. Mark's say-so; he said "later" on 2026-09-29.
28. Put the collector-on-merge alternative to Mark with its numbers, and accept
    his answer (he chose to keep it on every push on 2026-09-29).
29. A `<caption>` on every data table; the Power Ratings `#` header either
    sortable or styled unlike the sortable ones.
30. A committed synthetic "states" week that the browser checks render on
    every CI run: a tie, a skipped week, a stale preview.
31. Redraw the share image with the final name; a PNG favicon and Apple touch
    icon made in the cloud sandbox and moved as base64 (the file bridge
    corrupts binaries).
32. Then Stage 20's five real-person tests, and the re-audit: re-run
    `dashboard-design-audit` and the same senior audit prompt against the new
    `main`, so the score rests on a command and an independent read.

## Stage 35: the 2026-09-30 third audit (planned 2026-09-30)

The third independent senior audit scored the repository 83/100 on
2026-09-30 at `cf14efa` (after #214 to #248), up from 78 and 71. It read the
Audit Response Log and accepted every earlier decline on its reason. Its new
findings are Stage 35; the rest of its plan is the queue already scheduled
in Stages 32 to 34. Stage numbers stay frozen at 35.

Checked against the Response Log before planning. One finding re-raised a
logged decision in part: `weekly_summary`'s regexes, left alone in item 15
because they read git paths, not file stems. The new reason it gave is real
(`src/pipeline/paths.py`'s docstring claims all four copies were unified), so the
docstring is fixed and the regexes stay. The audit's after-lock queue
dropped ruff `I` and `UP` (item 18's tail); kept.

Rules, on top of CLAUDE.md's PR loop and Stage 30's: one item, one PR; a
PR touching the weekly pipeline merges only after Thursday's lock is seen
to run, except item 1, which Mark approved as the exception on
2026-09-30; every guard gets a mutation case run by `--id`; every
mutation claim names its case files.

### Stage 35 - Fixes from the third audit

1. The lock run's summary crashed on the preview the lock deletes (#237
   made `save_week` delete a tracked file, and the summary read every
   `git status` line). Reproduced before the fix. DONE in #249, merged
   the day before the first lock on that code. The picks were never at
   risk (the commit step and Pages both run after a failed Weekly
   update); the cost was a false red on the one run whose red means
   "Thursday night's game may be unpicked".
   1b. The audit-log collector pushed `main` with no catch-up step. DONE
   in #250, split from item 1 as not deadline work. The guard now finds
   every workflow with a `git-auto-commit-action` step instead of naming
   two, which is why this one was missed. Its first run after the merge
   went green through the new step.
2. The CI tie page tagged all 16 cards "Tie" from each Thursday lock to
   Tuesday's grading (it graded the raw picks of an ungraded week), and
   the checker counted JSON, not rendered tags. Also the scoreboard threw
   on a null `pct` (every graded game a tie) and its eyebrow printed the
   market row's decided count under "games graded". The tie rule was
   already recorded in #235 (`tests/test_tie_rendering.py`): a tie is
   graded and decides nothing. So the eyebrow now prints
   `accuracy.n_graded`, the calibration text's count. Branch
   `s35-tie-state`.
3. Stage 32 remnants, split by whether the weekly run executes them:
   (a) the stored drift baseline (#254), (b) the pipeline remnants (#253) (five stale
   `main()` comments, `@overload` on `build_team_ratings`, `return None`
   in `plan_week`, advisory mypy, the two `split('_week')` callers), both
   after the lock; (c) the rest (`tasks.py browser-check` and
   `runs()` reading `run: |` blocks, the top bar's observer on
   `border-box`), which touch no pipeline code.
   **The baseline, decided 2026-09-30 (Mark asked for the analysis, not a
   scope limit).** `config.BACKTEST_ACCURACY` was a literal typed in with
   the first upload (0.628 and 0.682: 683 and 741 of 1087 games), one game
   off each way from `data/calibration.json` (682 and 742), which the page
   and README print. So the drift issue, public on GitHub, quoted a
   baseline printed nowhere else, and nothing but a hand-dispatched
   reproducibility audit compared the two. The literal's own rule --
   "fixed, documented, not automatically recomputed" -- guards against a
   baseline computed from LIVE data. `calibration.json` is not live: one
   commit in its history, rewritten only by a deliberate
   `src/research/calibration.py` run, and already tied to model releases by
   `tests/test_backtest_figures_tie.py`. So the drift check reads its
   baseline from `calibration.json` and the literal goes; the rule is
   reworded to what it protects (the baseline is the committed backtest
   artifact, never a live recomputation, and moves only when that file is
   deliberately regenerated). Stage 33 item 24 needs the same reader for
   a log-loss baseline, which the file already carries.
4. DONE 2026-10-01 (run 36898525753, `c80cb28`). Watch Thursday's lock run (2026-10-01): started, locked week 4 before
   the 00:15 UTC Friday kickoff, deleted the preview in the same commit,
   wrote its summary with the new "Preview for 2026 week 4 removed" line,
   and pushed.

Then, in order: Stage 32 item 14 (packages), ruff `I`/`UP`, Stage 33 item
23 (line snapshots), items 21, 22 and 24 as registrations shown to Mark
first, item 26 when the next page-sized feature starts, then Stage 20 and
the fourth audit. (Item 26 went in early, on 2026-10-03, by Mark's call:
#265.)

## Stages 36 to 41: the 2026-10-04 fourth audit (planned 2026-10-04)

The fourth independent audit scored the repository 86/100 on 2026-10-04 at
`6af07c7` (after #249 to #265), up from 83, 78 and 71, with no regressions.
It proposed Stages 36 to 39 and 25 forward items. Every item was checked
against the code before it became one of the items below; the verdicts and
reasons are in the Audit Response Log. Mark approved this plan 2026-10-04.

**Corrections to the audit, so they are not re-litigated:**
- The week-4 lock (2026-10-01, `c80cb28`) ran on the code from before
  #255 and #258. The first scheduled run on the packages, `MODEL_SPECS`,
  the log-loss drift check and the template parts is Tuesday 2026-10-06;
  the first LOCK on them is Thursday 2026-10-08.
- (Withdrawn the same day.) The review first said seven registry entries
  were missing from Model Lab. Six of them (Stage 5 H11; Stage 6 N2, N3,
  A1, R2, A2) are off the page by Stage 18's decision, held by
  `test_every_result_file_is_an_entry_once_and_nothing_unasked_is`: never
  run, so no decision to show. Only Stage 33's R4 is a gap, because only
  Stage 33's registry promises a row for every question. The audit was
  right.
- The MNF closing line is not lost: nflverse keeps it after the game. What
  is lost is the MNF final score on the page.
- Neutral sites are a regular-season question, not a Super Bowl one: eight
  2026 games, and nothing in `src/` reads the schedule's `location`.
- Playoff pick'em points need nothing: `confidence_points` is `n - i` for
  any n, and bye weeks already vary n from week 5 (Mark agreed).
- Worst scheduled-start delay so far is 6h35m (canary); the weekend
  refresh's worst is 6h19m, not 5h51m.

**Decided:** the audience switcher is not built; the current state stays
(Mark, 2026-10-04). Two rendered options may be shown later, under Stage 22.
Releases per `MODEL_VERSION` are in (Mark, reversing "later").

Rules, on top of CLAUDE.md's PR loop: one item, one PR; anything touching
the weekly run or the weekend refresh merges only after the 2026-10-08 lock
is seen to run; every guard gets a mutation case run by `--id`; every
mutation claim names its case files.

### Stage 36 - Loose ends

1. The `sys.path.insert(0, ROOT)` lines made dead by `pyproject.toml`'s
   `pythonpath`, then ruff `RUF100` once (262 of the 265 unused `noqa` are
   E402 behind those lines; keep `weekend_refresh.py`'s real F401). Three
   stale comments (`generate_dashboard.py` sys.path, `requirements-dev.txt`
   "pyflakes only", `run-backtest.yml` naming `calibration.json` as the
   drift baseline) and `conftest.py`'s unused `GENERATOR`.
2. Stage 33's R4 gets its Model Lab row (a monitoring rule: ADOPTED, shown
   as ACCEPT), with a test that a registry promising a row for every
   question gets one.
3. The type-check test fails under `CI` instead of skipping.
4. A test that each `run-backtest.yml` option resolves to a real module.
5. The lateness margin in `tests/test_weekend_refresh.py` reads
   `LOCK_SLACK`; backup files under `src/dashboard/` are gitignored. The
   strict folder check stays (pushback: Pages builds from a clean checkout).
6. Booth's prompt: do not re-read CLAUDE.md or BOOTH_PROTOCOL.md after the
   stash. Booth skips PRs that edit its workflow; merges on Mark's say-so.
7. `tv_channels.main`'s folder defaults come from `paths.py`, and `COPIES`
   catches a `ROOT / 'predictions'` default. After the 2026-10-08 lock.
8. `docs/traps.md`: a short rules index at the top and a size guard.

### Stage 37 - The honest states

1. My Picks: "0 counted -- N late, M untimed" on the scoreboard, the trend
   chart and the My Picks page, with the export/import hint. The kickoff
   lock stays.
2. Week Board: "regional" on Sunday-afternoon CBS and FOX pills; one header
   per kickoff slot under the chronological sort only.
3. The weekly run refreshes the game status of the week it grades, in the
   same commit, so Monday night's score reaches the page; backfill the
   week 1 to 3 snapshots. (Not a fourth cron.)
4. Line snapshots append when the line changed, with a `captured_utc`.
5. Methodology: what the page deliberately does not show.
6. A card note on neutral-site games.
Items 3 and 4 wait for the 2026-10-08 lock.

### Stage 38 - Registrations written now

Family `stage38`, two confirmatory slots (97.5%): C1 an offseason gap in
the team ratings (item 8; all weeks decide, weeks 1-4 reported); B1
week-block bootstrap over R1-R3 and the published comparisons (item 13,
measurement); M1 live reliability against the backtest (item 14, printed,
no alert); L1 market at the lock against market at the close (item 17,
measurement); L2 line movement toward the model (item 17, slot). The
neutral-site home term is Mark's methodology call (a test at four or five
games a season cannot decide it). Drafts are in `memory/2026-10-04.md`;
shown to Mark before any registry file is written.

### Stage 39 - Ready for the playoffs (by mid-December)

1. The synthetic league as named scenarios with asserted outcomes, first:
   a tie, a cancelled game (NaN scores), a neutral site, a postponed game,
   playoff weeks 19 to 22 and an empty week 23, a Wednesday game, the
   week-12 Thanksgiving slate, the Friday Christmas games, Saturday games.
2. Round names and `game_type` carried into saved picks and the week
   stepper (week numbering already walks 19 to 22).
3. `check_build` and "every game started" semantics for 6, 4, 2 and 1-game
   weeks.
4. Ratings use regular-season plays only, so they freeze through the
   playoffs: disclose it, or register a change (Mark's call).
5. Playoff TV: sourced `data/tv/exceptions.json` entries in December, and a
   canary rule that they exist before week 19.
6. Bracket status in place of the simulation once `games_remaining == 0`.
7. A test that every scheduled game gets a status refresh after kickoff.

Item 1, first part (2026-10-04): `tests/test_league_scenarios.py` holds the
postponed and the cancelled game. Found while writing it: a cancelled game
reads "started" on the Week Board for the rest of the season, because
`weekend_refresh.game_status` has no state for a game that kicked off and
will never have a score. Not asserted either way; a "no result" state is
Mark's call, and it touches the weekend refresh, so after the 2026-10-08
lock in any case. **Mark's call (2026-10-05):** the card stays with a
"Cancelled" label; its pick is shown but not graded, and is left out of
every count and accuracy figure. Built after the lock.

### Stage 40 - Season turnover (January)

`docs/season-turnover.md` and `tasks.py turnover` (item 7); the 2026
forward test archived as `experiments/forward-2026/` with a Model Lab row
(item 9); the "season not started" state (10); My Picks per season (11);
the season in links and routes (12); whether R4's drift sample resets per
season or per `MODEL_VERSION`, decided before week 1; C1, L1 and L2 run
before the turnover.

### Stage 41 - Operations and releases

1. (Moved to Stage 42, item 1.)
2. Booth's run fails when its prose header and verdict block disagree (28
   of 322 reports did).
3. `tasks.py release`: a GitHub Release per `MODEL_VERSION` from
   `VERSION_HISTORY` (Mark: yes, 2026-10-04).
4. A "last 30 runs" table on Checking the AI's work, built from the public
   Actions API at page build, not a file every workflow commits.
5. Per-source reachability in the canary. Locking on a cached schedule is
   declined: the cached spread would silently change Model B's input.
6. A designed two-letter team tile shown beside today's fallback (the logo
   canary is declined: CI already proves the page works with ESPN blocked).
7. `data_provenance` in each saved pick.

**Order:** Stage 36 now (items 6 and 7 as noted); Stage 42 next (Mark
called the delays significant); Stage 38's drafts to Mark; Stage 37 after
the 2026-10-08 lock; Stage 21 when week 5 is graded; Stage 44 after 42,
then Stage 43; Stage 39 before December; Stage 41 when a week has slack;
Stage 40 in January. Items 18 to 21 and the audience switcher's rendered
options go to Stage 22.

### Stage 42 - On-time runs (Mark, 2026-10-04)

Mark: "preferably no delay at all", and the delays are significant.

GitHub's `schedule:` trigger is best-effort. Runs here started on time
until 2026-09-22 and 3.5 to 6.5 hours late since; `workflow_dispatch` runs
started within seconds throughout (2026-09-29). Nothing in Stages 36 to 41
prevented the delay, so this stage replaces the trigger, not the runner.

1. Every scheduled workflow records its start delay (cron time against
   `run_started_at`) in its summary, and warns at 7 hours (`LOCK_SLACK` is
   8). This was Stage 41 item 1.
2. cron-job.org (Mark's pick: a web page, nothing to deploy) sends
   `workflow_dispatch` for the Weekly update, the three weekend refreshes,
   the canary and the nightly mutation slice at their cron times. A
   fine-grained token for this repository only, Actions read and write,
   with an expiry; Mark creates it and the cron-job.org account, walked
   through step by step.
3. GitHub's own cron stays as the fallback. A `concurrency` group per
   workflow so the dispatch and a late cron run never overlap, and a test
   that a second run of the same slot changes nothing (a locked week is
   never rewritten; a refresh with nothing new commits nothing).
4. A missed dispatch is seen: cron-job.org's failure e-mail when GitHub
   refuses a request (an expired token, say), and item 1's delay line on
   the run that did start.
5. After four on-time weeks, `LOCK_SLACK` is revisited (Mark's call).

### Stage 43 - Spotter, the visual inspector (Mark, 2026-10-04)

A third agent, beside Scout and Booth. On every PR that changes the page
(`scout_preflight.page_files()`), Spotter builds the page, screenshots the
pages the diff touches at 390 and 1280 px in both themes, attaches the
images to the PR, and reads them against the repository's visual rules.
"Render it and look at it" stops being a process note.
1. Design and permissions: read and comment only, stated as Booth's are.
2. The screenshot job in CI, on the Playwright already in browser checks.
3. Spotter's prompt and its protocol file.
4. A fixture PR with a planted visual defect Spotter must catch, run like
   Booth's regression suite.
5. Booth cites Spotter's images instead of marking a visual claim
   UNVERIFIABLE.

### Stage 44 - Line Judge, the run watcher (Mark, 2026-10-04)

A fourth agent. After every scheduled run (Weekly update, weekend
refresh, canary, mutation slice) Line Judge reads the run's summary and
what it committed, and says whether it did the right thing: started on
time (Stage 42's delay line), locked before the first kickoff, every game
on the page, the drift report present. A run that went green and did the
wrong thing gets a diagnosed issue through `src/pipeline/alerts.py`.
1. What "right" means for each workflow, written as checks; most become
   plain tests or scripts, and the agent explains what they find.
2. Triggered on `workflow_run` completion.
3. Issue wording and de-duplication through the existing alerts.
4. A planted bad run in the synthetic league that it must flag.
5. A weekly one-line digest.
After Stage 42, whose delay record it reads.

## Stages 45 to 49: new items for the days before the 2026-10-08 lock (proposed 2026-10-04)

Mark asked for 25 new items, by the audit's categories or as features not
yet thought of, that can be done before Thursday's lock. Each was checked
against the repository on 2026-10-04 at `0ae5df4`. None touches the weekly
run or the weekend refresh, so none has to wait for the lock. Proposed;
Mark has not approved them yet.

**Approved and worked (2026-10-05).** Mark took the recommended ten, in
this order: 23 (#282), 21 (#283), 20 (#284), 4 (#285), 25 (#286), 15
(#288), 16 (#289), 17 (#290), 19 (#291), 22 (`docs/decisions/`, straight
to main). All ten are done. Narrowings: item 4 kept collect-agent-log's
`pull-requests: read` (Booth's reports are PR comments read through the
issues API; `issues: read` alone was not verified); item 15 covered
`src/research/calibration.py` only among the research scripts, and found
the tuned constants unguarded (now `tests/test_config_pins.py`); item 16
left out `confidence_points`, which is inline in `predict_week`; item 19
is strict on `src/agents` alone (`--follow-imports=silent`). Items 1 and 2
wait for the 2026-10-08 lock because the deploy runs on every data commit;
3, 5 to 14, 18 and 24 are not started.

### Stage 45 - Supply chain and security

1. Pin the nine action references still on tags (setup-node, cache,
   upload- and download-artifact, upload-pages-artifact, deploy-pages) and
   widen `tests/test_action_pins.py` to every `uses:`. Stage 27 left them
   "for now"; deploy-pages runs with `pages: write` and `id-token: write`.
2. A Content-Security-Policy meta tag. The page loads inline code and ESPN
   logos only; nothing says so today.
3. `pip-audit` against `requirements.txt`, report-only, in a nightly job.
   The CI installs stay as they are.
4. `SECURITY.md`, and a test that every workflow declares its permissions
   and holds none it does not use.

### Stage 46 - Proof and open data

5. Proof of lock: each week shows when its picks were locked and the
   commit that locked them, linked to GitHub, read at deploy from the
   commits API (the #281 pattern).
6. A "late by" column on the runs table, from each workflow's cron lines.
7. `picks.csv`, every locked pick and its grade, published beside the page.
8. A feed (`feed.xml`) of each week's picks and results.
9. Against the market: how the models did when they picked against the
   market's favourite (check first that no page already shows it).

### Stage 47 - Accessibility and resilience

10. Forced colours (Windows High Contrast): no rule today; bars and chips
    drawn as backgrounds can vanish. Rules and a browser-check pass.
11. A print stylesheet: no `@media print` rule today.
12. A canonical link and structured data (JSON-LD).
13. A render-time budget in the browser checks beside the byte budget.
14. A web app manifest beside the existing touch icon.

### Stage 48 - Test depth

15. Mutation cases for the modules no case targets: `src/pipeline/config.py`,
    `src/pipeline/ol_continuity.py`, `src/research/calibration.py` (the
    drift baseline's writer) first, then the research scripts.
16. Property tests (hypothesis, dev only) for `market_prob`,
    `confidence_points`, `kickoff_utc` across DST, `graded_correct`.
17. The suite in random order, nightly, to find tests that depend on order.
18. A dead-code report (vulture) with an allowlist; delete outside
    `src/pipeline` now, inside after the lock.
19. mypy strict on `src/agents`.

### Stage 49 - Agents, process and documentation

20. Scout preflight: a claim that a file was "restored", "committed" or
    "tracked" names a tracked file (#278's body said "restored the tracked
    `index.html`", which is untracked).
21. A session-start doctor: the read-only checks every session opens with
    (QB routine, Weekly update's drift line, the canary), read from the
    Actions API in one command.
22. Decision records: one page each for the decisions now spread through
    this file (one-file site, two models, the kickoff lock, Booth read-only,
    cron-job.org), linked from the README.
23. Stop hand-bumping the README's case-file count: generate it, or state it
    in a form a new case file does not change. Every branch that adds one
    conflicts with every other.
24. Split this file by audit era under `docs/history/`, with an index and a
    size guard like `docs/traps.md`'s.
25. The Releases workflow also runs on a pushed `v*` tag, so a new model
    version releases itself.

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
layers, with `src/site/` the only code that sees every sport; `src/pipeline`
and `src/research` counted as the NFL until Stage 52; the lock rule per
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
5. The proof: picks, backtest, `data/calibration.json` (moved) and the page
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
(`market.py`, `goalies.py`, `teams.py`); injuries are not read yet. Item 4 (colours and logos)
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
sport's page build under an audit hook and fails on any file of another sport it opens.

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
