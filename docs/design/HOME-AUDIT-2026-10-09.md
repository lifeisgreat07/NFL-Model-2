# Home page audit, 2026-10-09 (Stage 66 item 1)

The home page at `/`, built from `main` at `ce640d0` and looked at in
Chromium at 390 and 1280 px, in both themes, as a visitor who has never
heard of the project. Each finding is checked against the page itself.
The rendered options for Mark are the canvas "Sportalytics Home Page
Options".

## What a newcomer sees first

- The first line is the site name in small text, then "What's on" and
  "Two models per game, a market to beat, and every pick graded after the
  final whistle." Nothing says what the site is for. "Models" and "market"
  are the project's words, not a visitor's. Nor does it say that the picks
  are made before the games and can be checked.
- There is no mark or picture: the home page is the only page without the
  sport icon the other pages carry.
- At 1280 px everything fits in the top third of the window, in a narrow
  strip of three cards, and the rest is empty.

## The cards

- NFL: good. It has the week's state, the game count and days, Model B's
  record and the next kickoff. "Model B this season" assumes the visitor
  knows what Model B is.
- NHL: "Picks lock game by game" describes how the pipeline works, not
  what a visitor gets. The record and first puck drop are useful.
- NBA: "No live picks this season" is true for now, but the card links to a
  backtest page without saying what a backtest is. Opening night (October
  20) is not mentioned.
- Each whole card is one link, which gives a large target (good). Every
  card's link text starts with "Open the …", which is fine read on its own.

## Trust and orientation

- The page never says the picks are saved before kickoff in a public
  history, which is the project's strongest claim. The sports' pages say
  it; the home page does not.
- There are no links to Methodology, "Checking the AI's work" or the source.
- The footnote ("Each card is worked out in your browser from the files the
  last build read …") is a developer's note.
- The home page has no theme button. Since #353 it follows the choice made
  on any sport's page, but a visitor who lands on the home page first
  cannot set it there.

## What already works

- The skip link, one `h1`, landmarks, sport pills with `aria-current`, the
  contrast, and the cards stacking on a phone with no sideways scroll. The
  browser checks pass the page, with axe-core, at all six widths.

## The options (rendered)

- **A, scoreboard first:** a one-sentence promise (picked before the game,
  graded in public), a record strip, the three cards with the sport icons,
  "How it works" in three steps, and footer links.
- **B, up next first:** the next six games across sports, each with its
  pick or when it locks, then the cards.
- **C, explained for newcomers:** A's promise and cards, then the three
  steps and a short "New here?" (what is a model, what is the market, can I
  check the picks).

Claude's recommendation: **A**, with C's "New here?" folded in below the
steps. It answers "what is this, and why trust it" in the first screen. It
keeps the cards that already work, and it costs one new data point (the
record strip), which the build already has. B is the best page for a
returning visitor, but a poor first impression in the off-hours, when
nothing is up next.
