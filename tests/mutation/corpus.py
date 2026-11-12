"""
Loading and validation for the mutation corpus.

Split from the runner deliberately. Running the mutations is expensive -- each
one is a pytest invocation -- so it is an occasional command, not part of the
suite. But the corpus can ROT for free: a refactor moves the line a mutation
anchors to, the anchor stops matching, and that mutation silently stops
testing anything while the corpus still claims coverage.

That is not hypothetical. It happened twice in one session while these
mutations still lived in throwaway scripts: one anchor matched zero times
after a rename, another after a parameter changed. Both were caught only
because the script asserted its own anchor count and crashed.

So the split is: this module validates cheaply and runs inside the normal
suite on every run; runner.py executes and is invoked on purpose.
"""
import json
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
CASES_DIR = Path(__file__).parent / 'cases'

REQUIRED_CASE_FIELDS = ('id', 'why', 'find', 'replace', 'expect_caught_by')

#: Files that were split into parts, and the parts, in order (Stage 87 item 4).
#: A case may still name the whole file: it is resolved to the one part that
#: holds its anchor. A case whose anchor is in no part, or in more than one,
#: keeps the whole file's name, and anchor_occurrences counts across every part,
#: so the anchor check reports the real count instead of a missing file.
SPLIT = {
    'src/dashboard/app.js': ['src/dashboard/app_controls.js', 'src/dashboard/app_ratings.js',
                             'src/dashboard/app_board.js', 'src/dashboard/app_accuracy.js',
                             'src/dashboard/app_team.js', 'src/dashboard/app_pages.js'],
}


def _count(path, find_text):
    blob = (REPO_ROOT / path).read_bytes()
    nl = b'\r\n' if b'\r\n' in blob else b'\n'
    find = find_text.encode('utf-8').replace(b'\n', nl)
    return blob.count(find), find, nl


def resolve_target(target, find_text):
    """The file a case mutates: `target`, or for a split file the one part
    holding the anchor exactly once (the whole file's name when none does)."""
    if target not in SPLIT:
        return target
    hits = [p for p in SPLIT[target] if _count(p, find_text)[0] == 1]
    others = [p for p in SPLIT[target] if p not in hits and _count(p, find_text)[0]]
    return hits[0] if len(hits) == 1 and not others else target


class CorpusError(Exception):
    pass


def load_corpus():
    """Every mutation case across every corpus file, flattened.

    Each returned case carries its own target and test path, so the runner
    does not need to know which file it came from.
    """
    if not CASES_DIR.is_dir():
        raise CorpusError(f"no cases directory at {CASES_DIR}")

    cases = []
    for path in sorted(CASES_DIR.glob('*.json')):
        data = json.loads(path.read_text(encoding='utf-8'))
        for field in ('target', 'tests', 'cases'):
            if field not in data:
                raise CorpusError(f"{path.name}: missing top-level {field!r}")
        for case in data['cases']:
            missing = [f for f in REQUIRED_CASE_FIELDS if f not in case]
            if missing:
                raise CorpusError(
                    f"{path.name}: case {case.get('id', '?')!r} missing {missing}")
            tests = case.get('tests', data['tests'])
            # The runner hands this to pytest as ONE argv element. Two paths
            # separated by a space are accepted here, land as a single
            # nonexistent filename, and pytest exits 4 having reported no
            # failures at all -- which the runner then reads as "the suite
            # went red but the named guard passed" and prints WRONG-GUARD.
            # The case looks like a broken test rather than a broken case, and
            # you go and edit a guard that was fine. Refuse it at load time.
            if not (REPO_ROOT / tests).exists():
                raise CorpusError(
                    f"case {case['id']!r}: no such test file {tests!r}. A case "
                    f"names exactly one pytest path -- for a second one, give "
                    f"that case its own 'tests' key in a separate case.")
            named = case.get('target', data['target'])
            cases.append({
                **case,
                'corpus': path.name,
                'target': resolve_target(named, case['find']),
                'named_target': named,
                'tests': tests,
            })
    if not cases:
        raise CorpusError("the corpus is empty -- nothing would be tested")
    return cases


def anchor_occurrences(case):
    """How many times this case's `find` text appears in its target.

    Normalises the newlines in the corpus (always \\n) to whatever the file on
    disk uses. These files are CRLF on the Windows clone and LF in CI, and a
    multi-line anchor that does not account for that matches zero times in one
    of the two -- which reads exactly like corpus rot.
    """
    if case['target'] in SPLIT:
        counts = [_count(p, case['find']) for p in SPLIT[case['target']]]
        return sum(c for c, _, _ in counts), counts[0][1], counts[0][2]
    target = REPO_ROOT / case['target']
    if not target.exists():
        raise CorpusError(f"case {case['id']!r}: no such target {case['target']}")
    return _count(case['target'], case['find'])


def duplicate_ids():
    seen, dupes = set(), set()
    for case in load_corpus():
        if case['id'] in seen:
            dupes.add(case['id'])
        seen.add(case['id'])
    return sorted(dupes)
