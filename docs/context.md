# Where everything stands

**Read this first, every session. It is the only file that is rewritten every
time.** One screen, present tense, no history — history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins: CLAUDE.md holds what stays true
for months, this holds what is true today.

Last updated: 2026-09-09

---

## Right now

**Suite:** 672 passing, 1 skipped on `main`. Re-run before quoting it.

**Stage:** 7.5 (content & structure pass) is in progress. 7.6's repository half
shipped. Stages 1 and 2 are complete; Stage 3 is winding down. Pages are down
from 14 to **9**, which was 7.5's target.

**The single next action:** open `claude/reliability-rebuild`'s PR. Main has
already been merged into it and its CLAUDE.md conflict is resolved, so it is
ready — opening the PR is what starts its audit, which is why it was held back.

## Open work, and what each thing is waiting on

Branch names are written in full on purpose: `src/session_start.py`
cross-checks them against git and cannot see work referred to only by PR number.

| What | State | Waiting on |
|---|---|---|
| Branch claude/reliability-rebuild | Pushed, main merged in, no PR | Mark to open its PR. Connects `src/collect_agent_log.py`, which had never run, and rebuilds the reliability page around its output. |

PRs #44, #45 and #46 are all merged and their branches deleted. This is the
only branch left.

## What is queued after that

1. **Season Accuracy — declutter.** Clean on vocabulary, still too dense. This
   is the last substantive Stage 7.5 item.
2. Remaining 7.5 content work: My Picks "track record at this confidence",
   Boards "why this team is favoured" in football terms.
3. **The README's repo-layout block does not list `docs/` or `memory/`.** They
   did not exist on `main` when #46 was written and its own guard would have
   failed. They exist now; adding them is a two-line follow-up.
4. **Stage 7.6's browser half.** The repo's About panel is still empty. The
   description and topics are set in the GitHub web UI, not in any file here,
   so they are Mark's to do.

## Known and deliberately not fixed

- Season Accuracy's Weekly Trend still lists **2025 Wk 10** beside 2026 Week 1.
  This is graded *data*, not copy, so removing it means editing data files.
  Needs a deliberate decision, not a drive-by fix.
- This file is stamped on UTC, the clock the agent writing it runs on.
  `src/session_wrapup.py` runs on Mark's machine, hours behind, and accepts a
  stamp one day ahead for exactly this reason. It does not accept one day
  behind — that is a file nobody rewrote.
