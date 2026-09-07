"""
Parse the machine-readable verdict block out of a Booth audit report.

BOOTH_PROTOCOL.md requires every report to close with a fenced ```booth-verdict
block restating each numbered claim's verdict as JSON. This module reads it.

The point is Booth's regression suite: a fixture seeds a KNOWN defect in a
KNOWN file, then has to answer "did Booth catch it". Matching words in prose
would test Booth's phrasing rather than its detection -- a rewording would
break the suite while Booth was working perfectly, and a lucky word would pass
it while Booth missed everything. The block makes the question decidable.

What this module deliberately does NOT do is trust the block on its own. Booth
writes both the prose and the block, so a block that merely agrees with itself
proves nothing. Two defences:

  1. cross_check() compares the block against the report's own prose header
     counts. A block that disagrees with the prose above it is a report whose
     two halves were written from different conclusions, which is exactly the
     failure the block would otherwise hide.
  2. The suite asserts only that a claim implicating a seeded path came back
     DISCREPANCY. It never asks Booth to categorise the defect or rate itself.

Absence is not success. extract() returns None when there is no block, and
callers must treat that as "no verdict available" rather than "nothing wrong" --
the same ambiguity as a skipped workflow reporting green, which this project
has already been bitten by.
"""
import json
import re

VERDICTS = ('CONFIRMED', 'DISCREPANCY', 'UNVERIFIABLE')
OVERALLS = (
    'SAFE TO MERGE',
    'DO NOT MERGE -- DISCREPANCIES FOUND',
    'NEEDS HUMAN REVIEW',
)

# Tolerates leading indentation because the protocol shows the block indented
# inside a documentation example, and a report may quote it either way.
_BLOCK = re.compile(
    r'^[ \t]*```booth-verdict[ \t]*\n(.*?)^[ \t]*```',
    re.DOTALL | re.MULTILINE,
)

_COUNT = r'^\s*{label}:\s*(\d+)\s*$'


class VerdictError(ValueError):
    """The block is present but malformed. Never raised for a missing block."""


def extract(report_text):
    """Return the parsed verdict block, or None if the report has none.

    Raises VerdictError if a block is present but unusable -- a malformed
    block must fail loudly rather than degrade into 'no block', which would
    read as an older report and silently pass.
    """
    matches = _BLOCK.findall(report_text or '')
    if not matches:
        return None
    if len(matches) > 1:
        raise VerdictError(
            f"{len(matches)} booth-verdict blocks in one report; expected 1. "
            "Cannot tell which is the real verdict."
        )
    try:
        data = json.loads(matches[0])
    except json.JSONDecodeError as exc:
        raise VerdictError(f"booth-verdict block is not valid JSON: {exc}") from exc
    _validate(data)
    return data


def _validate(data):
    if not isinstance(data, dict):
        raise VerdictError(f"booth-verdict must be a JSON object, got {type(data).__name__}")

    for key in ('pr', 'head', 'claims', 'overall'):
        if key not in data:
            raise VerdictError(f"booth-verdict is missing required key {key!r}")

    if data['overall'] not in OVERALLS:
        raise VerdictError(
            f"overall verdict {data['overall']!r} is not one of {OVERALLS}"
        )

    claims = data['claims']
    if not isinstance(claims, list) or not claims:
        raise VerdictError("booth-verdict 'claims' must be a non-empty list")

    seen = set()
    for claim in claims:
        if not isinstance(claim, dict):
            raise VerdictError(f"each claim must be an object, got {claim!r}")
        for key in ('id', 'verdict', 'implicates'):
            if key not in claim:
                raise VerdictError(f"claim {claim!r} is missing {key!r}")
        if claim['verdict'] not in VERDICTS:
            raise VerdictError(
                f"claim {claim['id']}: verdict {claim['verdict']!r} "
                f"is not one of {VERDICTS}"
            )
        if not isinstance(claim['implicates'], list):
            raise VerdictError(f"claim {claim['id']}: 'implicates' must be a list")
        if claim['id'] in seen:
            raise VerdictError(
                f"claim id {claim['id']} appears twice; ids index the prose "
                "and must be unique"
            )
        seen.add(claim['id'])


def _prose_count(report_text, label):
    match = re.search(_COUNT.format(label=label), report_text, re.MULTILINE)
    return int(match.group(1)) if match else None


def cross_check(report_text, data=None):
    """Compare the block against the report's own prose counts.

    Returns a list of human-readable mismatches; empty means consistent.

    Booth writes both halves, so this is the one check that can catch the
    block being a second opinion rather than a restatement. A report whose
    summary says two discrepancies while its block lists none has a real
    problem regardless of which half is right.
    """
    if data is None:
        data = extract(report_text)
    if data is None:
        return ["no booth-verdict block found"]

    problems = []
    tally = {v: 0 for v in VERDICTS}
    for claim in data['claims']:
        tally[claim['verdict']] += 1

    for label, verdict in (
        ('Claims checked', None),
        ('Confirmed', 'CONFIRMED'),
        ('Discrepancies', 'DISCREPANCY'),
        ('Unverifiable', 'UNVERIFIABLE'),
    ):
        stated = _prose_count(report_text, label)
        if stated is None:
            problems.append(f"prose has no '{label}:' line to check against")
            continue
        actual = len(data['claims']) if verdict is None else tally[verdict]
        if stated != actual:
            problems.append(
                f"prose says {label}: {stated}, block has {actual}"
            )

    overall_in_prose = any(o in report_text for o in OVERALLS)
    if overall_in_prose and data['overall'] not in report_text:
        problems.append(
            f"block's overall {data['overall']!r} does not appear in the prose"
        )

    if tally['DISCREPANCY'] and data['overall'] == 'SAFE TO MERGE':
        problems.append(
            "block reports discrepancies but an unqualified SAFE TO MERGE"
        )

    return problems


def implicated_paths(data, verdicts=('DISCREPANCY',)):
    """Every path implicated by a claim with one of the given verdicts.

    The regression suite's actual question: does this set contain the file
    where the fixture seeded its defect?
    """
    out = set()
    for claim in data['claims']:
        if claim['verdict'] in verdicts:
            out.update(claim['implicates'])
    return out
