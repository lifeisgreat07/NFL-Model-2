# Where everything stands

**Read this first, every session. It is the only file rewritten every time.**
One screen, present tense, no history; history lives in `memory/`.
If this contradicts CLAUDE.md, this file wins.

Last updated: 2026-10-09, 04:55 UTC (Stage 52 merged; the 45 to 49 stack, Stage 39's cancelled state and the Monday fallback merged; Stages 62 to 67 planned; no PR open)

---

## Right now

**Suite:** run it before quoting it; CLAUDE.md's `Suite:` line is the checked
figure. The NFL now lives in `src/sports/nfl/` (research in
`src/sports/nfl/research/`), its files in `data/nfl/`, `predictions/nfl/`,
`results/nfl/`, `experiments/nfl/`; shared modules in `src/core/` (#351).
Run modules with `python -m src.<package>.<module>`. The dashboard template
is parts under `src/dashboard/`, joined by `src/core/template_parts.py`.

**Live:** the home page at `/`, the NFL at `/nfl/`, the NHL at `/nhl/`, the
NBA's backtest at `/nba/`. The NFL's workflows are `nfl-*.yml` now; Mark
re-pointed the six cron-job.org jobs on 10-08 (late). Unconfirmed: whether he
also updated the QB routine's prompt (`src.sports.nfl`, `data/nfl/qb_overrides/`,
eight hours' slack). Its next PR (Mon 22:00 UTC) shows which path it used.

**First checks next session:** Friday 05:17 UTC weekend refresh ran from
cron-job.org on `.github/workflows/nfl-weekend-refresh.yml` (not only GitHub's late copy);
the nightly canary, mutation slice and dependency audit ran green on the
moved tree. Tuesday 10-13 11:00 UTC is the slot guard's first real test.

**Mark delegated decisions to Claude on 2026-10-05 and 2026-10-08.** Each
decision is logged with its reason in `memory/` and the Audit Response Log.

## Open work, and what each is waiting on

| What | State | Waiting on |
|---|---|---|
| Stage 21 (`s21-insights`) | Built on the pre-move layout | Week 5 graded (Tue 10-13); rebase across #351's moves first |
| Stage 62 (theme, icons, NHL logo size) | Planned 10-09 | Nothing; icons need rendered options |
| Stage 63 (NHL board shows results and locked picks) | Planned 10-09 | Nothing |
| Stage 64 (NHL day strip + compact rows) | Layout chosen 10-09 | Nothing |
| Stage 65 (NBA live on GitHub's runners) | Planned 10-09 | Source probe from a runner; season start date |
| Stage 66 (home page audit and rework) | Planned 10-09 | Audit, then rendered options for Mark |
| Stage 67 (display name "Sportalytics") | Planned 10-09 | Best with or after Stage 66 |
| Stage 38 neutral-site rule | Decided 10-09: no home edge at neutral sites | A registered rule change and its back-check |
| Stage 46 items 6, 9; 47 items 13, 14 | Approved 10-09 (46.8 dropped) | 46.6 needs Stage 42 item 1 |
| Stage 39 remaining items; 42 item 1; 43; 44 | Open | Nothing (39.4 is Mark's call) |

## Queued, in order

1. Stage 62 item 1 (shared theme), 63, 64, 62's other items.
2. Stage 65's source probe from a runner, then the rest of 65.
3. Stage 42 item 1, then 46 items 9 and 6.
4. Stage 66's audit and rendered options; Stage 67 with it.
5. Stage 21 once week 5 is graded; Stage 39; Stage 38's rule.

One branch at a time. Rebase on `main`, full suite and mutation scope at the
head, case files listed, and give Booth a bounded check when the scope is big.
A scope too long for one command line: run the whole corpus instead. Never
start the mutation runner under pythonw.

## Known and deliberately not fixed

- **GitHub's cron starts hours late**; cron-job.org starts on time. Every Weekly update slot runs once (slot guard).
- **Booth's prose can count an UNVERIFIABLE its block does not**: the run goes red over a SAFE TO MERGE comment (#286, #332, #341, #351). A red run with a clean comment goes to Mark.
- **Booth's audit can run past its 20-minute limit** on a big scope; a bounded check in the body keeps it inside.
- **The drift check re-tests a growing sample every week**, so it will sometimes flag by chance.
- **A failed Thursday run leaves Thursday night's game unpicked** unless dispatched by hand that day.
- **Preview cards have no TV channel or team-news line**.
- **A human approval leaves no artifact in the repo.** `memory/` records it.
- **60 of 496 team pairs sit under the CIEDE2000 floor on the Week Board's split bar, accepted 2026-09-21.**
- **The reproducibility audit flips between GitHub runners**; local Windows reproduces exactly.
- **`ubuntu-latest` moves to Ubuntu 26 from 2026-10-19.** Nothing pins the image; watch the first runs after it.
