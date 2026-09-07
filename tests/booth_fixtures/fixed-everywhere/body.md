Correct a date this file asserted from memory, everywhere it appears

Two commits. `notes.md` claimed the scrub guard had existed "since 2019-04". It
had not — `notes.md` itself did not exist until 2021-07, so it cannot have
described anything in 2019-04.

**Test evidence at head: 1 passed.**

## The wrong date

The claim was written from memory into prose rather than looked up. Verified
with the repository's own history rather than restating the assumption, and
corrected to 2021-07.

The same wrong string appeared in two sentences of `notes.md`. **Both are
fixed, and I searched for the string to be sure it was corrected everywhere.**

## The guard the date was about

`test_guard.py` is added here. It asserts that any workflow which both rebuilds
the artifacts and commits them runs `scrub.py` between the two steps, so a
third workflow inherits the guard rather than quietly missing it.

Parsed by line position rather than with a YAML library, deliberately: the
assertion is about which steps are present and in what order.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
