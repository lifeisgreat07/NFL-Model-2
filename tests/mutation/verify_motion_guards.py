"""Do the motion guards in tests/test_motion_system.py actually fail?

A guard test that has never been seen red is not evidence of anything. Every
one of those tests passed on its first run against the current template, which
is what you would also see if the regexes matched nothing at all. This script
settles which it is: it injects eight defects one at a time and asserts that
the right test goes red for each.

Run it by hand -- it is deliberately NOT collected by pytest, because it
writes to `src/dashboard_template.html`:

    python tests/mutation/verify_motion_guards.py

Every mutant is a defect that has already shipped once or is one careless edit
away. The first is the literal `.4s` on `.tele-bar-seg` that Booth found on
PR #51 by sweeping 3,582 elements in a browser; the point of the guards is
that finding it should not have needed a browser.

The template is copied to a backup outside the repo before anything is
touched, restored from it after every mutant, and the final line compares the
bytes. If this script is interrupted mid-run, `git checkout
src/dashboard_template.html` puts it back.
"""
import shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
T = ROOT / 'src' / 'dashboard_template.html'
BAK = Path(tempfile.gettempdir()) / 'motion_guard_template.bak'
shutil.copyfile(T, BAK)

MUTANTS = [
    # (name, find, replace, test that must go red)
    ("the exact PR#51 defect: a literal duration on tele-bar-seg",
     "transition:width var(--dur-slow) var(--ease)",
     "transition:width .4s var(--ease)",
     "test_every_duration_is_a_token"),

    ("a literal duration hiding as the SECOND property of a compound transition",
     "transition:border-color var(--dur-base) var(--ease), color var(--dur-base) var(--ease), opacity var(--dur-base) var(--ease);",
     "transition:border-color var(--dur-base) var(--ease), color var(--dur-base) var(--ease), opacity .25s var(--ease);",
     "test_every_duration_is_a_token"),

    ("reduced-motion block stops collapsing --dur-slow",
     "--dur-fast:0ms; --dur-base:0ms; --dur-slow:0ms;",
     "--dur-fast:0ms; --dur-base:0ms;",
     "test_reduced_motion_collapses_every_duration_token"),

    ("reduced-motion collapses to a small value rather than zero",
     "--dur-fast:0ms; --dur-base:0ms; --dur-slow:0ms;",
     "--dur-fast:0ms; --dur-base:0ms; --dur-slow:50ms;",
     "test_reduced_motion_collapses_every_duration_token"),

    ("transition: all creeps back in",
     "transition:border-color var(--dur-base) var(--ease), color var(--dur-base) var(--ease), opacity var(--dur-base) var(--ease);",
     "transition:all var(--dur-base) var(--ease);",
     "test_transition_all_never_appears"),

    ("a second easing curve appears",
     "--ease:cubic-bezier(.2,.7,.2,1);",
     "--ease:cubic-bezier(.2,.7,.2,1); --ease-alt:cubic-bezier(.34,1.56,.64,1);",
     "test_there_is_exactly_one_easing_curve"),

    ("a hover rule is written outside the hover guard",
     "  *{box-sizing:border-box; margin:0; padding:0;}",
     "  .fake-thing:hover{color:var(--accent);}\n  *{box-sizing:border-box; margin:0; padding:0;}",
     "test_every_hover_rule_sits_behind_the_hover_guard"),

    ("a motion token is renamed away",
     "--press:translateY(1px);",
     "--press-unused:translateY(1px);",
     "test_the_motion_tokens_are_defined"),
]


def run():
    p = subprocess.run([sys.executable, '-m', 'pytest', 'tests/test_motion_system.py',
                        '-q', '--no-header', '--tb=no'],
                       capture_output=True, text=True, cwd=ROOT)
    return p.stdout


ok = True
for name, find, repl, expect in MUTANTS:
    src = BAK.read_text(encoding='utf-8')
    n = src.count(find)
    if n < 1:
        print(f"SKIP  {name}\n      anchor not found: {find[:70]!r}")
        ok = False
        continue
    T.write_text(src.replace(find, repl, 1), encoding='utf-8')
    out = run()
    caught = 'failed' in out
    named = expect in out
    print(f"{'RED  ' if caught else 'GREEN'} {name}   (anchor x{n})")
    if not named:
        print(f"      -> WRONG TEST or none: {out.strip().splitlines()[-1]}")
    if not (caught and named):
        ok = False

shutil.copyfile(BAK, T)
print()
print("template restored byte-for-byte:", T.read_bytes() == BAK.read_bytes())
print("ALL MUTANTS CAUGHT" if ok else "SOME MUTANTS SURVIVED")
sys.exit(0 if ok else 1)
