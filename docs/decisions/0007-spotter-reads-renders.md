# 0007. Spotter reads renders of the changed pages and comments; it cannot push, and it does not gate

## Decision

Spotter (Stage 43) is the visual reviewer. For a pull request that changes
what a page is built from, it looks at the pages as the dashboard draws
them, at 390x844 and 1440x900, in the light and the dark theme, from the
pull request's head and from its base. It posts one comment, updated in
place, saying what it sees and citing each image by name.

- **Three jobs, and only one of them holds a model.** A render job builds
  the dashboard from the head and from the base and takes the pictures; it
  has `contents: read` and no model. A publish job pushes those pictures to
  the orphan branch `spotter-renders`; it is the only job with
  `contents: write`, it runs no model, and it runs none of the pull
  request's code (it moves image files and nothing else). A reading job
  holds the model with `contents: read` and `pull-requests: write`, is
  handed the workflow's own token, and cannot mint an OIDC token.
- **Advisory.** Spotter's comment never carries a verdict word. Booth's
  report stays the verdict and a person still merges (decision record 0004).
- **No pixel comparison.** The pictures are for reading. The browser checks
  decided against pixel-diff gates (font hinting and antialiasing make them
  cry wolf) and that stands.
- **Not for forks.** A pull request from a fork is not rendered, as with
  Booth's dispatch.

## Why

- The model that reads a picture must not be able to change what it reads.
  Booth's lesson (0004) applies unchanged: the reader holds read and
  comment, and any write belongs to a job with no model and no pull request
  code in it.
- The pictures need a home a comment can link to. An orphan branch keeps the
  images out of main's history and out of the working tree, and each publish
  prunes the folders of pull requests that have closed.
- Naming each picture (`board-390x844-dark`) turns "renders at both sizes"
  in a description from a claim into a file name that can be checked.

## What it costs

- A second branch to keep tidy, and a publish job whose write permission
  is real, held by a test.
- Two builds per run (base and head), so a visual pull request waits longer.
- A reading is a model's opinion, which is why it advises.

## What would reopen it

A reading that needs to write (it should not), images too large for a
branch, or a check that proves the pixel gate can be made stable. Each is a
new record.

Sources: `tests/test_spotter_permissions.py`; `docs/history/07-fourth-audit-2026-10-04.md`,
Stage 43; `docs/decisions/0004-booth-read-only.md`.
