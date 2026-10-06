# New items before the 2026-10-08 lock

Part of the stage history; the index is `docs/stage-history.md`. Moved verbatim from
that file on 2026-10-06 (Stage 49 item 24).

## Stages 45 to 49: new items for the days before the 2026-10-08 lock (proposed 2026-10-04)

Mark asked for 25 new items, by the audit's categories or as features not
yet thought of, that can be done before Thursday's lock. Each was checked
against the repository on 2026-10-04 at `0ae5df4`. None touches the weekly
run or the weekend refresh, so none has to wait for the lock. Proposed;
Mark has not approved them yet.

**Approved and worked (2026-10-05).** Mark took the recommended ten, in
this order: 23 (#282), 21 (#283), 20 (#284), 4 (#285), 25 (#286), 15
(#288), 16 (#289), 17 (#290), 19 (#291), 22 (`docs/decisions/`, straight
to main). All ten are done. Narrowings: item 4 kept collect-agent-log's
`pull-requests: read` (Booth's reports are PR comments read through the
issues API; `issues: read` alone was not verified); item 15 covered
`src/research/calibration.py` only among the research scripts, and found
the tuned constants unguarded (now `tests/test_config_pins.py`); item 16
left out `confidence_points`, which is inline in `predict_week`; item 19
is strict on `src/agents` alone (`--follow-imports=silent`). Items 1 and 2
wait for the 2026-10-08 lock because the deploy runs on every data commit;
3, 5 to 14, 18 and 24 are not started.

### Stage 45 - Supply chain and security

1. Pin the nine action references still on tags (setup-node, cache,
   upload- and download-artifact, upload-pages-artifact, deploy-pages) and
   widen `tests/test_action_pins.py` to every `uses:`. Stage 27 left them
   "for now"; deploy-pages runs with `pages: write` and `id-token: write`.
2. A Content-Security-Policy meta tag. The page loads inline code and ESPN
   logos only; nothing says so today.
3. `pip-audit` against `requirements.txt`, report-only, in a nightly job.
   The CI installs stay as they are.
4. `SECURITY.md`, and a test that every workflow declares its permissions
   and holds none it does not use.

### Stage 46 - Proof and open data

5. Proof of lock: each week shows when its picks were locked and the
   commit that locked them, linked to GitHub, read at deploy from the
   commits API (the #281 pattern).
6. A "late by" column on the runs table, from each workflow's cron lines.
7. `picks.csv`, every locked pick and its grade, published beside the page.
8. A feed (`feed.xml`) of each week's picks and results.
9. Against the market: how the models did when they picked against the
   market's favourite (check first that no page already shows it).

### Stage 47 - Accessibility and resilience

10. Forced colours (Windows High Contrast): no rule today; bars and chips
    drawn as backgrounds can vanish. Rules and a browser-check pass.
11. A print stylesheet: no `@media print` rule today.
12. A canonical link and structured data (JSON-LD).
13. A render-time budget in the browser checks beside the byte budget.
14. A web app manifest beside the existing touch icon.

### Stage 48 - Test depth

15. Mutation cases for the modules no case targets: `src/pipeline/config.py`,
    `src/pipeline/ol_continuity.py`, `src/research/calibration.py` (the
    drift baseline's writer) first, then the research scripts.
16. Property tests (hypothesis, dev only) for `market_prob`,
    `confidence_points`, `kickoff_utc` across DST, `graded_correct`.
17. The suite in random order, nightly, to find tests that depend on order.
18. A dead-code report (vulture) with an allowlist; delete outside
    `src/pipeline` now, inside after the lock.
19. mypy strict on `src/agents`.

### Stage 49 - Agents, process and documentation

20. Scout preflight: a claim that a file was "restored", "committed" or
    "tracked" names a tracked file (#278's body said "restored the tracked
    `index.html`", which is untracked).
21. A session-start doctor: the read-only checks every session opens with
    (QB routine, Weekly update's drift line, the canary), read from the
    Actions API in one command.
22. Decision records: one page each for the decisions now spread through
    this file (one-file site, two models, the kickoff lock, Booth read-only,
    cron-job.org), linked from the README.
23. Stop hand-bumping the README's case-file count: generate it, or state it
    in a form a new case file does not change. Every branch that adds one
    conflicts with every other.
24. Split this file by audit era under `docs/history/`, with an index and a
    size guard like `docs/traps.md`'s.
25. The Releases workflow also runs on a pushed `v*` tag, so a new model
    version releases itself.
