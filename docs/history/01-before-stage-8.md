# Before the visual overhaul

Part of the stage history; the index is `docs/stage-history.md`. Moved verbatim from
that file on 2026-10-06 (Stage 49 item 24).

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
