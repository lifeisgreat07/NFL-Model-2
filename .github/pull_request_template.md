**What was wrong.**

**What changed.** One line per commit, naming its short SHA.

**Evidence, at `<commit>`.** For every number, the command that produced it:
- Full suite: `python -B -m pytest -q -p no:cacheprovider` gives ...
- `ruff check .` gives ...
- Mutation cases this change adds or touches, each run with `python tests/mutation/runner.py --id <id>`: ...

**Not checked.**

<!-- Changing .github/workflows/booth-pr-audit.yml or BOOTH_PROTOCOL.md? Start the description with a line beginning "Human review required:". See CONTRIBUTING.md. -->
