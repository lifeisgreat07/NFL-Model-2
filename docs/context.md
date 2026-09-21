# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history — history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-09-21 (#79 and #80 merged; the colour gradings are decided)

---

## Right now

**Suite:** 1305 passing, 1 skipped — `python -m pytest -q` on `main` at
`e1152f8`, HEAD level with origin, which is the order that makes the figure
reproducible. Corpus: 208 cases, all CAUGHT, from
`python tests/mutation/runner.py` with no `--id`, whose scope is every case.

**No open PRs and no branches but `main`.** #80 merged: both disputed colour
pairs graded ACCEPTED, each pinned by the fact it rests on. Booth: 13
CONFIRMED, 0 discrepancies, 1 UNVERIFIABLE, SAFE TO MERGE — and its header
agreed with its own verdict block for the first time in eleven reports.

**Stage 9's colour work is unblocked.** The decision that was holding it is
made; what remains is `matchupColors`, the Net Rating diverging pair, and the
confidence / flagged / "model was wrong" language.

**Next action: decide whether the Week Board's team-colour split bar survives
at all.** It is a deletion question before it is a colour one. Stage 8 says
team identity is a logo and never a colour; `matchupColors` is the only
consumer of `teamColor()`, whose fallback is now the last live site of the
`#8A93A8` literal. If the bars go, queue items 1 and 2 go with them and 60 of
496 close team pairs stop being anyone's problem. Mark wanted this decided by
looking, and the side-by-side treatment built for the token pairs on
2026-09-21 applies directly.

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| Booth can pass silently | Found 2026-09-21, unfixed | A step asserting a comment exists for the head SHA. Booth cannot audit its own workflow file, so it ships on a test and an argument, as #30 did |
| The repo's About panel | Empty | Mark. Repo settings; wording in CLAUDE.md |
| Confirming #73 on a phone | Not done | Only a device proves the zoom is gone |
| Week 2 grading | Tue 2026-09-22 | Watch that the page rebuilds itself |
| ATL's week 2 starter | Unresolved | Not ours — predictions are write-once |

## Queued, in order

1. **`matchupColors`, and `teamColor()`'s fallback with it.**
   `python src/verify_matchup_cvd.py` (CIEDE2000): 60 of 496 team pairs under
   15, 9 under 5, worst ARI/PHI 0.18. See the next action above — retiring the
   bars may delete the problem rather than tune it.
2. **`log_line_snapshot` writes nulls instead of skipping.**
   `src/weekly_update.py` appends a row when the spread is NaN — #75's
   all-null file, recurring on any run made days ahead of a week. The first
   item here with a real trigger and no decision in front of it, and Week 2
   grades tomorrow.
3. **`.game-card` overflows the viewport below 352px**, 340px card against a
   296px content box at 320. Stage 10's mobile pass.
4. **Six preflight and README guard gaps**, one confirmed by Booth on #78 and
   two found on 2026-09-21 in `check_visual_claims_have_artifacts`. All are
   written up in CLAUDE.md's traps.
5. **Stage 10**, then **Stage 6's broadcast channel**; Stage 7's text-only
   items are unblocked, visual ones wait for 10.

## Known and deliberately not fixed

- **A Booth header can disagree with its verdict block**, logged by `cross_check()`, ten of the last eleven reports. Should it fail? It has cost nothing yet only because the discrepancy count was zero either way.
- **`check_scoped_test_counts` skips a count for a module that does not exist** — a DELETED module passes silently.
- **Only the wrap-up gate and session-start recompute CLAUDE.md's `Suite:` line.** Both manual, accepted.
- **The README says "cases" where its guard counts FILES.** Bumping the number is forced by any new case file; fixing the wording moves the guard's own regex.
- **Nothing on the page reaches the listbox edge flip**; kept and checked over synthetic geometries.
- **A human approval leaves no artifact in the repo.** Booth marked the #80 acceptance UNVERIFIABLE for that reason and was right to; `memory/2026-09-21.md` is what it points at.
- **The co-occurrence trace, and the no-JS findings, are re-derivable only where a browser exists.** No CI job here has one. In both the premise is guarded in the suite and the finding itself is not; accepted.
