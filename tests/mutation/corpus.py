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
            cases.append({
                **case,
                'corpus': path.name,
                'target': case.get('target', data['target']),
                'tests': case.get('tests', data['tests']),
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
    target = REPO_ROOT / case['target']
    if not target.exists():
        raise CorpusError(f"case {case['id']!r}: no such target {case['target']}")
    blob = target.read_bytes()
    nl = b'\r\n' if b'\r\n' in blob else b'\n'
    find = case['find'].encode('utf-8').replace(b'\n', nl)
    return blob.count(find), find, nl


def duplicate_ids():
    seen, dupes = set(), set()
    for case in load_corpus():
        if case['id'] in seen:
            dupes.add(case['id'])
        seen.add(case['id'])
    return sorted(dupes)
