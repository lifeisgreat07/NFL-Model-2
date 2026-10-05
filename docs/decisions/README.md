# Decision records

The decisions the rest of the repository rests on, one page each: what was
decided, why, what it costs, and what would reopen it. Until Stage 49 item
22 (2026-10-05) these lived scattered through `docs/stage-history.md`,
CLAUDE.md and `docs/architecture.md`, where a reader had to know a decision
existed before they could find its reasoning.

A record is not edited to say something different happened. A reversal is
a new record that names the one it replaces, and the old one says
"superseded by" at the top.

| # | Decision |
|---|---|
| [0001](0001-one-file-site.md) | The dashboard is one static HTML file |
| [0002](0002-two-models.md) | Two models side by side: football only, and football plus the betting line |
| [0003](0003-kickoff-lock.md) | A week's picks are saved once, before its first kickoff, and never rewritten |
| [0004](0004-booth-read-only.md) | Booth, the auditor, cannot push, and merging stays a human decision |
| [0005](0005-cron-job-org.md) | Scheduled runs are started on time by cron-job.org; GitHub's cron is the fallback |
| [0006](0006-multi-sport.md) | One core, one module per sport, and nothing bleeds between them: each isolation rule held by a test |
