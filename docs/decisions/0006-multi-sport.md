# 0006. One core, one module per sport, and nothing bleeds between them

## Decision

The project predicts more than one league: the NFL, then the NHL, then the
NBA (Mark, 2026-10-05; MLB not this year). It does that as **one shared core
and one module per sport**, in three layers:

| Layer | Folder | May import | Imported by |
|---|---|---|---|
| Core | `src/core/` | itself, third-party libraries | sports, site, agents |
| Sport | `src/sports/<code>/` | the core, itself | the site layer only |
| Site | `src/site/` | the core, every sport | nothing |

A sport is a code (`nfl`, `nhl`, `nba`) and one object, `SPORT`, that
satisfies `SportModule` in `src/core/sport.py`. The core is written
against that interface and never against a sport. The site layer builds the
home page and is the only code that sees more than one sport.

**Every sport runs the NFL's workflow.** The same page set; Model A (the sport
alone) beside Model B (plus the market) and the market itself; a lock that
saves picks once before the start and never rewrites them; grading of locked
picks only; the drift check; alerts; pre-registered experiments judged by the
paired bootstrap on proper scoring rules; a routine for the late-breaking
player that opens a pull request and never writes picks; Booth on every PR.

### What is shared, and what each sport owns

| Shared (core) | Owned by each sport |
|---|---|
| The lock engine: write once, never rewrite, refuse a started game | The lock rule: a week at once (NFL), each game (NHL, NBA) |
| Grading, and the "Cancelled" state | What counts as the outcome; ties, overtime, shootouts |
| Drift check, calibration, paired bootstrap | Its baseline, its backtest, its figures |
| Experiment registry and decision labels | Its registrations, under `experiments/nfl/<code>/` |
| `ModelSpec`, the walk-forward evaluation | Its features and its model specs |
| Alerts (open or comment on an issue) | Its issue titles, prefixed "NFL: " / "NHL: " |
| The page shell, design tokens, charts | Its pages' content, team colours and logos |
| Booth, Scout's pre-flight, session tools, mutation harness | Its tests, its mutation cases, its Booth fixtures |
| The slot guard | Its scheduled runs and its cron-job.org jobs |
| | Its data source, loader, schema, cache and fallback |
| | Its routine (quarterback, starting goalie, availability) |
| | Standings rules and its playoff simulation |

### The isolation rules, each held by a test

1. **No sport imports another.** A module under `src/sports/<a>/` imports
   nothing under `src/sports/<b>/`.
2. **The core imports no sport.** Nothing under `src/core/` imports
   `src/sports/` or `src/site/`. Until Stage 52, `src/sports/nfl/` and
   `src/sports/nfl/research/` *are* the NFL, so the core imports neither.
3. **A sport's workflow writes only its own folders.** Every path a
   `<code>-*.yml` workflow adds, commits or uploads is under that sport's
   `data/`, `predictions/`, `results/`, `experiments/` or `site/` folder.
4. **Every name a sport owns carries the sport.** Files and folders, workflow
   names, issue titles, browser storage keys, CSS scopes, page routes and
   job names begin with the code, so two sports cannot collide on one name
   and a grep for a sport finds all of it.
5. **A change to one sport moves no byte another publishes.** Proved with a
   build before and after (Stage 52 for the move, Stage 60 both ways).

Rules 1 to 4 are static checks in `tests/test_sport_isolation.py`, each with
a mutation case that breaks it on purpose. Rule 5 needs a build, so it is a
proof run at the stages that could break it.

Until Stage 52 moves the NFL, the NFL's current paths (`src/sports/nfl/`,
`data/`, `predictions/`, the existing workflow names and storage keys) are
listed once in the test as the legacy layout. The list may only shrink; Stage
52 empties it.

## Why

- **Mark's rule: moving between sports should feel the same.** That only
  holds if one implementation serves all of them. Copying the NFL's code per
  sport gives three versions of the lock to keep agreeing, and this project
  has already met that failure: the live pipeline and the backtest built
  their own models and agreed only because two people copied carefully
  (`ModelSpec`, Stage 33 item 21).
- **Isolation by test, not by care.** Every guard here exists because a
  "surely nothing does that" was wrong at least once (CLAUDE.md, "an audit
  finding is a hypothesis"). A sport that can read another's folder will,
  eventually, by accident, and a published pick is the thing that would
  move.
- **Separate folders keep the record auditable per sport.** A lock is
  evidence because its commit is; mixing sports in one folder makes "what
  did the NHL lock on the 14th" a filter instead of a path.
- **A three-layer import rule is checkable with the standard library.** It
  is one AST walk per file, which keeps the guard free and fast enough to
  run on every commit.

## What it costs

- **A large move for the NFL** (Stage 52): every path, workflow and test is
  re-targeted. It is done once, behind a byte-identical proof, in the window
  after a Thursday lock, and Mark re-points the cron-job.org jobs and the QB
  routine by hand.
- **The interface constrains the NFL.** The NFL's weekly lock becomes one
  `LockRule` among others; nothing it does today may be lost in the move,
  which is what the proof checks.
- **Shared code moves slower.** A change to the core is a change to every
  sport and is audited as one.
- **The NFL page's address changes** to `/nfl/` (Stage 53), with a redirect
  from the old one.

## Considered and not chosen

- **One repository per sport.** Strongest isolation, but the shared core
  would be copied or packaged and versioned, and the home page would need a
  third repository to read the others. The rules above get the isolation
  with one repository.
- **Sports as configuration of one pipeline.** The NHL's lock per game, its
  standings points and its goalie are not settings of the NFL's code; they
  would become `if sport ==` branches through the core, which is the
  bleeding this record exists to prevent.

## What would reopen it

A sport whose workflow cannot be the NFL's (a sport with no market, no
late-breaking player, or no per-game outcome), or the core growing a branch
on a sport's code. Either is a new record.

Sources: `docs/stage-history.md`, Stages 50 to 61; `memory/2026-10-05.md`;
`src/core/sport.py`.
