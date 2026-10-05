# 0001. The dashboard is one static HTML file

## Decision

Every page's data is written into the HTML when it is built. The page makes
no network requests for data, and there is no server. The template is kept
as parts under `src/dashboard/` and joined by `src/pipeline/template_parts.py`
into one file at build time; that join is the only build step. The built
`index.html` is not committed: `.github/workflows/deploy-pages.yml` builds it
and is the only thing that publishes it.

## Why

- It runs on GitHub Pages from a scheduled job, with nothing to host or keep
  running.
- A stranger reading the repository sees no runtime dependencies and no
  framework: vanilla JavaScript over data that is already on the page.
- What the page shows is exactly what was in the repository at the build
  commit, so a published number can be traced to a file and a test.
- Not committing the build means branches that touch the template do not
  collide with builds on `main`.

## What it costs

- Every data change needs a rebuild, and a commit made by one workflow
  cannot trigger another on its own, so the deploy listens for the workflows
  that commit data as well as for pushes. That handoff broke once; a test now
  holds it (`tests/test_generated_data_reaches_the_page.py`).
- The page grows with the data. `tests/browser/check_page.py` holds a byte
  budget.
- The one table read live at build time, the scheduled jobs' last runs
  (#281), is read into a gitignored file at deploy, so a failed read says so
  on the page rather than failing the build.

## What would reopen it

A feature that needs data the build cannot know, such as a reader's own
picks stored on a server. None is planned.

Sources: `docs/architecture.md`, "Decisions the diagram rests on";
Stage 33 item 26 (the template in parts).
