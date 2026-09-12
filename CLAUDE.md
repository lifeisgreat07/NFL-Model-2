# NFL-Model-2 — working context

Read this first, every session, and again after any context compaction. It exists
because a compaction on 2026-09-04 destroyed a 25-item staged plan that had been
written only into the chat. The transcript on disk begins at the compaction
summary; the original messages were not recoverable. Anything that matters
belongs in this file, not in the conversation.

## What this is

A live NFL prediction dashboard, and equally a **portfolio piece** meant to show
employers real AI/ML engineering rigour. Both purposes are load-bearing: work
that is overkill for predicting football can still be right if it demonstrates
the engineering. Public repo, so anything committed is read by strangers.

## Non-negotiable methodology

- Tune on **validation** seasons [2022, 2023]; confirm on held-out [2024, 2025].
- Close calls go to a **paired bootstrap**, 5,000 resamples. A result counts only
  when the 95% interval **excludes zero**. Otherwise it is INCONCLUSIVE, and the
  page says so.
- Decision labels: ACCEPT / REJECT / INCONCLUSIVE / DEFERRED / CONFIRMED FINDING.
  Every Model Lab row carries one.
- **Accuracy cannot carry a result at this sample size.** Confirmed finding: the
  same commit and dataset disagree by one to two games out of ~1087 between a
  Linux runner and Windows, while log loss, Brier and AUC agree to four decimals.
  Judge on proper scoring rules; treat any accuracy-only claim as suspect.
- No subgroup hunting. The 12-partition narrow-edge search already demonstrated
  what that produces on noise. New slicing needs its own pre-declared experiment.
- `VERIFICATION.md`: no claim about tests, repo state or reproducibility without
  re-executed evidence. Scout does the work; Booth verifies it independently.
- Published numbers must be tied to their data file by a test. Prose drifts;
  `tests/test_published_bootstrap_numbers.py`, `tests/test_version_history.py`
  and `tests/test_pandas_version_experiment.py` are the pattern — every figure
  printed on the page, or argued from in a comment, must exist in the artifact
  it came from.
- **Mutation-test every new guard.** Write the failure it is meant to catch and
  confirm it catches it. See the traps section — this has bitten repeatedly, and
  the mutation harness itself has lied twice.
- **Render it and look at it.** Three separate bugs on 2026-09-06 were invisible
  in the code and obvious in a screenshot. A UI change is not verified until
  somebody has looked at it.

## Current state (update this when it changes)

Model v2.4. `TRAIN_SEASONS` 2020-2025, `BACKTEST_SEASONS` 2022-2025,
`QB_SHRINK_K = 8`, `RIDGE_ALPHA = 15.0`, `RECENCY_HALF_LIFE = 16`.
Canonical `BACKTEST_ACCURACY` moves only on a deliberate re-run.

Suite: **918 passing** (1 skipped) on `main` (2026-09-12, after PR #63). Run it before quoting
it — this line read 174 for three days after it stopped being true, and a stale
figure here is the first thing a fresh session anchors on.

Keep the shape `Suite: **N passing**` exactly. `src/session_wrapup.py` greps for
that literal, and rewording it to `**N passing, 1 skipped**` did not make the
check complain about the wording — it reported the line as *missing*, which
reads like a deleted section rather than an edited sentence.

**Stages 1, 2, 3 and 7.5 are complete. Stage 7.6's repository half is done.
Stage 8's design phase closed 2026-09-10; its decisions live in
`docs/design/STAGE8-DESIGN.md` and its specification is the pair of mocks
beside that file. Stage 8b — porting the design into
`src/dashboard_template.html` — is next.**

One habit from that stage is worth keeping whatever you work on: every numeric
claim about colour or geometry was re-derived before being believed — contrast
by recomputing WCAG luminance from the hex values, colour-blind separation by
running the Machado 2009 matrices and CIEDE2000, layout by rendering in
headless Chromium and reading `getBoundingClientRect`. Three claims were false.
Two of them were mine. Reading your own CSS back is not verification.

### Start here

**Current state now lives in `docs/context.md`. Read that first — it is
rewritten every session and this section is not.** `docs/index.md` maps where
everything is; `memory/` records what each session decided and why. This file
keeps what stays true for months: methodology, stage plans, and the traps below.

Merged: #40 through #57. Stage 7.5 has cut 14 pages to **9** — Playoff Odds
became a column on Power Ratings, Roadmap folded into Changelog (renamed What's
Changed), and How This Compares, Data Sources and the Glossary became parts of
Methodology. The plain-language guard is live and its allowlist is empty.
Stage 7.6's repository half is done: the README opens on a recruiter overview
and `tests/test_readme_accuracy.py` holds it to its own claims. Its browser
half — the repo description and topics — is still Mark's to do in the GitHub UI.

**Which branches are open, and what each waits on, is in
`docs/context.md` — that file is rewritten every session and this one is not.**
Do not maintain a second list here; that duplication is what this split exists
to end. This paragraph carried a count of open branches until 2026-09-10, when
it was still claiming "no open branches at all" with one pushed and unmerged —
the duplication it warns against, in the sentence warning against it. Go read
`docs/context.md`.

**Stage 3 closed with the finding it exists to prevent.**
`src/collect_agent_log.py` was written and tested in Stage 3 and had **never
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

Two habits that paid for themselves and should carry forward: build
the page and *click the thing you just added* before opening the PR (that is how
the `#`-column defect was found — it was invisible in the diff), and when
deleting a page, ask what it was the last example of before assuming the tests
still cover what they did yesterday.

**Stage numbers are frozen.** They were renumbered twice in two days and it
confused both this file and the Progress tab. A finished stage keeps its number
and is recorded as finished; nothing is renumbered again.

### Findings that still constrain the work

Conclusions, not history. Which PR produced what belongs in the Stage 7
write-ups; what matters here is what is now settled and must not be re-opened
casually.

- **Model B vs the market is INCONCLUSIVE** on all four metrics, stated with
  intervals. Two real findings did survive: Model B genuinely beats Model A on
  proper scoring rules, and the market genuinely beats Model A. The dashboard
  says all three.
- **There is no ATS edge.** 51.61%, CI [48.58%, 54.63%] — contains 50% and does
  not reach the 52.38% break-even. The betting question was asked properly and
  answered negatively. Do not re-open it without new data.
- **`nfl_data_py` is a verified fallback**, executed rather than assumed: it
  imports, all three loaders work, every required column is present, and it
  agrees with nflreadpy exactly on 2025 week 10. So the pandas 1.x pin buys a
  working revert path rather than a theoretical one.
- **The pandas 2.x unlock is not free.** Pre-declared hypothesis — log loss,
  Brier and AUC agree to four decimals across the major version — REFUTED. AUC
  moves up to 0.00125, 25x this project's own noise threshold, with both
  environments proven deterministic and scoring the same 1087 games. "Market
  alone", the one model with no EPA aggregation, is bit-identical; everything
  built on EPA features moves, which localises it to float aggregation over
  ~48k plays a season. Keep the pin; revisit only when something actually needs
  pandas 2.x, and regenerate every published figure as part of that work rather
  than discovering the shift afterwards.
- **An audit finding is a hypothesis, not a defect.** Four of Stage 2's seven
  queued items were not the item as written. SOS was computing correctly and
  the season had not started — acting on the audit would have deleted a working
  feature for being audited in September. The Team Deep-Dive page had never
  worked at all: a missing file returned `{}` in silence while the roadmap
  listed it Done. Read the code and render the page before believing a queued
  finding.

### Stage 1 - Recurring status checks (first every session, don't dwell)

Injury/roster data is CLOSED, not blocked - settled on VALUE, not
availability, so stop re-checking nflverse for it. Ensemble contingency is
blocked solely on another independently-useful model existing. ESPN QBR stops
at 2023, quick re-check only. Public betting % has no free source; reverse
line movement is blocked downstream of it. Line-movement accumulation is
confirmed working and needs many more weeks before a real predictive test -
do not force one on a small sample. Closing-line backtest stays deferred on
that same accumulation.

### Stage 2 - Deferred UX & repo hygiene  <- COMPLETE (2026-09-06)

Shipped as PRs #21-#24. See "Findings that still constrain the work" above; the four
corrections it produced are worth reading before starting anything that
assumes an audit finding is accurate.

### Stage 3 - Agent development  <- IN PROGRESS

**Built and merged:** Scout pre-flight, which checks a PR description against
reality before it opens (`src/scout_preflight.py`, #26). A committed mutation
corpus, so mutation tables are a command rather than a throwaway script
(`tests/mutation/`, #27). A test that every regenerating workflow prunes build
churn (#28). Booth reports that record the head SHA and body read-time, and a
past-tense rule for claims about a description (#29). An `edited` trigger so a
rewritten description is re-audited at all (#30) -- demonstrated live on PR
#34 on 2026-09-07: editing the description with no manual dispatch fired a
second audit on its own. #30 shipped on a mutation test and an argument
because Booth structurally cannot audit its own workflow file, so that
live run is the evidence it could not produce for itself. A machine-readable
`booth-verdict` block plus the parser that reads it (`src/booth_verdict.py`,
#31). The regression-fixture format and its integrity checks (#32).

**Two Booth defects were found and fixed on 2026-09-07**, both invisible to any
test because they concern how a report is read rather than what it checks. It
never re-audited a description-only edit, so a body could be rewritten after
its audit while the audit comment went on looking current. And it reported a
snapshot in the present tense, asserting what "a reviewer sees right now" about
text already replaced. Fixed in #30 and #29 respectively.

**Remaining, in the order agreed on 2026-09-07:**

1. **The fixture runner — BUILT** (`src/booth_fixture_runner.py`).
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
   STILL TO DO: a `workflow_dispatch` workflow that invokes the real action,
   one fixture per dispatch. Booth runs on subscription auth, so it costs no
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

### Stage 4 - Automation & monitoring

Data-quality checks on every weekly run; play-by-play cache layer; alerts on
upstream nflverse schema changes; auto-open a PR when check_drift.py detects
real drift; nightly canary against the last completed week, which would have
caught the nflreadpy offseason crash days early; automated weekly summary;
reproducibility audit and expanded leak-free coverage. Also the alert and
communication layer for Booth, now that autonomous operation is confirmed.

Add: a **build-output smoke check**. The Team Deep-Dive page rendered empty for
months because a missing file returned `{}` quietly. A check that every page's
data payload is non-empty after a build would have caught it the same day.

### Stage 5 - Model depth, real hypotheses only

Residual analysis FIRST, since it tells you which of the rest are worth
attempting. Then market-implied probability calibration as a Model B feature;
per-team learned home-field advantage; rest and travel; weather and wind for
outdoor games; situational splits; multi-season QB priors; injury-adjusted QB
ratings, indefinitely parked with the injury data closed; learned blend weight
between Models A and B - if an ensemble doesn't beat both, that's a publishable
REJECT.

### Stage 6 - New data sources

Next Gen Stats via nflreadpy, the most promising untapped source already in the
stack; participation/personnel grouping; referee crew assignments, cheap and
testable; multi-book line dispersion, accumulation-gated under Stage 1 rather
than a new build. Each item needs a stated hypothesis BEFORE the data is
pulled, or it is fishing.

### Stage 7 - Portfolio polish

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
and allowed only on Methodology, Model Lab and the build page. A future session
adding "the model's Brier score" to Boards fails the suite. Without a guard,
this pass reverts the first time anyone writes new copy — the same reasoning as
every other guard in this repo.

**Explicitly NOT in this stage — these belong to the visual overhaul:**

- How much room week-by-week net ratings take over a season on Team Deep Dive.
  A layout question Stage 10 owns; deciding it before the Stage 8 direction
  exists means deciding it twice.
- Import/Export picks buttons staying highlighted after a tap on mobile. A
  `:focus` state persisting after touch; Stage 9's focus and keyboard pass
  covers exactly this. Fix earlier only if it is a one-liner.

**Deferred as new features, not cleanup:**

- Weekly team news on Team Deep Dive — injuries, trades, firings, releases,
  scraped and summarised briefly. This is a new external data source with
  staleness, rate-limit and reliability concerns; Stage 6 in nature, and it
  must not gate the visual work. NOTE for a future session: Stage 1 records
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

**Items 1 and 2 are still open, and cannot be done from here.** They are repository settings, not
files: no `gh` CLI is installed on the Windows machine and the GitKraken MCP
exposes no repo-settings tool. They are a two-minute job for Mark in the GitHub
UI (Code tab → the gear beside "About").

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

One live tension: everything built in Stages 2-7 uses hardcoded pixel values,
because the scales do not exist yet. That is deliberate and accepted — the
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

**Still open, and worth more than any of these tools:** Mark has not yet named a
dashboard or site whose look he wants. Ask for a concrete reference before
Stage 8 begins. A token system with no point of view behind it is just tidier
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

**What remains is Stage 8b, the port** — lifting that block into
`src/dashboard_template.html` and restyling page by page. The template is
3,250 lines across nine pages; the design was proven against two. Roughly 704
tests assert on it, several on colour tokens and exact strings. Treat a failing
colour assertion as a question, not as something to update to match: those
tests encode earlier decisions that were themselves argued for.

**The audit's foundations list is now satisfied by the token block** — spacing
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

Do the concept first. Tokens chosen to serve a direction are a design system;
tokens chosen to reduce a count are a tidier mess.

### Stage 9 - Colour, components & interaction

**A point of view on colour**, not only the removal of ambiguity. The
corrective work: retire the 33 hardcoded team-brand hex values driving
probability bars in favour of `--series` tokens — `teamColor()` falls back to a
hardcoded dark `--chalk-dim`, so it is wrong in light mode, and red-vs-blue
bars read as bad-vs-good rather than as two teams. Disambiguate amber, which
currently means brand, active nav, sorted column, flagged state and series-b at
once.

Beyond that: the Net Rating bar was deliberately left amber in Stage 2 with a
note saying sign-encoding belongs here. A diverging pair with a neutral
midpoint is the `dataviz` answer; run it through the validator in both themes
rather than picking by eye. Decide what confidence looks like, what a flagged
game looks like, and what "the model was wrong" looks like — the dashboard
currently says all three in the same amber.

Also: one button component with real variants and states; a focus and keyboard
pass paired with `design:accessibility-review`; unify the two `.game-card`
render paths.

### Stage 10 - Layout, tables & responsiveness

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

## Ending a session

Run this every time, before the session closes:

```
python src/session_wrapup.py
```

A session ends when usage runs out or attention moves, not when the work
reaches a tidy boundary. Whatever is true at that moment is what the next
session inherits -- and it inherits it through this file, cold, with no memory
of the conversation that produced it. Every wrong fact here gets believed.

That is not hypothetical. This file said "Suite: 174 passing" for three days
after it stopped being true; the real number was 382. It is the first figure a
fresh session anchors on.

**What the script checks**, because these cannot be checked continuously:
the suite count stated above against a real run; a clean working tree;
nothing committed but unpushed; and which branch you are leaving behind. It
exits non-zero if any of them fail.

**What `tests/test_claude_md_freshness.py` checks**, free, on every commit:
that every repository path and every test name this file mentions still
exists, and that the stage headings are unique and in order. A moved file
leaves a silently wrong pointer; a guard named here and absent from the suite
reads as protection that is present. Note it deliberately skips the stage
sections -- those name work that does not exist yet, and checking a plan the
same way you check a description is wrong.

**What neither can check, and matters most.** The script prints these as
prompts:

- Does "Current state" describe today -- which stage is in progress, and the
  next concrete action?
- Is every PR opened this session either merged, or recorded here with its
  number and what it is waiting on?
- Did anything surprise you? A trap entry is cheap now and expensive to
  reconstruct later. Write the durable shape, not the story.
- Did a decision get made that a future session would otherwise re-litigate?
  Record the decision AND the reasoning, or it gets re-opened.
- Are the stage sections still in the order work will actually happen?
- Is the Progress tab consistent with this file?

**Then re-read this file as if you had never seen it.** Not skimmed -- read.
Ask of each paragraph whether it changes a decision. If it only records what
happened, it belongs in a Stage 7 write-up instead. This document is read
under compaction pressure, so its length is a cost paid on every session.

## Environment and workflow

- Real clone lives on the user's Windows PC `markys` at `E:\NFL-Model-2`
  (E: drive deliberately — C: is short on space). Desktop Commander and
  GitKraken MCP plugins are available there; run tests and heavy backtests on
  that machine, not in the cloud sandbox, which has no nflverse network access.
- The cloud sandbox clone is scratch. It cannot push — the repo is not in the
  session's authorised set. Commits and pushes happen on `markys`.
- **Playwright lives in the cloud sandbox, not on `markys`.** For screenshots:
  regenerate `index.html` on `markys`, stage it into the sandbox, and drive
  Chromium there. This is the only practical way to actually look at the page.
- The full backtest takes ~42 seconds. It is not the expensive step people
  assume; run it when a question needs it.
- Production-code changes go through a PR the user reviews. Pure
  dashboard/documentation changes may go straight to main.
- **One item, one PR.** Booth flagged a PR bundling three undisclosed features:
  a reviewer approving on the description alone approves more than they think.
  If a branch grows past its title, either split it or rewrite the description.
- **`.github/` is writable from `markys`.** Editing a workflow and pushing it to
  a feature branch both work, tested rather than assumed. Not verified: pushing
  `.github/` straight to `main`. The restriction that IS real is the Claude Code
  action's own, listed under traps.
  General lesson, and the second stale belief this file carried: an inherited
  "you can't do X" with no recorded test behind it is a hypothesis. Spend the
  thirty seconds testing it before building a manual process around it.
- No `gh` CLI and no PR-body-edit tool. A PR description can be corrected only
  by the user in the web UI, so get the description right when opening it.
- `cmd` mangles multi-line `python -c` strings, and **PowerShell has no
  heredocs** — `git commit -F <file>` with a written message file, and script
  files instead of inline `-c`, are the reliable forms.
- **To actually LOOK at the built dashboard, serve it over localhost.** Neither
  browser available here will open a `file://` URL, and GitHub Pages serves
  `main`, so a branch's page appeared unviewable — which cost PR #46 and PR #47
  an honest "nobody has looked at this" disclosure each. The fix is one line,
  and both the shell and the browser pane run on the same machine:

      Start-Process -WindowStyle Hidden python -ArgumentList "-m","http.server","8765"

  then open localhost:8765/index.html in the browser pane (not backticked: the
  freshness guard reads a backticked path ending in .html as a repo file and is
  right to). Regenerate, reload, look. The
  first thing it caught was a new empty state rendering as two paragraphs of
  centred prose. Stop it with `Get-Process python | Stop-Process` when done.
  Note the screenshot tool here does not write image files, so a visual check
  is still a **process note**, never attached evidence — Booth is right to mark
  an unattached screenshot UNVERIFIABLE.

## Traps that have actually bitten

- **Reading your own code back is not verification, and the failure is
  asymmetric.** Stage 8's design phase re-derived every numeric claim rather
  than believing it: contrast by recomputing WCAG luminance from the hex
  values, colour-blindness by running the Machado 2009 matrices and CIEDE2000,
  geometry by rendering in headless Chromium and reading
  `getBoundingClientRect`. That caught three false claims from Fable — and then
  two more of my own, in code I had just written and was confident about. One
  was a CSS comment asserting three rules shared a specificity so source order
  would decide; `.brand:hover .brand-mark .spin` is four classes and the rule
  it was supposed to lose to was three, so hovering the logo froze the loading
  spinner *and* hung the logic waiting for an animation that was no longer
  running. One wrong assumption, two failures, neither visible by re-reading.
  The other generalised a width measurement taken from one table row to rows
  that carry an extra element. **Measure the specific case; specificity beats
  source order; and a claim about rendered geometry is only true after
  rendering.**
- **An animated disclosure can leak its contents into the accessibility tree.**
  Replacing `display: none` with a `grid-template-rows: 0fr` transition
  animates beautifully and leaves the collapsed content readable by screen
  readers and findable by find-in-page, contradicting the toggle's own
  `aria-expanded="false"`. `display: none` had been doing that job correctly
  and the animation quietly removed it. Fix: `visibility: hidden` on the inner
  wrapper with `transition: visibility 0s linear var(--dur-slow)`.
- **A wholesale `innerHTML` re-render silently destroys interaction state.** An
  open breakdown vanished on a filter change. Whatever the user has toggled
  must live in `state` and be re-derived on render, and floating UI (tooltips,
  popovers) must live outside the rendered tree entirely. Worth naming because
  the same deliverable that recommended this rule did not follow it.
- **Naming a path in `docs/context.md` that does not exist fails the suite.**
  `tests/test_workflow_docs.py` parses these documents for path-shaped strings
  and asserts each one exists, and separately asserts `memory/README.md` lists
  every file in `memory/`. Both fired within a minute of a wrap-up commit that
  pointed at files delivered into a chat rather than committed. The guard is
  right; fix the doc, do not reword around it — and if the answer is that the
  files should not be in the repo, say so in the doc instead of implying they
  are coming.
- **A safeguard written down twice, both times as a benefit, hid what it broke.**
  A push made with the default `GITHUB_TOKEN` cannot trigger another workflow.
  The collector and the dashboard builder both documented that rule as loop
  protection, which it genuinely is. Neither noticed it also severs the
  handoff between them, so the collector wrote 44 audits to `main` and the page
  went on saying "The record has not been collected yet". Fixed with a
  `workflow_run` trigger and guarded by
  `tests/test_generated_data_reaches_the_page.py`. **Ask what a safeguard also
  prevents.** *(The builder was the Auto-regenerate dashboard workflow; Stage 8c
  phase 2 deleted it and moved the trigger to the Pages workflow. The guard
  moved with it — that is what the test is for.)*
  Note the general shape too: a step that runs, produces correct
  output, and has nothing downstream consuming it — the same shape as the
  collector itself having never run, one link further along.
- **Correct arithmetic on absent data still produces a lie.** Season Accuracy
  showed 64.3%, three flat trend lines, and a row reading zero-of-zero. Every number
  was computed correctly from what it was given. 2026 Week 1 had been graded
  before it was played, so an empty week became a row that reads "we got none of
  none right" and a second point for the chart to draw to — and underneath, the
  entire page rested on one week of the *previous* season. The `return {}`
  entry below is the same failure; this is what it looks like on a page.
  Absent inputs must be dropped where the data is built, not filtered downstream.
- **A sign error in generated prose is invisible.** The Week Board's
  "the betting line agrees" shipped on all sixteen cards with `spread_line`'s
  sign inverted — it is positive when the HOME team is favoured, and the card
  displays it negated, football-style. "Agrees" reads exactly as well as
  "disagrees". Caught only by loading the page and noticing the sentence
  contradicted the card's own Vegas line two inches above it. **The convention
  was already written down**, in `tests/team_dive_harness.js`; it was got wrong
  by assuming rather than reading. When copy is generated from signed numbers,
  execute it in a harness with mirrored inputs — `tests/test_why_words.py` does.
- **Renaming a piece of UI leaves references behind.** Retitling the Week Board
  toggle orphaned its own reset label, a line in the onboarding banner, and a
  sentence in Methodology. Third instance of this shape, after the mobile nav
  still listing Playoff Odds. `git grep` the old string before considering a
  rename finished.
- **A guard can ban a term and miss its abbreviation.** The jargon list held
  "confidence interval" while `95% CI` sat on the Week Board's every card.
  Anchor the abbreviation to a phrase that cannot false-positive (`95% ci`, not
  a bare `ci`) — a guard that cries wolf earns an allowlist entry and then gets
  ignored, which is worse than the leak.
- **Two CI jobs can disagree about the same commit, and the green one wins by
  default.** `run-tests.yml` was red on every pull request for days while
  `booth-pr-audit.yml` ran the identical suite green on the identical commit.
  Nobody investigated, because Booth is the job that gets read. The cause was
  the actions/checkout default of `fetch-depth: 1`: sixteen tests here read real
  git history and skip without it, and one — `test_scout_preflight.py`'s
  exit-code test — built its fixture from the last three non-merge commits,
  found one, manufactured nothing, and failed on its own empty fixture. Both
  workflows now set `fetch-depth: 0` and that test skips instead of failing.
  **A red check you have learned to ignore is worse than no check.** When two
  jobs disagree, the difference is in the workflow files, not the tests.
- **A green checkmark on a Booth run means Booth posted a report, not that the
  report was favourable.** The workflow exits 0 whenever the audit completes.
  The verdict is in the comment text. PR #45's third audit was green in Actions
  and read NEEDS HUMAN REVIEW with four discrepancies.
- **The `edited` trigger on `booth-pr-audit.yml` fires for the PR description
  only, and its `if:` guard additionally requires `github.event.changes.body`.**
  Editing a *comment* in the thread raises `issue_comment`, which that workflow
  does not listen to — so nothing starts and nothing explains why. If an audit
  seems not to fire after an edit, check whether the edit went into the
  description box at the top or a comment below it.
- **A document can point at a file that has never existed, for months.**
  `METHODOLOGY.md` was cited by the README's fifth line and two `src/`
  docstrings; `git log --all --diff-filter=A -- METHODOLOGY.md` returns nothing.
  `src/tune_qb_shrink_k.py` had already noticed and written it down, which fixed
  nothing, because a note is not a check. `tests/test_readme_accuracy.py` is now
  the check.
- **A guard whose rule names a forbidden string will match its own docstring.**
  Third occurrence this session. Exclude the file that states the rule, and say
  so in a comment — the alternative is describing the banned string obliquely
  enough to dodge your own regex, which damages the rule to protect the checker.
- **`git reset --hard` and `git checkout --` have destroyed in-progress edits
  three times.** Before any restore, check what is uncommitted; prefer
  re-applying a known edit over reverting a whole file. When mutation-testing a
  file that holds uncommitted work, restore from a byte-level backup taken in
  the script, never from git.
- **A guard wired into one of several paths reads as a guard that is present.**
  A churn pruner stopped the workflows committing their own build timestamps.
  It ran in only one of the two workflows that regenerated, and this file's
  prose said merely that it "prevents" the churn — which is what stopped anyone
  checking coverage. Both ran it after that, enforced by a test asserting that
  *any* workflow regenerating and committing those artifacts pruned between the
  two steps, so a third would inherit the guard instead of quietly missing it.
  The durable shape: prose names a protection but never its coverage, and the
  gap is invisible from the description alone. Ask which paths, and prefer a
  test that enumerates them over a sentence that asserts them.
  *(Both the pruner and that test were deleted in Stage 8c phase 2 — untracking
  index.html removed the churn entirely, so the guard had nothing left to
  guard. `tests/test_workflows_do_not_commit_build_output.py` now asserts the
  stronger invariant that no workflow commits those paths at all. The lesson
  above is kept because it is about prose and coverage, not about that file.)*
- **A zero-line binary diff is not automatically churn.** An auto-commit
  showing `dist/picks_2026_week1.pdf | Bin 3802 -> 3802 bytes, 0 insertions,
  0 deletions` looks exactly like the timestamp churn above, and on 2026-09-07
  I nearly reported the guard as broken on that basis. It was not.
  The pruner deliberately did NOT normalise the "generated
  `<date>`" line printed inside the picks PDF, because that is visible content
  on a page someone prints — a rebuild on a different day is a REAL change and
  should commit. The byte count is identical because a date string is the same
  length either way. Its docstring says all of this. Read what a normaliser
  deliberately excludes before concluding it failed; the symptom of "working
  as designed" and "broken" are byte-identical here.
- **A date recalled is a date invented. `git log` is three seconds away.**
  Writing the churn guard into `weekly-update.yml` on 2026-09-07, I annotated it
  "same guard the other workflow has run since 2026-08" — from memory, into
  a permanent code comment, in the same PR whose other half exists to correct an
  unverified inherited claim. It was 2026-09-04. The same wrong date went into
  two sentences of this file and into the commit message. Booth caught all three;
  `git log --format="%h %ad %s" --date=short -- <path>` confirmed it in one call.
  Provenance claims — when something landed, how long a file has said a thing,
  which commit introduced a behaviour — feel like recall and are actually
  queries. The tell is the phrasing: "since", "has always", "was originally".
  Any sentence carrying one is a claim that must be looked up before it ships,
  and note that a claim about what *this file* has said is dated by this file's
  own history (created 2026-09-05), not by the history of the thing described.
- **A number in prose is a claim, and prose has no test.** One habit produced
  four wrong figures on 2026-09-07, in four distinct ways. They are worth
  separating, because only one of them looks like carelessness:
  1. *Recalled, never measured.* "The guard has run since 2026-08" — it was
     2026-09-04. Written from memory into a permanent code comment, inside the
     PR whose other half existed to correct an unverified inherited claim.
  2. *A conclusion reported as a search result.* Correcting that date, I
     searched the two paths I already had in mind, found nothing further, and
     wrote "corrected everywhere". Booth found a third occurrence in a
     docstring, in a file the same branch had just added.
  3. *A judgement wearing the precision of a count.* "72 of the 73 matches
     were real history" — which ones count as history is editorial, and the
     phrasing left an auditor no way to tell which was excluded. Name the
     exception; never publish a subtraction.
  4. *Measured, and still unreproducible.* "The Playoff Odds page is 979
     characters" came from a real slice — that page's `id=` attribute to the
     next page's `id=`, a span running past the closing `</section>`. The
     element is 953; the visible text is 585. Booth measured six plausible
     ways and got none of them, correctly.

  Only the two that reached a re-runnable check were caught before shipping.
  Commit messages have no such check and cannot be corrected without
  invalidating the Booth reports written against those SHAs, so the discipline
  has to happen before the commit, not after.

  **The rule.** A figure ships with the command that produced it, and a
  completeness claim cites a repo-wide search rather than the paths you
  happened to think of. A number whose method is unstated is unfalsifiable by
  anyone but its author — the same defect as not measuring at all.

  **The self-referential case.** A count of something its own sentence is part
  of must name the commit it was taken at. `git grep -n "2026-08"` returned 73
  matches across 12 files at `f482f4f`; every one is a real historical date
  except the line in this file quoting the mistake. A live figure written here
  would be wrong the moment it landed, because this paragraph contains the
  string.

  **None of it was catchable by a test.** All four are claims *about* the code
  rather than behaviour *of* it, and the suite was green throughout. Two
  independent Booth runs reached the docstring finding separately. That is the
  clearest evidence yet that Booth does something a suite structurally cannot,
  rather than agreeing with what it reads.
- `backtest()` calls `dropna(subset=features)`, so different feature sets can
  silently evaluate different game sets. Any paired comparison must verify the
  row sets match rather than assume it (`bootstrap_brier_gap.py` does, and
  `compare_pandas_versions.py` checks it before reading any metric).
- `home_margin` exists in the feature table for ATS work and must never enter a
  feature list — it is the scoreline being predicted.
- **Booth's audit sandbox can check out a file one commit behind its own HEAD.**
  Flagged in two separate audits (PRs #28 and #29), so it is the environment
  rather than a one-off. `git status` shows `CLAUDE.md` modified, the on-disk
  md5 matches `HEAD~1`, and `git reflog` records no second checkout — the
  working tree is simply not what HEAD says it is. Booth handled it correctly
  both times, verifying against the commit object (`git show HEAD:CLAUDE.md`,
  `git grep <rev>`) and saying so in the report. Consequence for a reader: a
  plain `git grep` run in that sandbox can disagree with a claim that is true
  of the commit. This is NOT a regression and NOT something a PR caused; do not
  spend a session chasing it. Verify against revisions, not the working tree,
  whenever the two could differ.
- **The Claude Code action refuses to run when a PR's copy of its workflow file
  differs from `main`'s.** It skips with a *success* status and a validation
  message, which looks like nothing happened. This is a security control, not a
  bug. Consequence: after changing `booth-pr-audit.yml` on `main`, any open PR
  must merge `main` in before Booth will audit it, and "re-run the job" does not
  help, because a re-run replays the original workflow definition.
- **The mutation runner's restore does not survive the process being killed.**
  It restores in a `finally`, which covers exceptions but not a hard kill. The
  Desktop Commander bridge cuts a command off at ~60 seconds and a full corpus
  run takes longer, so a run started in the foreground gets killed partway and
  leaves whatever case was in flight applied to the working tree. On
  2026-09-07 that left `src/scout_preflight.py` mutated and the next suite run
  reported 8 unrelated failures. Two rules: run the corpus as
  `python tests/mutation/runner.py > <file> 2>&1` and read the file afterwards,
  never in the foreground; and after ANY interrupted mutation run, check
  `git status` before believing a test result. A `git checkout -- <one file>`
  is the right repair once the diff is confirmed to be only the mutation.
- **Anything under a Booth fixture tree must be excluded from pytest
  collection.** `tests/booth_fixtures/conftest.py` sets
  `collect_ignore_glob = ['*']` for exactly this. A fixture is a deliberately
  bad PR: the moment one seeds a genuinely failing test, a collected fixture
  fails the real suite. It bit in a subtler form first — pytest imported a
  fixture's `test_guard.py`, created a `__pycache__` beside it, and the
  loader's tree walk then read a `.pyc` as UTF-8 and failed five fixture tests
  for a reason unrelated to anything they assert. It reproduced ONLY in the
  full suite; in isolation nothing collected the file and everything passed.
  A failure that appears only alongside everything else is the expensive kind,
  so the loader skips generated directories independently of the conftest.
- **Mutation cases live in `tests/mutation/cases/*.json` and run via
  `python tests/mutation/runner.py`.** Do not write a throwaway mutation
  script: every PR before #27 did, threw it away, and left a mutation table
  nobody could replay. Booth said so on PR #26. Add a case, run the id, quote
  the command. `tests/test_mutation_corpus.py` keeps the anchors from rotting
  on every ordinary suite run, and proves the runner can still report failure.
  A case must name the test it expects to be caught by; a mutation caught by
  a *different* guard is reported WRONG-GUARD, because the intended guard is
  then still untested.
- A guard whose comment claims more than its code delivers has now appeared
  **five** times: the leak test that flagged a `dropna` subset, the "superseded
  figures" check that banned its own honest disclosure, the "quotes the
  reproduced figures" check that passed a half-revert, the changelog date guard
  that was never reached because an ordering guard fired first, and
  `compare_pandas_versions.py` asserting determinism in its verdict text without
  checking it. **Mutation-test every new guard**, and check WHICH assertion
  caught the mutation — if it is not the one you intended, the intended guard is
  still untested.
- **A stale `.pyc` makes a mutation harness lie.** Several mutations preserve
  file size (`2.4` → `2.5`, `2026` → `2126`), and bytecode invalidation keys on
  size plus a one-second-granularity mtime. Written milliseconds apart, Python
  reuses the previous case's bytecode, and mutations report CAUGHT while showing
  the *previous* case's failure message. Clear `__pycache__` and run with `-B`
  in any mutation script.
- **A silent `return {}` on a missing file hid a broken page for months.** The
  Team Deep-Dive page rendered empty for all 32 teams because the history file
  was in the wrong directory and the loader said nothing. Every missing-input
  branch must say something.
- **Graded prediction files store `1`/`0`, not `true`/`false`.** A `=== true`
  comparison against them is quietly false. Normalise at the boundary and keep
  null as null, so "not graded yet" cannot collapse into "wrong".
- **A screenshot that is not attached is not evidence.** Booth marked the same
  visual claim UNVERIFIABLE three times across one PR because the images existed
  only in the working session. Attach them, or state the claim as a process
  note rather than proof.
- **Changing only a URL fragment does not reload the page.** A share link pasted
  into a tab that already has the dashboard open runs no init code; it needs a
  `hashchange` listener. Test a receive path as a genuine second visit, not as a
  fresh page load.
- **A regex anchored on a bare class name also matches the CSS that defines
  it.** `tests/test_dashboard_charts.py` matched `srs-bar-track(?P<cls>[^"]*)"`,
  which hit the *stylesheet* rule declaring the class and then hopped forward
  into the first real bar — one phantom "bar" whose class list was a wall of CSS
  (containing the word `diverging`, so it passed) and whose `left:` had been
  read off a different element entirely. The count guard beside it asserted
  `len(bars) >= 3` and was satisfied by that phantom for as long as it existed.
  Deleting the Playoff Odds page dropped the count to 2 and only then exposed
  it. Two durable lessons: anchor markup matchers on `class="`, not on the class
  name; and **a count assertion validates the number of matches, not their
  identity** — a matcher can drift onto the wrong thing and still count high.
- **Deleting the only input that reaches a branch silently untests that
  branch.** The zero-line rule has two halves — a left-anchored magnitude bar
  must NOT wear `.diverging`, a signed bar must. Playoff Odds was the only
  left-anchored bar on the dashboard, so removing that page left the first half
  unreachable with every test still green. The fix, and the pattern to reuse:
  state the rule as a plain function, then check it twice — once over whatever
  the page really contains, once over a parametrized table of synthetic inputs
  that keeps both branches alive regardless of what the markup holds this week.
  **When deleting a page, ask what it was the last example of.**
- **A mutation case's `tests` must name exactly ONE pytest path.** Two paths
  with a space between them load fine, reach pytest as a single nonexistent
  filename, and pytest exits non-zero having reported no failures — which the
  runner reads as "the suite went red but the named guard passed" and prints
  WRONG-GUARD. The verdict blames a guard that is perfectly healthy and the
  obvious next move is to go and edit it. `tests/mutation/corpus.py` now refuses
  it at load time with a sentence naming the actual mistake. For a second test
  file, give that individual case its own `tests` key.
- **Adding a way to sort a table can make an existing column start lying.** The
  Power Ratings `#` was the row's index in the current sort. That was harmless
  while net rating was effectively the only sort anyone used, and the comment
  beside it already claimed the number was the team's "real league position" —
  true only by accident. The first click on the new Playoff Odds header printed
  **"#1 Cincinnati" next to a negative net rating, on a page titled Power
  Ratings**. Found by rendering the page and clicking the new control, not by
  reading the diff. The rank is now computed once in Python from the net order
  and travels with the team. Durable form: **a new control does not only add
  behaviour, it reaches states the old code was never asked about** — after
  adding one, exercise the page through it and re-read every neighbouring
  claim, in prose and in cells, that was only ever true in the default state.
- **This dashboard has TWO navigations, and deleting a page from one leaves a
  dead tab in the other.** The desktop sidebar (`.nav-btn`) and the mobile
  bottom-nav "more" sheet (`.bnav-more-item`, `.bnav-item`). PR #40 deleted the
  Playoff Odds page and its sidebar button and shipped to main with the mobile
  tab still there, opening a blank screen on a phone. The desktop render looked
  perfect and every test passed. `test_every_nav_on_the_page_agrees_on_which_pages_exist`
  now asserts that every `data-page` target has a matching `<section>`, stated
  as a set relation so the next deletion is covered without anyone remembering
  this. **Deleting a page means deleting every control that reaches it — grep
  `data-page`, do not grep the nav you happen to be looking at.**
- **A guard that reads the source FILE counts commented-out markup as present.**
  Two of the strongest new guards — the ones asserting the build record had
  survived a merge — both SURVIVED their mutations: one because wrapping the
  whole grid in `<!--` left the regex matches intact, the other because the
  title it searched for also appears in an unrelated nav label, so
  `title in page` stayed true with the card renamed away. Strip comments and
  match the ELEMENT you mean, not a substring of the file. Both were caught by
  mutation testing and by nothing else, which is the argument for the harness.
- **A plan in this file is a hypothesis about code, and this one was wrong.**
  The Stage 7.5 entry asserted the Roadmap's Done list duplicated the Changelog.
  Checking took one script and found ~3 of 16 overlapping; the rest existed
  nowhere else. Three earlier inherited claims in this file were also wrong (the
  "no PR-body-edit tool" line, the SOS "defect", the Team Deep-Dive "Done"
  status). **Before executing a deletion this file plans, verify the premise
  the plan rests on, and record the correction beside the original.**
- **A PR description is a separate artifact from the code, and fixing one does
  not fix the other.** Booth flagged a wrong count in #44's description. The
  response was to correct the code comment and add a CLAUDE.md entry — both
  real improvements, neither of them the thing under audit. The next run said
  it plainly: *"Fixing a code comment does not fix a GitHub PR description;
  those are different artifacts, and only one of them was touched."* A
  description cannot be corrected by a commit, and there is **no MCP tool to
  edit one** — GitKraken exposes `pull_request_create`, not update. So a
  description fix is always a hand edit by Mark: give him the exact replacement
  text rather than a description of the change.
- **Booth reads the description ONCE, at a timestamp it records.** Its header
  says `Description read at: <time>`. Edit the description after that moment
  and the report is stale, not wrong — it will flag a discrepancy that is
  already fixed, and re-reading the same report looks like the fix failed. On
  #44 the read was 22:17:12, the post 22:25, and the edit landed between them.
  **Before treating a repeated finding as unresolved, compare that timestamp to
  when the description last changed.**
- **When one number moves for two different reasons, say which is which.**
  The plain-language allowlist went from nine entries to zero: eight were
  rewritten, and the ninth left because the guard's own matcher was fixed
  (`epa` had been matching inside "s*epa*rately" — it was never on the page).
  The writeup called it eight throughout, so the count silently credited a
  matcher fix as a copy rewrite. Booth caught it on PR #44. Both facts were
  known at the time and one was dropped in the summary, which is the specific
  way this goes wrong: **the miscount is not a slip in arithmetic, it is a
  cause that got left out of the sentence.**
- **THE RECURRING ONE: a real number from a command whose scope is not the
  sentence's scope.** Booth found this shape four times, three of them inside a
  single afternoon (2026-09-10), on three different PRs:

  | Where | Written | True |
  |---|---|---|
  | #51 claim 7 | "every measured element reports 0s" | 8 selectors measured; a 3,582-element sweep found 64 still animating |
  | #51 claim 17 | the three `--shadow-sm` / `--shadow-md` / `--shadow-lg` tokens "still used in ten places" | 9 token references; 10 `box-shadow` declarations |
  | #52 claim 5 | "seven pairs sit between 14.9 and 15.25" | nine — read by eye off a wider band printed for another purpose |
  | #54 claim 4 | the churn-guard test file "… its 31 tests still pass" | 3 — the 31 was a three-file run (3 + 20 + 8) |

  **Not one of these was invented.** Every number was real output from a real
  command. That is exactly why re-reading never catches them: the author
  remembers running the command and getting the figure, so it feels earned.
  What goes unchecked is the *attribution* — whether the command's scope is the
  sentence's scope — and attribution is invisible to the person who did it.
  Note also the direction of drift: the command is almost always **wider** than
  the sentence (three files quoted at one, a wide band quoted at a narrow one,
  eight selectors quoted as "every"), because the wider command was run first,
  for a different reason, and the sentence was written later.

  So the rule is not "be careful with numbers", which describes nothing you can
  do. It is: **write the command beside the number.** A one-file
  `pytest … -q --collect-only → 3` cannot be written next to "31" —
  the mismatch becomes self-evident at the moment of writing, which is the only
  moment it is cheap. Corollary, stated because it is the one that keeps
  failing: **never quote a count from a multi-file pytest run.** Collect each
  file on its own.

  `check_scoped_test_counts` in `src/scout_preflight.py` closes the one variant
  that is mechanically decidable — a count attributed to a named test module is
  checked by collecting that module. `tests/test_scoped_count_guard.py` holds
  #54's failing sentence, so the guard cannot rot silently — re-anchored to
  that test file itself in Stage 8c phase 2, because the module #54 actually
  named was deleted and the checker deliberately passes counts for modules that
  do not exist (a body may describe a file a later phase adds). The other three
  variants have no general check and are governed by the rule above.
- **THE OTHER RECURRING ONE, and it is NOT the same defect: a number that was
  correct when written, falsified by the base moving underneath it.** Nobody
  mis-attributed anything and nobody edited the text. The world moved and the
  sentence stayed still. The entry above is an error at the moment of writing;
  this one is an error that arrives later, in a file nobody has touched.

  It happened five times on 2026-09-10/11 alone:

  | Where | Written | What moved |
  |---|---|---|
  | PR #56 body | `731 passed` | the branch rebased; 751 by audit time |
  | PR #60 commits 1-2 | `Suite: 751 passing` | rebased onto a base with ~23 more tests -> 774 |
  | PR #61 README | `18 cases` | PR #59 merged and added one -> 19 |
  | `.game-grid` comment | "stretching would pad the short ones" | true at a 205px spread, false at 20px |
  | `.shared-banner` comment | "Amber, not blue" | `--accent` had become a blue |

  The fix is not "be careful", which describes nothing you can do, and it is
  not documentation — this file already documented the first variant at length
  while PR #56 reproduced it four times the same afternoon. **The fix is that
  a number in prose must have something that recomputes it.** 2026-09-11 ran
  the experiment cleanly, by accident:

  - README's counts are guarded by `tests/test_readme_accuracy.py` -> the
    stale count failed loudly in CI within minutes of #59 merging.
  - This file's suite line is guarded by `src/session_wrapup.py` -> caught.
  - The dE00 figures in the template's model-colour comment are guarded by a
    verifier plus its own mutation cases (PR #60) -> caught.
  - The `Suite:` trailers in commit messages are guarded by **nothing, and
    cannot be** -> they rotted silently and cost an audit to find.

  So, mechanically: **before writing a number, name the thing that will
  recompute it. If nothing can, do not write the number there.** A commit
  message is the clearest case — it cannot be corrected without rewriting its
  SHA, which invalidates every Booth report referencing it, so a count in one
  is unfixable by construction. Put verification numbers in the PR body, which
  `scout-preflight.yml` re-checks on `synchronize` precisely because a rebase
  can falsify them, and leave them out of commit messages.

  Not yet mechanised: nothing rejects a `Suite: N passing` trailer in a commit
  message. That check is the obvious next step and is queued in
  `docs/context.md`.
- **A wrap-up check that greps this file for a literal string is disabled by
  rewording that string, and says the line is MISSING.** `session_wrapup.py`
  matches `Suite:\s*\*\*([0-9,]+)\s+passing\*\*`. Writing
  `Suite: **527 passing, 1 skipped**` — strictly more information — made it
  report "CLAUDE.md has no 'Suite: **N passing**' line to check", which reads
  like a deleted section, not an edited sentence. Any prose this file carries
  *for a tool* is an interface: extra detail goes outside the matched span.
- **The suite count is not a property of the code alone — one test skips while
  HEAD is ahead of `origin`.** A test in `tests/test_session_start.py` skips
  with "HEAD is not on a remote branch, so there is nothing to prove here", so the
  same tree reports `764 passed, 2 skipped` with a local commit sitting
  unpushed and `765 passed, 1 skipped` the moment it is pushed. The wrap-up
  gate then fails `suite count` against a `CLAUDE.md` line that is correct,
  and the obvious repair — editing the number down to match the run — is the
  wrong one: it makes the file false for every session that reads it from a
  clean checkout. **Push first, then run the suite, then quote it.** Both of
  that run's failures had this single cause, and `unpushed work` failing
  alongside `suite count` is the tell.
- **`session_wrapup.py` reports the PASSED count and says nothing about
  failures, so `a real run gives N` can mean a red suite.** Writing the entry
  above produced `764` a second time — not from the skip, but because its own
  first draft put a test path with a trailing colon-and-line-number inside
  backticks, which the path guard in `tests/test_claude_md_freshness.py` reads
  as a filename that does not exist, and a test went red. Same number, wholly
  different cause. **When `suite count` disagrees, run pytest yourself and read
  the whole summary line before touching the figure.** A line number belongs
  outside the backticks; only the bare path goes inside. The sentence you are
  reading was itself rewritten twice for exactly that reason.
- **`scout_preflight.py --base main` compares against LOCAL main, which goes
  stale the moment a PR is merged on GitHub.** Right after merging #41 it
  reported "2 commits on this branch, but the body never mentions 2 of them"
  and named a commit that was already on main — which reads exactly like the
  undisclosed-scope failure it exists to catch. The fix is
  `git fetch origin main:main`, not editing the PR body to explain a commit
  that is not actually in the diff. **Refresh local main before every
  pre-flight.**
- **The full mutation run outlives the 60-second Desktop Commander timeout.**
  89 cases take several minutes. The tool call returns "device did not respond"
  while the run continues, so: redirect to a file, poll for completion, read the
  file — and check `git status` before believing anything, because a killed
  runner skips the `finally` that restores the mutated file.
- **`scout_preflight.py` reads only the PASSED count too, so a RED suite is
  reported as a stale number.** An entry above records this for
  `session_wrapup.py`; on 2026-09-12 it turned up in a second tool, where it is
  worse, because the message preflight prints is the PR #21 stale-figure text —
  "the body claims [876] passing but a real run at HEAD gives 875" — which
  names a cause that is not the cause and sends the reader to edit the PR body
  instead of to the red test. `run_test_suite` matches `(\d+) passed` and never
  looks at the failures. The trigger is worth knowing on its own:
  `test_it_prints_the_context_file_rather_than_pointing_at_it` in
  `tests/test_session_start.py` compares `session_start.py`'s piped stdout
  against `docs/context.md`, and every line it reported missing carried an em
  dash — so the suite is green run directly and red run as a subprocess of
  another Python process, which is exactly how preflight runs it. Two small
  fixes: fail on a non-zero failure count rather than reporting a total, and
  pin the encoding on that subprocess. **The general shape: a tool that reports
  one number out of a multi-number summary will invent a cause for the
  difference, and the invented cause is plausible enough to act on.**
- **I FOUND A DEFECT THAT WAS ALREADY GUARDED, AND NEARLY SHIPPED THE WRONG
  FIX INTO THIS FILE.** Worth more than the finding itself, so it is recorded
  as the correction it is. #60's fourth audit disagrees with itself: the prose
  header says "Confirmed: 13 ... Unverifiable: 2" while its `booth-verdict`
  block lists fourteen CONFIRMED and one UNVERIFIABLE, and the overall prose
  sides with the block. Real, and worth knowing. The first draft of this entry
  then said the counts had "nothing recomputing either" and prescribed "a check
  in the parser: assert the header tallies match the block." **Both halves were
  false.** `cross_check()` in `src/booth_verdict.py` already does exactly that,
  `src/collect_agent_log.py` already prefers the block over the prose and says
  so in its own module docstring, `tests/test_collect_agent_log.py` has
  `test_a_report_disagreeing_with_itself_is_counted`, and the log had already
  recorded this very audit with the two sentences spelled out:
  `"prose says Confirmed: 13, block has 14"` and
  `"prose says Unverifiable: 2, block has 1"`, under a `summary` field named
  `reports_disagreeing_with_themselves`. One `python -c` against
  `data/agent_log.json` would have found all of it, and did — after the entry
  was written.
  **Two lessons.** The narrow one: a self-disagreeing report is detected and
  TALLIED, not failed, so the only open question is whether it should stop an
  audit rather than be counted by one — a much smaller question than "build the
  check." The general one is this file's own rule, turned on its author:
  *an audit finding is a hypothesis, not a defect.* Before writing that
  something is unguarded, grep for the guard. The cost of not doing so is a
  permanent instruction, in the document every session reads cold, to build a
  thing that already exists.
