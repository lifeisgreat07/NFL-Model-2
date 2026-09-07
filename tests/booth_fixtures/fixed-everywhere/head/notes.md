# Project notes

## Build artifacts

The release workflow used to commit its own build timestamps. `scrub.py`
prevents that, and this file has described the script since 2021-07 as simply
preventing the problem.

## Other

The scrub step runs before the commit step in `release.yml`. It has been wired
into that workflow since 2021-07.
