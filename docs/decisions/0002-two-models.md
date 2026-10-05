# 0002. Two models, side by side

## Decision

The dashboard shows two models for every game:

- **Model A**, football only: offence, defence, quarterback and a
  change-of-quarterback term, each a difference between the two teams, in a
  logistic regression refit every week.
- **Model B**, Model A plus the current betting spread.

Both are fitted from one definition, `MODEL_SPECS`, which the live pipeline
and the backtest share (Stage 33 item 21).

## Why

- Model A answers the football question: how much can public play-by-play
  say on its own?
- Model B answers the practical one: given what the market already knows,
  does the football add anything?
- Showing both, with the market's own probability beside them, lets the
  page say plainly what the backtest found, instead of picking the flattering
  comparison.

## What the backtest found, and the page says

- Model B beats Model A on proper scoring rules (log loss, Brier): a
  CONFIRMED FINDING.
- The market beats Model A: a CONFIRMED FINDING.
- Model B against the market is INCONCLUSIVE on all four metrics, stated
  with intervals.
- There is no edge against the spread: 51.61%, 95% interval [48.58%,
  54.63%], which contains 50% and does not reach the 52.38% break-even.

## What it costs

Two of everything on the page, and a reader can mistake Model B's better
scores for the model having found something the market missed. The page
says it has not.

## What would reopen it

A pre-registered experiment that changes one of the findings above, judged
on proper scoring rules with the paired bootstrap CLAUDE.md requires.

Sources: README, "Current model"; CLAUDE.md, "Findings that still
constrain the work".
