# Where everything stands

**Read this first, every session. It is the only file that is rewritten every
time.** One screen, present tense, no history — history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins: CLAUDE.md holds what stays true
for months, this holds what is true today.

Last updated: 2026-09-09

---

## Right now

**Suite:** 635 passing, 1 skipped on `main`. Re-run before quoting it.

**Stage:** 7.5 (content & structure pass) is in progress. Stages 1 and 2 are
complete; Stage 3 is winding down. Pages are down from 14 to **9**, which was
7.5's target.

**The single next action:** get PR #45's audit to a clean verdict and merge it.
Everything else is branched behind it or waits on it.

## Open work, and what each thing is waiting on

Branch names are written in full on purpose: `src/session_start.py`
cross-checks them against git and cannot see work referred to only by PR number.

| What | State | Waiting on |
|---|---|---|
| PR #45, branch claude/session-memory-docs | Open, audited three times | A clean audit. This is the file you are reading, plus `docs/index.md`, `memory/` and their guards. |
| Branch claude/readme-recruiters | Pushed, no PR | Mark to open its PR. Stage 7.6: the recruiter-facing README and its accuracy guard (the guard's file is on that branch, so it is not named as a path here). Off `main`, no conflict with #45. |
| Branch claude/reliability-rebuild | Pushed, no PR | Merge #45, then merge main into it. It conflicts with #45 on CLAUDE.md's "Start here" — take #45's version, the short pointer. |

PR #44 is merged.

## What is queued after that

1. **Season Accuracy — declutter.** Clean on vocabulary, still too dense.
2. Remaining 7.5 content work: My Picks "track record at this confidence",
   Boards "why this team is favoured" in football terms.
3. **Stage 7.6's other half.** The repo's About panel is still empty. The
   description and topics are set in the GitHub web UI, not in any file here,
   so they are Mark's to do; see CLAUDE.md.

## Known and deliberately not fixed

- Season Accuracy's Weekly Trend still lists **2025 Wk 10** beside 2026 Week 1.
  This is graded *data*, not copy, so removing it means editing data files.
  Needs a deliberate decision, not a drive-by fix.
- The agent-log data file does not exist on `main` yet — the workflow that
  writes it is on the reliability-rebuild branch. (Not named as a path here on
  purpose: `docs/index.md` and this file are both held to "every path you name
  must exist", and naming one that does not is how documents start lying.)
- This file is stamped on UTC, the clock the agent writing it runs on.
  `src/session_wrapup.py` runs on Mark's machine, hours behind, and accepts a
  stamp one day ahead for exactly this reason. It does not accept one day
  behind — that is a file nobody rewrote.
