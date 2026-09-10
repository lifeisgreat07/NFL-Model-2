# Stage 8 — the visual direction, as decided

Closed 2026-09-10. The token values below were verified by computation, not by
eye — before changing any of them, read "Numbers that were checked" and re-run
the arithmetic. This file is the decision record **and** carries the token
block, because that is the one part of the work that cannot be re-derived: the
values were chosen against computed contrast and colour-blindness floors, not
by eye. The mocks that exercised it were delivered into the 2026-09-10
conversation and deliberately not committed -- they are scaffolding around fake
data, and a stale copy in the repo would become a second source of truth. Their
shared block was 19,577 characters and byte-identical across both pages,
verified by diff.

Produced over four rounds with Claude Fable (v3.0 -> v3.4). Every numeric claim
in every round was re-derived independently before being accepted: contrast by
recomputing WCAG relative luminance from the hex values with sRGB alpha
compositing for tints, colour-blind separation by running the Machado 2009
matrices at severity 1.0 and computing CIEDE2000, geometry by rendering in
headless Chromium and reading `getBoundingClientRect`. Three claims were found
false that way and sent back. That habit should continue into the port.

## The rule the whole thing rests on

**Colour has exactly four jobs.** Nothing else gets a hue.

1. **Structure** -- the nine-step neutral ramp, reached only through semantic
   aliases (`--surface`, `--text-2`, `--border-strong`, ...). Never `--n6`
   directly in a component.
2. **The model's lean, and the active thing** -- one accent, one blue.
3. **A graded outcome** -- `--graded-correct` / `--graded-wrong`, and **only
   after a game has been scored.** This is load-bearing: a colour that means
   "correct" must never appear on a game that has not happened, or the page is
   lying. It is why the pick emphasis below uses weight and words, not green.
4. **Chart series identity** -- `--series-a/-b/-m/-p`, keyed to the entity so
   hiding one never repaints the others, and fenced to charts, legends,
   end-labels and the swatch on a tile that names the same entity.

**Team identity is a logo, never a colour.** An image does not compete with the
accent for signal. The `.logo` wrapper owns the 20x20 box, not the `<img>`, so
a failed load never shifts the layout; failure adds `is-fallback`, which draws
a disc. One capture-phase `error` listener on `document` handles every logo on
the page, because image errors do not bubble.

**Elevation is a border, not a shadow.** `--shadow-overlay` has exactly one
consumer, the `.overlay` component.

## The token block, verbatim

```css
:root {
  color-scheme: dark;
  --n0: #0B0D10;  /* canvas */                --n1: #121519;  /* surface */
  --n2: #181C22;  /* raised */                --n3: #232830;  /* hairline */
  --n4: #2F3641;  /* strong border */         --n5: #4A5260;  /* disabled text */
  --n6: #7D8794;  /* muted text */            --n7: #AEB6C0;  /* secondary text */
  --n8: #E6E9ED;  /* primary text */
  --bg: var(--n0); --surface: var(--n1); --surface-2: var(--n2);
  --border: var(--n3); --border-strong: var(--n4);
  --text: var(--n8); --text-2: var(--n7); --text-3: var(--n6); --text-disabled: var(--n5);
  --accent: #7FA8F5; --accent-strong: #5C8CE8;
  --accent-soft: rgba(127,168,245,.14); --accent-ring: rgba(127,168,245,.45);
  --graded-correct: #4FAE8A; --graded-correct-soft: rgba(79,174,138,.14);
  --graded-wrong:   #D46C6C; --graded-wrong-soft:   rgba(212,108,108,.14);
  --series-a: #A78BF7; --series-b: #7EDDE8; --series-m: #D9AE45; --series-p: #D0699C;
  --shadow-overlay: 0 12px 32px rgba(0,0,0,.5);
  --z-nav: 10; --z-overlay: 20;
  --s1: 4px; --s2: 8px; --s3: 12px; --s4: 16px; --s5: 20px;
  --s6: 24px; --s7: 32px; --s8: 40px; --s9: 48px;
  --r-sm: 4px; --r-md: 8px; --r-lg: 12px; --r-full: 999px;
  --logo: 20px;
  --font: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto,
          "Helvetica Neue", Arial, sans-serif;
  --fs-11: 11px; --fs-12: 12px; --fs-13: 13px; --fs-14: 14px;
  --fs-16: 16px; --fs-20: 20px; --fs-24: 24px; --fs-32: 32px;
  --lh-tight: 1.15; --lh-body: 1.45; --track-label: .06em;
  --dur-fast: 80ms; --dur-base: 160ms; --dur-slow: 240ms;
  --ease: cubic-bezier(.2, .7, .2, 1);
  --press: translateY(1px);
}
[data-theme="light"] {
  color-scheme: light;
  --n0: #F3F4F6; --n1: #FFFFFF; --n2: #F7F8FA; --n3: #E4E7EB; --n4: #CBD1D9;
  --n5: #A3ABB6; --n6: #626C7B; --n7: #4A5260; --n8: #14181E;
  --accent: #1F5ED6; --accent-strong: #174BB0;
  --accent-soft: rgba(31,94,214,.10); --accent-ring: rgba(31,94,214,.35);
  --graded-correct: #187052; --graded-correct-soft: rgba(24,112,82,.12);
  --graded-wrong:   #B94343; --graded-wrong-soft:   rgba(185,67,67,.10);
  --series-a: #6D3BC7; --series-b: #0E7C84; --series-m: #8C6410; --series-p: #731847;
  --shadow-overlay: 0 12px 32px rgba(20,24,30,.14);
}
@media (prefers-reduced-motion: reduce) {
  :root { --dur-fast: 0ms; --dur-base: 0ms; --dur-slow: 0ms; }
}
```

Series shapes and dashes, which carry identity when the colour cannot:
Model A circle / solid, Model B square / `6 3`, Market triangle / `2 3`,
My Picks diamond / `8 3 2 3`. Dark series values are stepped in lightness
(L* 64 / 83 / 73 / 58) rather than being a brightness flip of the light ones.

## Numbers that were checked, and must stay true

- Every text pairing in both themes clears 4.5:1. The full 58-row table lives
  in the amendment-1/2 documents; all 58 were recomputed and 57 matched to the
  stated decimal.
- Two values were darkened to reach that floor and must not drift back:
  light `--n6` `#6B7482` -> `#626C7B` (4.45:1 -> 5.00:1 on `--surface-2`), and
  light `--graded-correct` `#1E7F5F` -> `#187052` (4.22:1 -> 5.08:1 on its own
  tint over white).
- **Prohibited pairing:** dark `--text-3` on `--accent-soft` computes to
  3.97:1. It does not occur today. Do not introduce it.
- Series separation, CIEDE2000 under Machado 2009 at full severity: the light
  deuteranopia minimum is Model A -- Model B at 15.8, above the >= 15 floor.
  Light `--series-p` is `#731847` for that reason (it was `#831F52`, which put
  Model B -- My Picks at 14.7, under the floor). Moving any series colour means
  re-running that computation, not eyeballing it.
- Every series also carries a **shape and a dash**, so identity survives
  greyscale, colour-blindness and forced-colours without the colour at all.

## Motion

Four values, and the whole dashboard's feel is these four:

| Token | Value | Job |
|---|---|---|
| `--dur-fast` | 80ms | a colour changing under the pointer |
| `--dur-base` | 160ms | a control changing state |
| `--dur-slow` | 240ms | a region appearing |
| `--ease` | `cubic-bezier(.2,.7,.2,1)` | one curve. Never a bounce. |

`--press: translateY(1px)` is the single press gesture, on everything
clickable. `prefers-reduced-motion: reduce` sets the three durations to `0ms`
in one block, so the reduced-motion path cannot drift out of sync.

**Rules that were expensive to learn:**

- `transition: all` appears zero times. Name the properties.
- **Every** `:hover` rule lives inside `@media (hover: hover)`. The phone
  layout has a bottom tab bar, i.e. real touch users, and an unguarded hover
  sticks after a tap.
- No entrance animation may fire on a re-render. Both pages render by assigning
  `innerHTML`, and Season Accuracy re-renders on a debounced resize; an
  entrance wired naively re-fires every time the window moves. Entrances are
  armed by an explicit `{enter: true}` from first paint and deliberate user
  actions only, and every other render path removes the class.
- **Specificity beats source order, and it bit twice.** The three brand-mark
  states are deliberately all (0,4,0) so source order decides
  hover < entering < loading. Dropping `.brand` from one of them makes
  `.brand:hover` (four classes) outrank `.is-loading` (three), which freezes
  the spinner while the pointer is over the logo. The comment in the CSS says
  so; leave it there.

## Decisions a future session should not re-litigate

**Cut from the Week Board, deliberately** (Mark, 2026-09-10): the four stat
tiles above the filter row, the `A - MARKET` field on each card, and the
kickoff / confidence / gap sort control. Three of the tiles duplicated the
filter chips; the fourth aggregated a field that was itself removed. The page
opens on the games. `.tiles` and `.seg` stayed in the shared CSS because
Season Accuracy still uses them -- deleting a usage is not deleting a
component.

**Kept, explicitly, and not candidates for consolidation:** the week stepper,
and the day / kickoff time / broadcast channel on every card.

**`MARKET ODDS`, not `MARKET IMPLIED`,** and stated for the **Model A
favourite** -- the bold row -- so the three probabilities a reader compares
(Model A, Model B, Market) always name one team. Stating it for the away team
or the underdog forces mental subtraction on exactly the cards that matter.

**The breakdown's derived rows carry their own subject** (`34.5% MIA`). They
are home-win probabilities sitting beside a column naming whoever leads, and
without the subject printed the row reads as the other team's number. This is
the same class of defect as the market sentence that once shipped inverted.

**When Model A and Model B disagree,** each probability pill takes its own
model's weight, so the bold Model B pill can sit on the row Model A greyed
out, and the column header reads `TEAM . A != B`. The row weighting still
follows Model A, for stability across sort and filter.

**Home team is a word, not an `@`.** The old `@` was appended to the *away*
row to mean "this team is away", but the convention puts `@` before the home
team with an object (`@ MIA`); a trailing `@` marks the team it does not
describe. Now the home row carries a `Home` tag. At the 340px card floor a
bordered chip does not fit, so the tag is borderless -- and on a **final**
game the pre-game record is dropped, because the score supersedes it and the
two cannot both fit. Measured: `.who` content 146px in a 146px box at 340px,
164/164 at 358px, no overflow in any theme.

**The model's pick is emphasised two ways, and neither is a colour.** A 2px
accent rail down the favourite's row -- which is not a new symbol, because the
sidebar's active-page indicator is already that bar -- plus the pick stated in
words in the facts row (`MODEL A PICKS  BUF 65%`). A `PICK` badge was built and
rejected: it is a sixth signal for a fact already encoded five ways, it reads
as a tout sheet, and on an `A != B` card it stamps "PICK" on a row Model B
disagrees with.

**The brand mark is a football,** outline only so it reads at 20px. Still by
default; settles once on first paint; nudges under the pointer; and tumbles
**only while data is loading**, so the motion is a status indicator rather than
decoration. `brandMark.start()` / `.stop()` are the whole surface. `.stop()`
waits for the current revolution to end so the ball rests at 0deg instead of
snapping, with a 900ms fallback so it can never stick on. Under reduced motion
nothing spins, so the mark drops to `--text-3` while busy and `aria-busy`
carries it for assistive tech. A perpetually spinning logo was built and
rejected.

## Two traps found by rendering, already fixed here, worth not reintroducing

- **An animated disclosure can leak into the accessibility tree.** Replacing
  `display: none` with `grid-template-rows: 0fr` animates nicely but leaves the
  collapsed content readable by screen readers and findable by find-in-page,
  contradicting the button's `aria-expanded="false"`. The fix is `visibility:
  hidden` on the inner wrapper with `transition: visibility 0s linear
  var(--dur-slow)`, so it stays visible until the collapse finishes.
- **Wholesale `innerHTML` re-render destroys interaction state.** An open
  breakdown vanished on a filter change. Interaction state lives in `state`
  (`state.open` keyed by game index) and is re-derived on render. Keep that
  rule: anything the user has toggled must survive the next render, and
  floating UI must live outside the rendered tree -- which is why `.overlay` is
  a single element on `<body>`.

## Architecture, decided

**Keep wholesale re-render.** Under a hundred cards and four charts, it costs
milliseconds and buys total predictability: every view is a pure function of
`state`, with no reconciliation code to get wrong. The two rules that make it
safe are above. Revisit only if a view needs sub-100ms live updates.

**Navigation stubs are already wired:** `openTeam(abbr)` from every team row
(an `<a>`, keyboard-reachable, inheriting the base focus ring) and
`openWeek(n)` from every Season Accuracy week row. Both are one function body
away from real routing.

## What the port has to face

`src/dashboard_template.html` is 3,250 lines / 224KB and covers nine pages;
the mocks cover two. Roughly 704 tests assert against the template, several of
them on colour tokens and on exact strings (`tests/test_dashboard_charts.py`,
`tests/test_plain_language.py`, `tests/test_share_link.py`,
`tests/test_whats_changed_page.py`). Expect test churn, and treat a failing
colour assertion as a question -- the tests encode earlier decisions that were
themselves argued for -- rather than as something to update to match.
