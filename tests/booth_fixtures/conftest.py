"""
Keep pytest out of the fixture trees.

Everything under tests/booth_fixtures/<id>/{base,head}/ is *material for Booth
to audit*, not tests of this repository. Some of it is deliberately wrong --
that is the entire point of a regression fixture -- and a fixture whose own
tests fail would fail this project's real suite if collected.

Two things went wrong before this file existed, both worth keeping written
down because the second is the subtle one:

  1. head/test_guard.py is named like a test, so pytest imported and ran it as
     part of the ordinary suite. It happened to pass. The next fixture, which
     seeds a genuinely failing test, would not have.

  2. Importing it created head/__pycache__/*.pyc, and the loader's tree walk
     read every file as UTF-8. A .pyc is not UTF-8. Five fixture tests failed
     with a decode error that had nothing to do with what they assert, and
     only in the full suite -- in isolation nothing collected the file, so it
     passed. A failure that appears only when run alongside everything else is
     the expensive kind to chase.

The loader also skips __pycache__ independently. Belt and braces on purpose:
this conftest stops the .pyc being created here, and the loader stops it
mattering if something else creates one.
"""
collect_ignore_glob = ['*']
