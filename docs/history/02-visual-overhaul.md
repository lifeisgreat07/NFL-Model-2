# The visual overhaul

Part of the stage history; the index is `docs/stage-history.md`. Moved verbatim from
that file on 2026-10-06 (Stage 49 item 24).

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
`src/sports/nfl/dashboard_template.html` and restyling page by page. The template was
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
`src/sports/nfl/dashboard_template.html`; it was a mock-only element. The real consumers
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
