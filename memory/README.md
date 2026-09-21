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
| [2026-09-09](2026-09-09.md) | #44 merged; the wrap-up gate and its pytest guard were found disagreeing about dates; METHODOLOGY.md turned out never to have existed |
| [2026-09-10](2026-09-10.md) | Stage 8's design phase closed; re-deriving every colour and geometry claim caught three false ones, two of them mine |
| [2026-09-11](2026-09-11.md) | #58, #59 and #61 merged; a test was found silently skipping in CI since #58; the session's lesson is that a number in prose needs something that recomputes it |
| [2026-09-12](2026-09-12.md) | #64, #65, #66 and #67 merged and the remote cut to one branch; a PR body was caught carrying a figure no command had produced; scoping a number to its commit proved to be what keeps it true |
| [2026-09-13](2026-09-13.md) | #68 and #70 merged; CLAUDE.md was audited against the repo and corrected in 34 places; four audits on #69 found four defects and none of them were in the code |
| [2026-09-15](2026-09-15.md) | #71, #72 and #73 all merged; a phone's zoomed-out board turned out to be `min-width` beating `width` on `.visually-hidden`; four PR bodies carried a bad figure, every one caught by Booth and none by any mechanical check, two of them after the trap entry for the previous one was already written. Second session: the first real week graded cleanly but the page never rebuilt — the guard written for that exact failure named one workflow and was blind to the second; fixed and merged as #74, which Booth confirmed from an eight-hour gap in the Actions run log |
| [2026-09-16](2026-09-16.md) | #76 merged and #77 opened; #75 closed as 16 rows of nulls; a missing webfont turned a real defect off entirely, and `document.fonts.check()` turned out to answer a different question than the one it was being asked; two mutations survived a new guard because today's palette reaches only one side of its rule |
| [2026-09-20](2026-09-20.md) | #78 opened: all six "Not traced" `ACCEPTED_CLOSE` entries traced by rendering the page. Four pairs co-occur and every instance carries a word or a shape; two cannot meet at all — and so, it turned out, can neither of the two entries already graded KNOWN DEFECT, which turns that queue item into a judgement for Mark. The session's lesson is that a sweep over live data answers only for today's data: the first run reported a token as appearing nowhere, because the chart carrying it needs two graded weeks and it is September |
