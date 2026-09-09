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

**The single next action:** merge PR #44. Booth returned SAFE TO MERGE on
2026-09-09 — 13 claims, 13 confirmed, 0 discrepancies.

## Open work, and what each thing is waiting on

Branch names are written in full on purpose: `src/session_start.py`
cross-checks them against git and cannot see work referred to only by PR number.

| What | State | Waiting on |
|---|---|---|
| PR #44, branch claude/plain-english-rewrites | **SAFE TO MERGE** | Nothing. Merge it first — the other two sit behind it. |
| PR #45, branch claude/session-memory-docs | Open | Its own audit. This is the file you are reading, plus `docs/index.md`, `memory/` and their guards. |
| Branch claude/reliability-rebuild | Pushed, no PR | Merge #44, then merge main into it before opening its PR. It is branched off #44. |

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
