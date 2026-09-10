# Where everything stands

**Read this first, every session. It is the only file that is rewritten every
time.** One screen, present tense, no history — history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins: CLAUDE.md holds what stays true
for months, this holds what is true today.

Last updated: 2026-09-10

---

## Right now

**Suite:** 704 passing, 1 skipped on `main`. Re-run before quoting it. Nothing
in Stage 8's design phase touched `src/` or `tests/`, so that count still holds.

**Stage:** 7.5 is **complete** — every content and structure item has shipped.
7.6's repository half is done. Stages 1 and 2 are complete; Stage 3 is closed
apart from one post-merge check below. Pages are down from 14 to **9**.
**Stage 8's design phase is complete** as of 2026-09-10; its implementation
half (8b) has not started.

**The single next action:** port the design into `src/dashboard_template.html`.
Read `docs/design/STAGE8-DESIGN.md` first — it is the decision record, and
several of its rules exist because breaking them shipped a visible defect.
The specification is the pair of mocks beside it; their first 19,577
characters are byte-identical and that block is what gets lifted.

## Open work, and what each thing is waiting on

Branch names are written in full on purpose: `src/session_start.py`
cross-checks them against git and cannot see work referred to only by PR number.

**No branches are open.** PRs #44 through #50 are all merged and their branches
deleted. `main` is the only branch, local and remote.

| What | State | Waiting on |
|---|---|---|
| `docs/design/weekboard.html` + `seasonaccuracy.html` | Delivered in chat 2026-09-10, not yet saved into the repo | Mark to download both from the conversation into `docs/design/`. Without them the decision record has no specification to point at. |
| The repo's About panel | Empty | Mark, in the GitHub web UI. Wording is in CLAUDE.md, ready to paste. |
| `Auto-regenerate dashboard` run #56 | Failed 2026-09-09 | Someone to read its log. See "Known" below. |

## What is queued after that

1. **Stage 8b — port the design into `src/dashboard_template.html`.** Lift the
   shared block, then restyle page by page: Week Board first (it exercises the
   most components), then Season Accuracy, then the other seven. The template
   is 3,250 lines / 224KB across nine pages against the mocks' two, and ~704
   tests assert on it, several on colour tokens and exact strings. Expect test
   churn, and treat a failing colour assertion as a question rather than
   something to update to match — those tests encode decisions that were
   argued for.
2. **The first real graded week.** `.github/workflows/weekly-update.yml` fires Tuesday 2026-09-15
   at 11:00 UTC (07:00 local) and grades 2026 Week 1. Season Accuracy fills in
   by itself. Worth watching once, because it has never run against a week that
   actually had games.
3. **A two-line README follow-up:** its repo-layout block still omits `docs/`
   and `memory/`, which did not exist on `main` when it was written.

## Known and deliberately not fixed

- **`Auto-regenerate dashboard` run #56 failed** and nobody has read why. Its
  log needs a GitHub sign-in this session did not have, and the only visible
  annotation is a Node 20 deprecation warning, which is not an error. The
  hypothesis — unverified — is two rebuilds racing to push, which a
  `concurrency` group would fix, as `.github/workflows/booth-pr-audit.yml`
  already does. Do not treat that hypothesis as a diagnosis.
- **`index.html` is generated AND committed**, so `main` rebuilds it whenever
  the collector runs and every branch touching the template conflicts with it.
  It bit twice in one day. Resolve by taking the branch's copy and rebuilding
  from the merged sources — never by editing conflict markers in a generated
  file. Worth restructuring during Stage 8, when the template is open anyway.
