# Session memory

One file per working session, named `YYYY-MM-DD.md` (add `-2` for a second
session the same day). **Append-only.** A past session's file is never edited to
match what later turned out to be true — that is the whole value of it. If a
decision was reversed, the reversal is recorded in the newer file.

## What goes in one

Four headings, in this order. Keep it to what a future session would have to
reconstruct expensively:

- **Shipped** — PR numbers and one line each.
- **Decided** — the decision AND the reasoning. Without the reasoning it gets
  re-litigated in a month.
- **Surprised us** — anything that behaved differently from what was assumed.
  The durable shape belongs in CLAUDE.md's traps; the story belongs here.
- **Left open** — what the next session inherits.

## What does NOT go in one

A narrative of the session. Nobody reads it. If it does not change a future
decision, leave it out.

## Sessions

| Date | Headline |
|---|---|
| [2026-09-08](2026-09-08.md) | Stage 7.5 cut the dashboard from 14 pages to 9; the jargon guard went live; the agent log turned out never to have run |
