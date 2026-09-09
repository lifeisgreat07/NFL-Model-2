# Where everything stands

**Read this first, every session. It is the only file that is rewritten every
time.** One screen, present tense, no history — history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins: CLAUDE.md holds what stays true
for months, this holds what is true today.

Last updated: 2026-09-08

---

## Right now

**Suite:** 628 passing, 1 skipped on `main`. Re-run before quoting it.

**Stage:** 7.5 (content & structure pass) is in progress. Stages 1 and 2 are
complete; Stage 3 is winding down. Pages are down from 14 to **9**, which was
7.5's target.

**The single next action:** check whether PR #44's newest audit passed, then
merge it.

## Open work, and what each thing is waiting on

| What | State | Waiting on |
|---|---|---|
| PR #44 — plain-English rewrites | Open, audited 3× | A clean audit at head `6333700`. Its only finding was a count in the description, which has been corrected; the runs that flagged it read the old text. |
| Branch `claude/session-memory-docs` | This branch | Its own PR — the file you are reading. |
| Branch `claude/reliability-rebuild` | Pushed, no PR | Merge #44 first, then merge main into it. It is branched off #44. |

## What is queued after that

1. **Season Accuracy — declutter.** Clean on vocabulary, still too dense.
2. **Stage 7.6 — the repository front door.** GitHub's About panel is empty and
   the README opens on regression maths. Two of its three items are Mark's to do
   in the GitHub UI; see CLAUDE.md.
3. Remaining 7.5 content work: My Picks "track record at this confidence",
   Boards "why this team is favoured" in football terms, README.

## Known and deliberately not fixed

- Season Accuracy's Weekly Trend still lists **2025 Wk 10** beside 2026 Week 1.
  This is graded *data*, not copy, so removing it means editing data files.
  Needs a deliberate decision, not a drive-by fix.
- The agent-log data file does not exist on `main` yet — the workflow that
  writes it is on the reliability-rebuild branch. (Not named as a path here on
  purpose: `docs/index.md` and this file are both held to "every path you name
  must exist", and naming one that does not is how documents start lying.)
